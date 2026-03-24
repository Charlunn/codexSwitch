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

search_text = '''function updateCodexConfig(apiKey) {
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

    // Simple TOML manipulation (regex-based for speed)
    const apiBase = `http://127.0.0.1:${PORT}/v1`;

    if (configContent.includes('[openai]')) {
      // Update existing [openai] section
      configContent = configContent.replace(/api_base\s*=\s*".*"/, `api_base = "${apiBase}"`);
      configContent = configContent.replace(/api_key\s*=\s*".*"/, `api_key = "${apiKey}"`);

      if (!configContent.includes('api_base =')) {
         configContent = configContent.replace('[openai]', `[openai]\napi_base = "${apiBase}"`);
      }
      if (!configContent.includes('api_key =')) {
         configContent = configContent.replace('[openai]', `[openai]\napi_key = "${apiKey}"`);
      }
    } else {
      // Create new [openai] section
      configContent += `\n[openai]\napi_base = "${apiBase}"\napi_key = "${apiKey}"\n`;
    }

    fs.writeFileSync(configPath, configContent.trim() + '\n');
    emitLog(`Automatically updated ${configPath} / 已自动更新本地配置文件`, 'success');
    return true;
  } catch (err) {
    emitLog(`Failed to update config: ${err.message}. Please configure manually. / 自动更新配置失败，请手动配置。`, 'warning');
    return false;
  }
}'''

replace_text = '''function updateCodexConfig(apiKey) {
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
      const lines = configContent.split('\\n');
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

      configContent = lines.join('\\n');
    } else {
      configContent += `\\n[openai]\\napi_base = "${apiBase}"\\napi_key = "${apiKey}"\\n`;
    }

    fs.writeFileSync(configPath, configContent.trim() + '\\n');
    emitLog(`Automatically updated ${configPath} / 已自动更新本地配置文件`, 'success');
    return true;
  } catch (err) {
    emitLog(`Failed to update config: ${err.message}. Please configure manually. / 自动更新配置失败，请手动配置。`, 'warning');
    return false;
  }
}'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced')
else:
    print('Failed to replace')
