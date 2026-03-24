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

search_text = '''            eventSource.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    addLog(data.message, data.level);
                    // Force refresh stats on important events
                    if (data.level !== 'info') {
                        loadStats();
                        loadAccounts();
                    }
                } catch(err) {}
            };'''

replace_text = '''            eventSource.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);

                    // Handle special system messages for automated login flow (处理自动化登录成功的特殊系统消息)
                    if (data.level === 'system' && data.message.startsWith('SUCCESS_LOGIN:')) {
                        const parts = data.message.split(':');
                        const email = parts[1];
                        const apiKey = parts[2];

                        document.getElementById('dummyKeyDisplay').innerText = apiKey;
                        showToast(t('accountLinked'), 'success');
                        addLog(`Account ${email} linked successfully!`, 'success');
                        loadAccounts();
                        loadStats();
                        return;
                    }

                    addLog(data.message, data.level);
                    // Force refresh stats on important events
                    if (data.level !== 'info') {
                        loadStats();
                        loadAccounts();
                    }
                } catch(err) {}
            };'''

if replace_in_file('public/index.html', search_text, replace_text):
    print('Successfully replaced')
else:
    print('Failed to replace')
