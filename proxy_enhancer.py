import sys

def replace_in_file(filename, search_text, replace_text):
    with open(filename, 'r') as f:
        content = f.read()
    if search_text not in content:
        print('Search text not found')
        return False
    new_content = content.replace(search_text, replace_text)
    with open(filename, 'w') as f:
        f.write(new_content)
    return True

search_text = '''function selectAvailableAccounts() {
  const available = accounts.filter(a =>
    a.status !== 'exhausted' && a.status !== 'error' && a.quota.used < a.quota.limit
  );
  available.sort((a, b) =>
    (b.quota.limit - b.quota.used) - (a.quota.limit - a.quota.used)
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

  // Allow passing requests even without strict dummy key verification
  // if you want local open access, but here we keep the check:
  if (!apiKey || !userApiKeys.has(apiKey)) {
    emitLog(`Unauthorized request to ${req.originalUrl} (Invalid Key) / 未授权的请求 (API Key 无效)`, 'error');
    return res.status(401).json({
      error: { message: 'Invalid or missing API key. Please configure dummy key in config.toml. / API Key 无效或缺失，请在 config.toml 中配置 dummy key', type: 'invalid_request_error' }
    });
  }

  userApiKeys.get(apiKey).requestCount++;
  proxyStats.totalRequests++;
  emitLog(`Incoming request / 收到请求: ${req.method} ${req.originalUrl}`, 'info');

  const availableAccounts = selectAvailableAccounts();

  if (availableAccounts.length === 0) {
    proxyStats.failedRequests++;
    emitLog('No available accounts in the pool! All accounts exhausted or errored. / 账号池中没有可用账号！所有账号已耗尽或报错。', 'error');
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
        // Strip out host and local authorization from headers (清理不兼容的 Header)
        const headers = { ...req.headers };
        delete headers['host'];
        delete headers['content-length']; // will be recalculated by request (会被 request 库重新计算)

        headers['Authorization'] = `Bearer ${token}`;

        const options = {
          hostname: 'api.openai.com',
          port: 443,
          path: targetPath,
          method: req.method,
          headers: headers
        };

        const proxyReq = https.request(options, (proxyRes) => {
          // If 401, 429 or 5xx, we consider it a failure for this account and retry (如果报错则认为是账号失效/限流，进行重试)
          if (proxyRes.statusCode === 401 || proxyRes.statusCode === 429 || proxyRes.statusCode >= 500) {
            account.status = proxyRes.statusCode === 401 ? 'error' : (proxyRes.statusCode === 429 ? 'exhausted' : account.status);
            lastError = { message: `OpenAI API returned status ${proxyRes.statusCode}.`, type: 'upstream_error' };
            proxyRes.resume(); // consume response to free memory (消费尽返回流以免内存泄漏)
            emitLog(`Account ${account.email} failed with status ${proxyRes.statusCode}. Retrying... / 账号返回 ${proxyRes.statusCode} 错误，正在切换重试...`, 'warning');
            reject(new Error(`Upstream error ${proxyRes.statusCode}`));
          } else {
            // Success (200, 400, 404, etc. - client errors are returned to client)
            account.quota.used++;
            proxyStats.successfulRequests++;
            emitLog(`Request fulfilled using account ${account.email} (Status: ${proxyRes.statusCode}) / 账号处理请求成功 (状态码: ${proxyRes.statusCode})`, 'success');
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res).on('finish', resolve);
          }
        });

        proxyReq.on('error', (err) => {
          account.status = 'error';
          lastError = { message: 'Proxy request failed.', type: 'proxy_error', details: err.message };
          reject(err);
        });

        // Write the buffered body if it exists (重新写入缓存的 Body 以支持 POST 请求重试)
        if (req.body && req.body.length > 0) {
          proxyReq.write(req.body);
        }
        proxyReq.end();
      });

      // If we reach here, the promise resolved, meaning the request was successfully piped back. (执行成功，退出循环)
      return;

    } catch (error) {
      console.error(`[Proxy] Account ${account.email} failed with error: ${error.message}. Switching to next account...`);
      // Warning is already emitted inside the promise reject, but catch network errors here
      if(error.message !== `Upstream error 401` && error.message !== `Upstream error 429` && !error.message.startsWith(`Upstream error 5`)) {
          emitLog(`Network error for account ${account.email}: ${error.message}. Retrying... / 账号网络错误，正在重试...`, 'warning');
      }
    }
  }

  // All accounts failed (所有账号均失败)
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
});'''

replace_text = '''function selectAvailableAccounts() {
  const available = accounts.filter(a =>
    a.status !== 'exhausted' && a.status !== 'error' && a.quota.used < a.quota.limit
  );
  // Dynamic weight routing: Sort by remaining quota (优先选择额度最充足的账号)
  available.sort((a, b) =>
    (b.quota.limit - b.quota.used) - (a.quota.limit - a.quota.used)
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
            account.quota.used++;
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
});'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced')
else:
    print('Failed to replace')
