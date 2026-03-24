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

search_text = '''const accounts = [
  {
    id: '1',
    email: 'user1@email.com',
    plan: 'plus',
    token: encrypt('sk-openai-token-xxx'),
    quota: { used: 0, limit: 120, resetAt: new Date(Date.now() + 60*60*1000).toISOString() },
    status: 'active'
  }
];'''

replace_text = '''const accounts = [
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
];'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced accounts')
else:
    print('Failed to replace accounts')

search_text = '''            const newAccount = {
              id: existingIdx !== -1 ? accounts[existingIdx].id : Date.now().toString(),
              email: email,
              name: session.user?.name || '',
              plan: 'plus',
              token: encrypt(session.accessToken),
              quota: existingIdx !== -1 ? accounts[existingIdx].quota : { used: 0, limit: 120, resetAt: new Date(Date.now() + 60*60*1000).toISOString() },
              status: 'active'
            };'''

replace_text = '''            const newAccount = {
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
            };'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced login logic')
else:
    print('Failed to replace login logic')

search_text = '''function selectAvailableAccounts() {
  const available = accounts.filter(a =>
    a.status !== 'exhausted' && a.status !== 'error' && a.quota.used < a.quota.limit
  );
  // Dynamic weight routing: Sort by remaining quota (优先选择额度最充足的账号)
  available.sort((a, b) =>
    (b.quota.limit - b.quota.used) - (a.quota.limit - a.quota.used)
  );
  return available;
}'''

replace_text = '''function selectAvailableAccounts() {
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
}'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced selection logic')
else:
    print('Failed to replace selection logic')

search_text = '''            // Success (200, or client errors like 400, 404 which should be passed back)
            account.quota.used++;
            proxyStats.successfulRequests++;'''

replace_text = '''            // Success (200, or client errors like 400, 404 which should be passed back)
            account.quota.fiveHour.used++;
            account.quota.weekly.used++;
            account.quota.total.used++;
            proxyStats.successfulRequests++;'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced success logic')
else:
    print('Failed to replace success logic')

search_text = '''// Get account list (获取账号列表)
app.get('/api/accounts', (req, res) => {
  res.json(accounts.map(a => ({
    id: a.id,
    email: a.email,
    name: a.name,
    plan: a.plan,
    quota: a.quota,
    status: a.status
  })));
});'''

replace_text = '''// Get account list (获取账号列表)
app.get('/api/accounts', (req, res) => {
  res.json(accounts.map(a => ({
    id: a.id,
    email: a.email,
    name: a.name,
    level: a.level,
    quota: a.quota,
    status: a.status
  })));
});'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced api logic')
else:
    print('Failed to replace api logic')

search_text = '''// Get proxy stats (获取代理统计信息)
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
});'''

replace_text = '''// Get proxy stats (获取代理统计信息)
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
});'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced stats logic')
else:
    print('Failed to replace stats logic')
