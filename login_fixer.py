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

search_text = '''    // Redirect user to OpenAI Login
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
          if (session.accessToken) {'''

replace_text = '''    // Redirect user to OpenAI Login
    await page.goto('https://chatgpt.com/auth/login');

    res.send(`
      <html>
        <body style="background: #0f172a; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif;">
          <h2>Please complete login in the opened browser window</h2>
          <p>请在打开的浏览器窗口中完成登录</p>
          <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
            Waiting for session token... / 正在等待捕获 Token...
          </div>
          <p style="font-size: 0.8rem; color: #64748b; margin-top: 20px;">
            Tip: If the browser is stuck on a CAPTCHA, solve it manually. / 提示：如果浏览器卡在人机验证，请手动完成。
          </p>
        </body>
      </html>
    `);

    page.on('response', async (response) => {
      const url = response.url();
      // Listen for both domains as OpenAI is migrating
      if (url.includes('/api/auth/session')) {
        emitLog(`Detected session request: ${url} (Status: ${response.status()}) / 检测到 Session 请求: ${url} (状态: ${response.status()})`, 'info');

        if (response.status() === 200) {
          try {
            const session = await response.json();
            if (session.accessToken) {'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced login logic')
else:
    print('Failed to replace login logic')
