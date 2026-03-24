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
    plan: 'plus',
    token: encrypt('sk-openai-token-xxx'),
    quota: { used: 0, limit: 120, resetAt: new Date(Date.now() + 60*60*1000).toISOString() },
    status: 'active'
  }
];

const proxyStats = {
  totalRequests: 0,
  successfulRequests: 0,
  failedRequests: 0
};

// ============ SSE Logs Emitter ============
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

function selectAvailableAccounts() {
  const available = accounts.filter(a =>
    a.status !== 'exhausted' && a.status !== 'error' && a.quota.used < a.quota.limit
  );
  available.sort((a, b) =>
    (b.quota.limit - b.quota.used) - (a.quota.limit - a.quota.used)
  );
  return available;
}

// ============ 反向代理 (Codex 负载均衡网关) ============

app.all('/v1/*', async (req, res) => {
  // 1. Authenticate local Codex client
  const authHeader = req.headers['authorization'];
  let apiKey = null;

  if (authHeader && authHeader.startsWith('Bearer ')) {
    apiKey = authHeader.substring(7);
  } else {
    apiKey = req.headers['x-api-key'];
  }

  // Allow passing requests even without strict dummy key verification
  // if you want local open access, but here we keep the check:
  if (!apiKey || !userApiKeys.has(apiKey)) {
    emitLog(`Unauthorized request to ${req.originalUrl} (Invalid Key)`, 'error');
    return res.status(401).json({
      error: { message: 'Invalid or missing API key. Please configure dummy key in config.toml.', type: 'invalid_request_error' }
    });
  }

  userApiKeys.get(apiKey).requestCount++;
  proxyStats.totalRequests++;
  emitLog(`Incoming request: ${req.method} ${req.originalUrl}`, 'info');

  const availableAccounts = selectAvailableAccounts();

  if (availableAccounts.length === 0) {
    proxyStats.failedRequests++;
    emitLog('No available accounts in the pool! All accounts exhausted or errored.', 'error');
    return res.status(503).json({
      error: { message: 'No available accounts to process the request.', type: 'server_error' }
    });
  }

  let lastError = null;
  const targetPath = req.originalUrl;

  for (const account of availableAccounts) {
    const token = decrypt(account.token);
    if (!token) {
      account.status = 'error';
      lastError = { message: `Could not decrypt token for account ${account.email}.`, type: 'server_error' };
      continue;
    }

    try {
      await new Promise((resolve, reject) => {
        // Strip out host and local authorization from headers
        const headers = { ...req.headers };
        delete headers['host'];
        delete headers['content-length']; // will be recalculated by request

        headers['Authorization'] = `Bearer ${token}`;

        const options = {
          hostname: 'api.openai.com',
          port: 443,
          path: targetPath,
          method: req.method,
          headers: headers
        };

        const proxyReq = https.request(options, (proxyRes) => {
          // If 401, 429 or 5xx, we consider it a failure for this account and retry
          if (proxyRes.statusCode === 401 || proxyRes.statusCode === 429 || proxyRes.statusCode >= 500) {
            account.status = proxyRes.statusCode === 401 ? 'error' : (proxyRes.statusCode === 429 ? 'exhausted' : account.status);
            lastError = { message: `OpenAI API returned status ${proxyRes.statusCode}.`, type: 'upstream_error' };
            proxyRes.resume(); // consume response to free memory
            emitLog(`Account ${account.email} failed with status ${proxyRes.statusCode}. Retrying...`, 'warning');
            reject(new Error(`Upstream error ${proxyRes.statusCode}`));
          } else {
            // Success (200, 400, 404, etc. - client errors are returned to client)
            account.quota.used++;
            proxyStats.successfulRequests++;
            emitLog(`Request fulfilled using account ${account.email} (Status: ${proxyRes.statusCode})`, 'success');
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res).on('finish', resolve);
          }
        });

        proxyReq.on('error', (err) => {
          account.status = 'error';
          lastError = { message: 'Proxy request failed.', type: 'proxy_error', details: err.message };
          reject(err);
        });

        // Write the buffered body if it exists
        if (req.body && req.body.length > 0) {
          proxyReq.write(req.body);
        }
        proxyReq.end();
      });

      // If we reach here, the promise resolved, meaning the request was successfully piped back.
      return;

    } catch (error) {
      console.error(`[Proxy] Account ${account.email} failed with error: ${error.message}. Switching to next account...`);
      // Warning is already emitted inside the promise reject, but catch network errors here
      if(error.message !== `Upstream error 401` && error.message !== `Upstream error 429` && !error.message.startsWith(`Upstream error 5`)) {
          emitLog(`Network error for account ${account.email}: ${error.message}. Retrying...`, 'warning');
      }
    }
  }

  // All accounts failed
  proxyStats.failedRequests++;
  emitLog('All accounts failed to process the request.', 'error');
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

// ============ OAuth 路由 ============

// 发起 OAuth 登录
app.get('/api/auth/login', (req, res) => {
  const state = crypto.randomBytes(16).toString('hex');
  const authUrl = `https://auth.openai.com/authorize?` + querystring.stringify({
    client_id: OPENAI_CLIENT_ID,
    response_type: 'code',
    redirect_uri: CALLBACK_URL,
    scope: 'api.full',
    state: state
  });

  res.redirect(authUrl);
});

// OAuth 回调
app.get('/api/auth/callback', async (req, res) => {
  const { code, state, error } = req.query;

  if (error) {
    return res.redirect('/?error=' + encodeURIComponent(error));
  }

  if (!code) {
    return res.redirect('/?error=no_code');
  }

  try {
    // 用授权码换取 token
    const tokenResponse = await fetch('https://auth.openai.com/oauth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        grant_type: 'authorization_code',
        client_id: OPENAI_CLIENT_ID,
        client_secret: OPENAI_CLIENT_SECRET,
        code: code,
        redirect_uri: CALLBACK_URL
      })
    });

    const tokenData = await tokenResponse.json();

    if (tokenData.error) {
      return res.redirect('/?error=' + encodeURIComponent(tokenData.error_description || tokenData.error));
    }

    // 用 access_token 获取用户信息
    const userResponse = await fetch('https://api.openai.com/v1/me', {
      headers: { 'Authorization': `Bearer ${tokenData.access_token}` }
    });

    const userData = await userResponse.json();

    // 添加账号
    const newAccount = {
      id: Date.now().toString(),
      email: userData.email || 'unknown',
      name: userData.name || '',
      plan: 'plus',
      token: encrypt(tokenData.access_token),
      quota: { used: 0, limit: 120, resetAt: new Date(Date.now() + 60*60*1000).toISOString() },
      status: 'active'
    };

    accounts.push(newAccount);

    // 生成用户 API Key
    const apiKey = generateApiKey();
    userApiKeys.set(apiKey, {
      userId: newAccount.id,
      email: newAccount.email,
      createdAt: new Date().toISOString(),
      requestCount: 0
    });

    // 重定向到成功页面
    res.redirect('/?success=true&apiKey=' + apiKey);

  } catch (err) {
    console.error('OAuth error:', err);
    res.redirect('/?error=oauth_failed');
  }
});

// 获取账号列表
app.get('/api/accounts', (req, res) => {
  res.json(accounts.map(a => ({
    id: a.id,
    email: a.email,
    name: a.name,
    plan: a.plan,
    quota: a.quota,
    status: a.status
  })));
});

// 切换账号
app.put('/api/accounts/:id/switch', (req, res) => {
  accounts.forEach(a => a.isActive = (a.id === req.params.id));
  res.json({ success: true });
});

// 删除账号
app.delete('/api/accounts/:id', (req, res) => {
  const idx = accounts.findIndex(a => a.id === req.params.id);
  if (idx !== -1) accounts.splice(idx, 1);
  res.json({ success: true });
});

// 代理统计
app.get('/api/proxy/stats', (req, res) => {
  res.json({
    ...proxyStats,
    accounts: accounts.map(a => ({
      email: a.email,
      quotaUsed: a.quota.used,
      quotaLimit: a.quota.limit,
      status: a.status
    }))
  });
});

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', proxy: 'running', accounts: accounts.length });
});

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