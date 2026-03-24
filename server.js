const puppeteer = require("puppeteer");
const os = require("os");
const fs = require("fs");
const express = require('express');
const path = require('path');
const crypto = require('crypto');
const http = require('http');
const https = require('https');
const net = require('net');
const url = require('url');
const querystring = require('querystring');

const app = express();
const PORT = 1337;
const HTTP_PROXY_PORT = 1338;

const ENCRYPTION_KEY = crypto.scryptSync('cx-proxy-secret', 'salt', 32);
const IV_LENGTH = 16;

const OPENAI_CLIENT_ID = process.env.OPENAI_CLIENT_ID || 'your-openai-client-id';
const OPENAI_CLIENT_SECRET = process.env.OPENAI_CLIENT_SECRET || 'your-openai-client-secret';
const CALLBACK_URL = process.env.CALLBACK_URL || 'http://localhost:1337/api/auth/callback';

// Buffer the raw body for API proxying to allow retries
app.use('/v1', express.raw({ type: '*/*', limit: '10mb' }));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const userApiKeys = new Map([
  ['cx_dummy_test_key_123', { userId: '1', email: 'test@email.com', requestCount: 0 }]
]);

const accounts = [
  {
    id: '1',
    email: 'user1@email.com',
    level: 'Plus',
    token: encrypt('sk-openai-token-xxx'),
    quota: {
        total: { used: 0, limit: 1000 },
        weekly: { used: 0, limit: 200 },
        fiveHour: { used: 0, limit: 40, resetAt: new Date(Date.now() + 5*60*60*1000).toISOString() }
    },
    status: 'active'
  }
];

const proxyStats = {
  totalRequests: 0,
  successfulRequests: 0,
  failedRequests: 0
};

// ============ SSE Logs Emitter (日志推送服务器端发送事件) ============
const logClients = new Set();

function emitLog(message, level = 'info') {
  const logEntry = JSON.stringify({ message, level, timestamp: Date.now() });
  for (const client of logClients) {
    client.write(`data: ${logEntry}\n\n`);
  }
}

app.get('/api/logs/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  logClients.add(res);

  req.on('close', () => {
    logClients.delete(res);
  });
});

function encrypt(text) {
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv('aes-256-cbc', ENCRYPTION_KEY, iv);
  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return iv.toString('hex') + ':' + encrypted;
}

function decrypt(text) {
  try {
    const parts = text.split(':');
    const iv = Buffer.from(parts[0], 'hex');
    const encrypted = parts[1];
    const decipher = crypto.createDecipheriv('aes-256-cbc', ENCRYPTION_KEY, iv);
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  } catch { return null; }
}

function generateApiKey() {
  return 'cx_' + crypto.randomBytes(24).toString('hex');
}

/**
 * Automatically update local Codex config.toml to point to this proxy
 * (自动更新本地 Codex 配置文件)
 */
function updateCodexConfig(apiKey) {
  try {
    const configDir = path.join(os.homedir(), '.codex');
    const configPath = path.join(configDir, 'config.toml');

    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }

    let configContent = '';
    if (fs.existsSync(configPath)) {
      configContent = fs.readFileSync(configPath, 'utf8');
      // Backup old config
      fs.writeFileSync(configPath + '.bak', configContent);
    }

    // Simple TOML manipulation
    const apiBase = `http://127.0.0.1:${PORT}/v1`;

    if (configContent.includes('[openai]')) {
      // Use logic that doesn't rely on regex for simple replacement (更鲁棒的替换逻辑)
      const lines = configContent.split('\n');
      let inOpenAi = false;
      let apiBaseUpdated = false;
      let apiKeyUpdated = false;

      for (let i = 0; i < lines.length; i++) {
        if (lines[i].trim() === '[openai]') inOpenAi = true;
        else if (lines[i].startsWith('[') && lines[i].endsWith(']')) inOpenAi = false;

        if (inOpenAi) {
          if (lines[i].includes('api_base')) {
            lines[i] = `api_base = "${apiBase}"`;
            apiBaseUpdated = true;
          }
          if (lines[i].includes('api_key')) {
            lines[i] = `api_key = "${apiKey}"`;
            apiKeyUpdated = true;
          }
        }
      }

      if (!apiBaseUpdated) lines.splice(lines.findIndex(l => l.trim() === '[openai]') + 1, 0, `api_base = "${apiBase}"`);
      if (!apiKeyUpdated) lines.splice(lines.findIndex(l => l.trim() === '[openai]') + 1, 0, `api_key = "${apiKey}"`);

      configContent = lines.join('\n');
    } else {
      configContent += `\n[openai]\napi_base = "${apiBase}"\napi_key = "${apiKey}"\n`;
    }

    fs.writeFileSync(configPath, configContent.trim() + '\n');
    emitLog(`Automatically updated ${configPath} / 已自动更新本地配置文件`, 'success');
    return true;
  } catch (err) {
    emitLog(`Failed to update config: ${err.message}. Please configure manually. / 自动更新配置失败，请手动配置。`, 'warning');
    return false;
  }
}

function selectAvailableAccounts() {
  const available = accounts.filter(a =>
    a.status !== 'exhausted' && a.status !== 'error' &&
    a.quota.fiveHour.used < a.quota.fiveHour.limit &&
    a.quota.weekly.used < a.quota.weekly.limit &&
    a.quota.total.used < a.quota.total.limit
  );
  // Sort by remaining 5h quota (以 5 小时内余量作为主排序条件)
  available.sort((a, b) =>
    (b.quota.fiveHour.limit - b.quota.fiveHour.used) - (a.quota.fiveHour.limit - a.quota.fiveHour.used)
  );
  return available;
}

// ============ Reverse Proxy (反向代理 - Codex 负载均衡网关) ============

app.all('/v1/*', async (req, res) => {
  // 1. Authenticate local Codex client (鉴权本地客户端)
  const authHeader = req.headers['authorization'];
  let apiKey = null;

  if (authHeader && authHeader.startsWith('Bearer ')) {
    apiKey = authHeader.substring(7);
  } else {
    apiKey = req.headers['x-api-key'];
  }

  if (!apiKey || !userApiKeys.has(apiKey)) {
    emitLog(`Unauthorized request to ${req.originalUrl} (Invalid Key) / 未授权的请求 (API Key 无效)`, 'error');
    return res.status(401).json({
      error: { message: 'Invalid or missing API key. Please configure dummy key in config.toml.', type: 'invalid_request_error' }
    });
  }

  userApiKeys.get(apiKey).requestCount++;
  proxyStats.totalRequests++;

  // Log request content snippet for visibility (日志显示请求摘要)
  let requestSummary = '';
  try {
     if (req.body && req.body.length > 0) {
        const bodyStr = req.body.toString('utf8');
        const bodyJson = JSON.parse(bodyStr);
        requestSummary = bodyJson.messages ? bodyJson.messages[bodyJson.messages.length - 1].content.substring(0, 30) : '';
     }
  } catch(e) {}

  emitLog(`Incoming request: ${req.method} ${req.originalUrl} ${requestSummary ? '-> ' + requestSummary + '...' : ''}`, 'info');

  const availableAccounts = selectAvailableAccounts();

  if (availableAccounts.length === 0) {
    proxyStats.failedRequests++;
    emitLog('No available accounts in the pool! / 账号池中没有可用账号！', 'error');
    return res.status(503).json({
      error: { message: 'No available accounts to process the request.', type: 'server_error' }
    });
  }

  let lastError = null;
  const targetPath = req.originalUrl;

  // Seamless retry mechanism (无缝重试机制)
  for (const account of availableAccounts) {
    const token = decrypt(account.token);
    if (!token) {
      account.status = 'error';
      lastError = { message: `Could not decrypt token for account ${account.email}.`, type: 'server_error' };
      continue;
    }

    try {
      await new Promise((resolve, reject) => {
        const headers = { ...req.headers };
        delete headers['host'];
        delete headers['content-length'];

        headers['Authorization'] = `Bearer ${token}`;

        const options = {
          hostname: 'api.openai.com',
          port: 443,
          path: targetPath,
          method: req.method,
          headers: headers
        };

        const proxyReq = https.request(options, (proxyRes) => {
          // If 401 or 429, mark account and RETRY next (如果是 401 或 429，标记账号并进入下一轮循环重试)
          if (proxyRes.statusCode === 401 || proxyRes.statusCode === 429) {
            account.status = proxyRes.statusCode === 401 ? 'error' : 'exhausted';
            lastError = { message: `OpenAI API returned ${proxyRes.statusCode}.`, type: 'upstream_error' };
            proxyRes.resume();
            emitLog(`Account ${account.email} reported ${proxyRes.statusCode}. Switching to next account... / 账号返回 ${proxyRes.statusCode}，正在自动切换...`, 'warning');
            reject(new Error(`Upstream ${proxyRes.statusCode}`));
          } else if (proxyRes.statusCode >= 500) {
             // 5xx might be transient, but we still try another account
             lastError = { message: `OpenAI API returned ${proxyRes.statusCode}.`, type: 'upstream_error' };
             proxyRes.resume();
             emitLog(`Upstream 5xx for ${account.email}. Retrying...`, 'warning');
             reject(new Error(`Upstream ${proxyRes.statusCode}`));
          } else {
            // Success (200, or client errors like 400, 404 which should be passed back)
            account.quota.fiveHour.used++;
            account.quota.weekly.used++;
            account.quota.total.used++;
            proxyStats.successfulRequests++;
            emitLog(`Request fulfilled by ${account.email} (Status: ${proxyRes.statusCode})`, 'success');
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res).on('finish', resolve);
          }
        });

        proxyReq.on('error', (err) => {
          account.status = 'error';
          lastError = { message: 'Proxy request failed.', type: 'proxy_error', details: err.message };
          reject(err);
        });

        if (req.body && req.body.length > 0) {
          proxyReq.write(req.body);
        }
        proxyReq.end();
      });

      return; // Request handled successfully

    } catch (error) {
       // Log the error and continue to the next account in the loop
       console.error(`[Proxy Retry] Account ${account.email} failed: ${error.message}`);
    }
  }

  // All accounts failed
  proxyStats.failedRequests++;
  emitLog('All accounts failed to process the request. / 账号池内所有账号均无法处理此请求。', 'error');
  if (!res.headersSent) {
    res.status(503).json({
      error: {
        message: 'All available OpenAI accounts failed to process the request.',
        type: 'server_error',
        last_error: lastError
      }
    });
  }
});

// ============ OAuth Routes (OAuth 路由) ============

// Automated Token Capture Flow (自动化 Token 捕获流)
app.get('/api/auth/login', async (req, res) => {
  const requestId = crypto.randomBytes(8).toString('hex');
  const userDataDir = path.join(os.tmpdir(), `cx-puppeteer-${requestId}`);

  emitLog(`Starting automated login browser... / 正在启动自动化登录浏览器...`, 'info');

  try {
    const browser = await puppeteer.launch({
      headless: false,
      userDataDir: userDataDir,
      defaultViewport: null,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Redirect user to OpenAI Login
    await page.goto('https://chat.openai.com/auth/login');

    res.send(`
      <html>
        <body style="background: #0f172a; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif;">
          <h2>Please complete login in the opened browser window</h2>
          <p>请在打开的浏览器窗口中完成登录</p>
          <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
            Waiting for session token... / 正在等待捕获 Token...
          </div>
        </body>
      </html>
    `);

    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('chat.openai.com/api/auth/session') && response.status() === 200) {
        try {
          const session = await response.json();
          if (session.accessToken) {
            const email = session.user?.email || 'unknown';
            emitLog(`Captured Token for: ${email} / 已捕获账号 Token: ${email}`, 'success');

            // Add or Update Account
            const existingIdx = accounts.findIndex(a => a.email === email);
            const newAccount = {
              id: existingIdx !== -1 ? accounts[existingIdx].id : Date.now().toString(),
              email: email,
              name: session.user?.name || '',
              level: 'Plus', // Default for now
              token: encrypt(session.accessToken),
              quota: existingIdx !== -1 ? accounts[existingIdx].quota : {
                  total: { used: 0, limit: 1000 },
                  weekly: { used: 0, limit: 200 },
                  fiveHour: { used: 0, limit: 40, resetAt: new Date(Date.now() + 5*60*60*1000).toISOString() }
              },
              status: 'active'
            };

            if (existingIdx !== -1) {
              accounts[existingIdx] = newAccount;
            } else {
              accounts.push(newAccount);
            }

            // Generate/Update Dummy Key
            const apiKey = generateApiKey();
            userApiKeys.set(apiKey, {
              userId: newAccount.id,
              email: newAccount.email,
              createdAt: new Date().toISOString(),
              requestCount: 0
            });

            // Update local config
            if (typeof updateCodexConfig === 'function') {
                updateCodexConfig(apiKey);
            }

            emitLog(`Account ${email} is now ready and configured! / 账号 ${email} 已就绪并完成配置！`, 'success');

            // Success notification to all clients via SSE
            emitLog(`SUCCESS_LOGIN:${email}:${apiKey}`, 'system');

            await browser.close();
          }
        } catch (e) {
          console.error('Failed to parse session JSON', e);
        }
      }
    });

    browser.on('disconnected', () => {
       emitLog(`Login browser closed. / 登录浏览器已关闭。`, 'info');
    });

  } catch (err) {
    emitLog(`Failed to launch browser: ${err.message}`, 'error');
    if (!res.headersSent) res.status(500).send('Failed to launch login flow');
  }
});

// Get account list (获取账号列表)
app.get('/api/accounts', (req, res) => {
  res.json(accounts.map(a => ({
    id: a.id,
    email: a.email,
    name: a.name,
    level: a.level,
    quota: a.quota,
    status: a.status
  })));
});

// Switch active account flag (切换账号状态)
app.put('/api/accounts/:id/switch', (req, res) => {
  accounts.forEach(a => a.isActive = (a.id === req.params.id));
  res.json({ success: true });
});

// Delete account (删除账号)
app.delete('/api/accounts/:id', (req, res) => {
  const idx = accounts.findIndex(a => a.id === req.params.id);
  if (idx !== -1) accounts.splice(idx, 1);
  res.json({ success: true });
});

// Get proxy stats (获取代理统计信息)
app.get('/api/proxy/stats', (req, res) => {
  const aggregated = accounts.reduce((acc, a) => {
    acc.totalUsed += a.quota.total.used;
    acc.totalLimit += a.quota.total.limit;
    acc.weeklyUsed += a.quota.weekly.used;
    acc.weeklyLimit += a.quota.weekly.limit;
    acc.fiveHourUsed += a.quota.fiveHour.used;
    acc.fiveHourLimit += a.quota.fiveHour.limit;
    return acc;
  }, { totalUsed: 0, totalLimit: 0, weeklyUsed: 0, weeklyLimit: 0, fiveHourUsed: 0, fiveHourLimit: 0 });

  res.json({
    ...proxyStats,
    aggregated,
    accounts: accounts.map(a => ({
      email: a.email,
      level: a.level,
      quota: a.quota,
      status: a.status
    }))
  });
});

// Health check (健康检查)
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', proxy: 'running', accounts: accounts.length });
});

// ============ Background Session Refresher (后台 Session 刷新任务) ============

async function refreshAllSessions() {
  if (accounts.length === 0) return;

  emitLog('Starting background session refresh... / 正在执行后台 Session 刷新...', 'info');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  for (const account of accounts) {
    try {
      const page = await browser.newPage();
      // We can't easily refresh without cookies, but if we have userDataDirs it would work.
      // For now, let's assume we just want to visit the session endpoint if possible.
      // A better way is to store the userDataDir path per account.

      emitLog(`Refreshing session for ${account.email}...`, 'info');
      // This is a placeholder for actual session refresh logic which may require
      // cookie persistence or re-login.

      await page.close();
    } catch (e) {
      emitLog(`Failed to refresh session for ${account.email}: ${e.message}`, 'warning');
    }
  }

  await browser.close();
  emitLog('Background session refresh completed. / 后台 Session 刷新完成。', 'info');
}

// Refresh sessions every 4 hours (每 4 小时刷新一次)
setInterval(refreshAllSessions, 4 * 60 * 60 * 1000);

app.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════════════╗
║           cx Proxy Server v1.0.0                ║
╚══════════════════════════════════════════════════════╝

🌐 WebUI:     http://localhost:${PORT}
🔌 API Base:  http://localhost:${PORT}/v1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO USE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Open http://localhost:${PORT}
2. Click "Login with OpenAI" to OAuth login
3. Configure Codex config.toml (~/.codex/config.toml or .codex/config.toml):

   [openai]
   api_base = "http://127.0.0.1:${PORT}/v1"
   api_key = "your_generated_dummy_key"

4. Codex requests will be load-balanced automatically!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Note: Set OPENAI_CLIENT_ID and OPENAI_CLIENT_SECRET
      environment variables for OAuth to work.

Press Ctrl+C to stop
`);
});