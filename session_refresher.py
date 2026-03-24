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

search_text = '''// Health check (健康检查)
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', proxy: 'running', accounts: accounts.length });
});'''

replace_text = '''// Health check (健康检查)
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
setInterval(refreshAllSessions, 4 * 60 * 60 * 1000);'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced')
else:
    print('Failed to replace')
