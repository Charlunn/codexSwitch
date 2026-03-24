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

search_text = '''// Initiate OAuth Login (发起 OAuth 登录)
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

// OAuth Callback (OAuth 回调)
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
});'''

replace_text = '''// Automated Token Capture Flow (自动化 Token 捕获流)
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
              plan: 'plus',
              token: encrypt(session.accessToken),
              quota: existingIdx !== -1 ? accounts[existingIdx].quota : { used: 0, limit: 120, resetAt: new Date(Date.now() + 60*60*1000).toISOString() },
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
});'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced')
else:
    print('Failed to replace')
