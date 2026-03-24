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

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const userApiKeys = new Map();

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

// ============ 代理服务器 ============

function createProxyServer() {
  const server = http.createServer();

  server.on('connect', (req, clientSocket, head) => {
    const [hostname, port] = req.url.split(':');
    const targetPort = parseInt(port) || 443;

    if (hostname === 'api.openai.com' || hostname.endsWith('.openai.com') || hostname === 'auth.openai.com') {
      const apiKey = req.headers['x-api-key'];

      if (!apiKey || !userApiKeys.has(apiKey)) {
        clientSocket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
        clientSocket.end();
        return;
      }

      const serverSocket = net.connect(targetPort, hostname, () => {
        clientSocket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        serverSocket.write(head);
        serverSocket.pipe(clientSocket);
        clientSocket.pipe(serverSocket);
      });

      serverSocket.on('error', () => {
        proxyStats.failedRequests++;
        clientSocket.end();
      });

    } else {
      const serverSocket = net.connect(targetPort, hostname, () => {
        clientSocket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        serverSocket.write(head);
        serverSocket.pipe(clientSocket);
        clientSocket.pipe(serverSocket);
      });

      serverSocket.on('error', () => clientSocket.end());
    }
  });

  server.on('request', (req, res) => {
    const parsedUrl = url.parse(req.url);

    if (parsedUrl.hostname === 'api.openai.com') {
      handleOpenAIRequest(req, res, parsedUrl);
    } else {
      const proxyReq = http.request({ hostname: parsedUrl.hostname, port: parsedUrl.port, path: parsedUrl.path, method: req.method, headers: req.headers }, (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res);
      });
      req.pipe(proxyReq);
    }
  });

  return server;
}

async function handleOpenAIRequest(req, res, parsedUrl) {
  const apiKey = req.headers['authorization']?.replace('Bearer ', '') || req.headers['x-api-key'];

  if (!apiKey || !userApiKeys.has(apiKey)) {
    return res.status(401).json({
      error: { message: 'Invalid API key provided.', type: 'invalid_request_error' }
    });
  }

  userApiKeys.get(apiKey).requestCount++;
  proxyStats.totalRequests++;

  const availableAccounts = selectAvailableAccounts();

  if (availableAccounts.length === 0) {
    proxyStats.failedRequests++;
    return res.status(503).json({
      error: { message: 'No available accounts to process the request.', type: 'server_error' }
    });
  }

  let lastError = null;

  for (const account of availableAccounts) {
    const token = decrypt(account.token);
    if (!token) {
      account.status = 'error'; // Mark account as bad if token is undecryptable
      lastError = { message: `Could not decrypt token for account ${account.email}.`, type: 'server_error' };
      continue; // Try next account
    }

    try {
      await new Promise((resolve, reject) => {
        const options = {
          hostname: 'api.openai.com',
          port: 443,
          path: parsedUrl.path,
          method: req.method,
          headers: {
            ...req.headers,
            'Authorization': `Bearer ${token}`,
            'host': 'api.openai.com' // Explicitly set host header
          }
        };

        const proxyReq = https.request(options, (proxyRes) => {
          // We consider status codes < 500 as "successful" from the proxy's perspective.
          // The client should handle 4xx errors. We only retry on 5xx or network errors.
          if (proxyRes.statusCode < 500) {
            account.quota.used++;
            proxyStats.successfulRequests++;
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res).on('finish', resolve);
          } else {
             // OpenAI server error (500, 502, 503, etc.), let's try another account.
            account.status = 'error';
            lastError = { message: `OpenAI API returned status ${proxyRes.statusCode}.`, type: 'upstream_error' };
            proxyRes.resume(); // Consume response data to free up memory.
            reject(new Error('Upstream server error'));
          }
        });

        proxyReq.on('error', (err) => {
          // This handles network errors (e.g., DNS resolution, TCP connection timeout).
          account.status = 'error';
          lastError = { message: 'Proxy request failed.', type: 'proxy_error', details: err.message };
          reject(err);
        });

        req.pipe(proxyReq);
      });

      return; // If we get here, the request was successful and piped. Exit the loop.

    } catch (error) {
       // This block is entered if the promise is rejected (network error or 5xx from OpenAI).
       // Log the error and try the next account in the loop.
      console.error(`Account ${account.email} failed. Trying next one. Error: ${error.message}`);
    }
  }

  // If the loop finishes without returning, it means all accounts have failed.
  proxyStats.failedRequests++;
  res.status(503).json({
    error: {
      message: 'All available accounts failed to process the request.',
      type: 'server_error',
      last_error: lastError
    }
  });
}

const proxyServer = createProxyServer();
proxyServer.listen(HTTP_PROXY_PORT, () => {
  console.log(`🔌 Proxy listening on port ${HTTP_PROXY_PORT}`);
});

app.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════════════╗
║           cx Proxy Server v1.0.0                ║
╚══════════════════════════════════════════════════════╝

🌐 WebUI:     http://localhost:${PORT}
🔌 Proxy:    http://localhost:${HTTP_PROXY_PORT}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO USE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Open http://localhost:${PORT}
2. Click "Login with OpenAI" to OAuth login
3. Set system proxy to 127.0.0.1:${HTTP_PROXY_PORT}
4. Codex requests will be load-balanced!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Note: Set OPENAI_CLIENT_ID and OPENAI_CLIENT_SECRET
      environment variables for OAuth to work.

Press Ctrl+C to stop
`);
});