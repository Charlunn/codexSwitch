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

search_text = '''                appTitle: "Codex Load Balancer",
                gatewayActive: "API Gateway Active at",
                loginBtn: "Login with OpenAI",
                accountPool: "Account Pool",
                loadingAccounts: "Loading accounts...",
                noAccounts: "No Accounts Connected",
                noAccountsDesc: "Login with OpenAI to add your first account to the pool.",
                addAccountBtn: "Add Account",
                configTitle: "Codex Configuration",
                configDesc: "Edit your <code>~/.codex/config.toml</code> or <code>.codex/config.toml</code> file to use this local gateway.",
                trafficMonitor: "Traffic Monitor",
                statTotal: "Total Requests",
                statSuccess: "Successful",
                statFailed: "Failed / Retried",
                statRate: "Success Rate",
                consoleTitle: "Gateway Console",
                clearLogsBtn: "Clear",
                initConsole: "Initializing console...",
                configCopied: "Configuration copied to clipboard!",
                apiQuotaUsage: "API Quota Usage",
                reqs: "reqs",
                healthy: "Healthy",
                rateLimited: "Rate Limited",
                error: "Error",'''

replace_text = '''                appTitle: "Codex Load Balancer",
                gatewayActive: "API Gateway Active at",
                loginBtn: "Login with OpenAI",
                accountPool: "Account Pool",
                loadingAccounts: "Loading accounts...",
                noAccounts: "No Accounts Connected",
                noAccountsDesc: "Login with OpenAI to add your first account to the pool.",
                addAccountBtn: "Add Account",
                configTitle: "Codex Configuration",
                configDesc: "Edit your <code>~/.codex/config.toml</code> or <code>.codex/config.toml</code> file to use this local gateway.",
                trafficMonitor: "Traffic Monitor",
                statTotal: "Total Requests",
                statSuccess: "Successful",
                statFailed: "Failed / Retried",
                statRate: "Success Rate",
                statAggregated: "Aggregated Quota",
                consoleTitle: "Gateway Console",
                clearLogsBtn: "Clear",
                initConsole: "Initializing console...",
                configCopied: "Configuration copied to clipboard!",
                apiQuotaUsage: "API Quota Usage",
                totalQuota: "Total",
                weeklyQuota: "Weekly",
                fiveHourQuota: "5-Hour",
                reqs: "reqs",
                healthy: "Healthy",
                rateLimited: "Rate Limited",
                error: "Error",'''

if replace_in_file('public/index.html', search_text, replace_text):
    print('Successfully replaced i18n EN')
else:
    print('Failed to replace i18n EN')

search_text = '''                appTitle: "Codex 负载均衡器",
                gatewayActive: "API 代理运行于",
                loginBtn: "使用 OpenAI 登录",
                accountPool: "API 账号池",
                loadingAccounts: "正在加载账号...",
                noAccounts: "暂无连接的账号",
                noAccountsDesc: "请使用 OpenAI 登录，以将您的第一个账号添加到账号池中。",
                addAccountBtn: "添加账号",
                configTitle: "Codex 客户端配置",
                configDesc: "请修改 <code>~/.codex/config.toml</code> 或当前项目的 <code>.codex/config.toml</code> 来使用此本地代理。",
                trafficMonitor: "流量监控",
                statTotal: "总请求数",
                statSuccess: "请求成功",
                statFailed: "失败 / 触发重试",
                statRate: "请求成功率",
                consoleTitle: "代理控制台 (实时日志)",
                clearLogsBtn: "清空",
                initConsole: "控制台初始化中...",
                configCopied: "配置已复制到剪贴板！",
                apiQuotaUsage: "API 额度使用情况",
                reqs: "次",
                healthy: "健康",
                rateLimited: "被限流",
                error: "报错",'''

replace_text = '''                appTitle: "Codex 负载均衡器",
                gatewayActive: "API 代理运行于",
                loginBtn: "使用 OpenAI 登录",
                accountPool: "API 账号池",
                loadingAccounts: "正在加载账号...",
                noAccounts: "暂无连接的账号",
                noAccountsDesc: "请使用 OpenAI 登录，以将您的第一个账号添加到账号池中。",
                addAccountBtn: "添加账号",
                configTitle: "Codex 客户端配置",
                configDesc: "请修改 <code>~/.codex/config.toml</code> 或当前项目的 <code>.codex/config.toml</code> 来使用此本地代理。",
                trafficMonitor: "流量监控",
                statTotal: "总请求数",
                statSuccess: "请求成功",
                statFailed: "失败 / 触发重试",
                statRate: "请求成功率",
                statAggregated: "总额度余量统计",
                consoleTitle: "代理控制台 (实时日志)",
                clearLogsBtn: "清空",
                initConsole: "控制台初始化中...",
                configCopied: "配置已复制到剪贴板！",
                apiQuotaUsage: "API 额度使用情况",
                totalQuota: "总配额",
                weeklyQuota: "周配额",
                fiveHourQuota: "5小时配额",
                reqs: "次",
                healthy: "健康",
                rateLimited: "被限流",
                error: "报错",'''

if replace_in_file('public/index.html', search_text, replace_text):
    print('Successfully replaced i18n ZH')
else:
    print('Failed to replace i18n ZH')

search_text = '''                <div class="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                            <div class="text-gray-400 text-xs uppercase tracking-wider mb-1" data-i18n="statRate">Success Rate</div>
                            <div class="text-2xl font-bold text-blue-400" id="statRate">100%</div>
                        </div>
                    </div>'''

replace_text = '''                <div class="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                            <div class="text-gray-400 text-xs uppercase tracking-wider mb-1" data-i18n="statRate">Success Rate</div>
                            <div class="text-2xl font-bold text-blue-400" id="statRate">100%</div>
                        </div>
                    </div>

                    <div class="mt-6 space-y-3">
                        <div class="text-gray-400 text-xs uppercase tracking-wider mb-2" data-i18n="statAggregated">Aggregated Quota</div>

                        <div class="space-y-1">
                            <div class="flex justify-between text-xs text-gray-500">
                                <span data-i18n="fiveHourQuota">5-Hour</span>
                                <span id="aggFiveHour">0/0</span>
                            </div>
                            <div class="w-full bg-gray-900 rounded-full h-1.5 overflow-hidden border border-gray-800">
                                <div id="aggFiveHourBar" class="bg-blue-500 h-full transition-all duration-500" style="width: 0%"></div>
                            </div>
                        </div>

                        <div class="space-y-1">
                            <div class="flex justify-between text-xs text-gray-500">
                                <span data-i18n="weeklyQuota">Weekly</span>
                                <span id="aggWeekly">0/0</span>
                            </div>
                            <div class="w-full bg-gray-900 rounded-full h-1.5 overflow-hidden border border-gray-800">
                                <div id="aggWeeklyBar" class="bg-indigo-500 h-full transition-all duration-500" style="width: 0%"></div>
                            </div>
                        </div>

                        <div class="space-y-1">
                            <div class="flex justify-between text-xs text-gray-500">
                                <span data-i18n="totalQuota">Total</span>
                                <span id="aggTotal">0/0</span>
                            </div>
                            <div class="w-full bg-gray-900 rounded-full h-1.5 overflow-hidden border border-gray-800">
                                <div id="aggTotalBar" class="bg-purple-500 h-full transition-all duration-500" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>'''

if replace_in_file('public/index.html', search_text, replace_text):
    print('Successfully replaced stats UI')
else:
    print('Failed to replace stats UI')

search_text = '''                document.getElementById('statTotal').textContent = stats.totalRequests || 0;
                document.getElementById('statSuccess').textContent = stats.successfulRequests || 0;
                document.getElementById('statFailed').textContent = stats.failedRequests || 0;

                if (stats.totalRequests > 0) {
                    const rate = Math.round((stats.successfulRequests / stats.totalRequests) * 100);
                    document.getElementById('statRate').textContent = `${rate}%`;
                }'''

replace_text = '''                document.getElementById('statTotal').textContent = stats.totalRequests || 0;
                document.getElementById('statSuccess').textContent = stats.successfulRequests || 0;
                document.getElementById('statFailed').textContent = stats.failedRequests || 0;

                if (stats.totalRequests > 0) {
                    const rate = Math.round((stats.successfulRequests / stats.totalRequests) * 100);
                    document.getElementById('statRate').textContent = `${rate}%`;
                }

                if (stats.aggregated) {
                    const agg = stats.aggregated;
                    document.getElementById('aggTotal').textContent = `${agg.totalUsed} / ${agg.totalLimit}`;
                    document.getElementById('aggTotalBar').style.width = `${Math.min(100, (agg.totalUsed/agg.totalLimit)*100)}%`;

                    document.getElementById('aggWeekly').textContent = `${agg.weeklyUsed} / ${agg.weeklyLimit}`;
                    document.getElementById('aggWeeklyBar').style.width = `${Math.min(100, (agg.weeklyUsed/agg.weeklyLimit)*100)}%`;

                    document.getElementById('aggFiveHour').textContent = `${agg.fiveHourUsed} / ${agg.fiveHourLimit}`;
                    document.getElementById('aggFiveHourBar').style.width = `${Math.min(100, (agg.fiveHourUsed/agg.fiveHourLimit)*100)}%`;
                }'''

if replace_in_file('public/index.html', search_text, replace_text):
    print('Successfully replaced stats JS')
else:
    print('Failed to replace stats JS')

search_text = '''            list.innerHTML = accounts.map((a) => {
                const usagePercent = Math.min(100, (a.quota.used / a.quota.limit) * 100);
                const statusColor = a.status === 'active' ? 'bg-green-500' : (a.status === 'exhausted' ? 'bg-yellow-500' : 'bg-red-500');
                const statusText = a.status === 'active' ? t('healthy') : (a.status === 'exhausted' ? t('rateLimited') : t('error'));

                return `
                <div class="bg-gray-800/50 border border-gray-700 rounded-xl p-5 hover:border-gray-600 transition-colors">
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center font-bold text-gray-300 border border-gray-600">
                                ${a.email[0].toUpperCase()}
                            </div>
                            <div>
                                <h3 class="font-medium text-gray-200">${a.email}</h3>
                                <div class="flex items-center gap-2 mt-1">
                                    <span class="flex items-center gap-1.5 text-xs text-gray-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-800">
                                        <span class="w-1.5 h-1.5 rounded-full ${statusColor}"></span>
                                        ${statusText}
                                    </span>
                                    <span class="text-xs text-gray-500 bg-gray-900 px-2 py-0.5 rounded border border-gray-800 uppercase">${a.plan}</span>
                                </div>
                            </div>
                        </div>
                        <button onclick="deleteAccount('${a.id}')" class="text-gray-500 hover:text-red-400 transition-colors" title="Remove">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>

                    <div>
                        <div class="flex justify-between text-xs text-gray-400 mb-1.5">
                            <span>${t('apiQuotaUsage')}</span>
                            <span>${a.quota.used} / ${a.quota.limit} ${t('reqs')}</span>
                        </div>
                        <div class="w-full bg-gray-900 rounded-full h-2 border border-gray-800 overflow-hidden">
                            <div class="bg-gradient-to-r from-primary to-secondary h-2 rounded-full quota-bar" style="width: ${usagePercent}%"></div>
                        </div>
                    </div>
                </div>
            `}).join('');'''

replace_text = '''            list.innerHTML = accounts.map((a) => {
                const statusColor = a.status === 'active' ? 'bg-green-500' : (a.status === 'exhausted' ? 'bg-yellow-500' : 'bg-red-500');
                const statusText = a.status === 'active' ? t('healthy') : (a.status === 'exhausted' ? t('rateLimited') : t('error'));

                const q = a.quota;
                const fiveHourPct = Math.min(100, (q.fiveHour.used / q.fiveHour.limit) * 100);
                const weeklyPct = Math.min(100, (q.weekly.used / q.weekly.limit) * 100);
                const totalPct = Math.min(100, (q.total.used / q.total.limit) * 100);

                return `
                <div class="bg-gray-800/50 border border-gray-700 rounded-xl p-5 hover:border-gray-600 transition-colors">
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center font-bold text-gray-300 border border-gray-600">
                                ${a.email[0].toUpperCase()}
                            </div>
                            <div>
                                <h3 class="font-medium text-gray-200">${a.email}</h3>
                                <div class="flex items-center gap-2 mt-1">
                                    <span class="flex items-center gap-1.5 text-xs text-gray-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-800">
                                        <span class="w-1.5 h-1.5 rounded-full ${statusColor}"></span>
                                        ${statusText}
                                    </span>
                                    <span class="text-xs text-gray-500 bg-gray-900 px-2 py-0.5 rounded border border-gray-800 uppercase font-bold text-blue-400">${a.level || 'Plus'}</span>
                                </div>
                            </div>
                        </div>
                        <button onclick="deleteAccount('${a.id}')" class="text-gray-500 hover:text-red-400 transition-colors" title="Remove">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>

                    <div class="space-y-3">
                        <div class="text-xs font-semibold text-gray-500 uppercase tracking-tight">${t('apiQuotaUsage')}</div>

                        <div class="space-y-1">
                            <div class="flex justify-between text-[10px] text-gray-400 uppercase">
                                <span>${t('fiveHourQuota')}</span>
                                <span>${q.fiveHour.used} / ${q.fiveHour.limit}</span>
                            </div>
                            <div class="w-full bg-gray-900 rounded-full h-1.5 border border-gray-800 overflow-hidden">
                                <div class="bg-blue-500 h-full rounded-full" style="width: ${fiveHourPct}%"></div>
                            </div>
                        </div>

                        <div class="space-y-1">
                            <div class="flex justify-between text-[10px] text-gray-400 uppercase">
                                <span>${t('weeklyQuota')}</span>
                                <span>${q.weekly.used} / ${q.weekly.limit}</span>
                            </div>
                            <div class="w-full bg-gray-900 rounded-full h-1.5 border border-gray-800 overflow-hidden">
                                <div class="bg-indigo-500 h-full rounded-full" style="width: ${weeklyPct}%"></div>
                            </div>
                        </div>

                        <div class="space-y-1">
                            <div class="flex justify-between text-[10px] text-gray-400 uppercase">
                                <span>${t('totalQuota')}</span>
                                <span>${q.total.used} / ${q.total.limit}</span>
                            </div>
                            <div class="w-full bg-gray-900 rounded-full h-1.5 border border-gray-800 overflow-hidden">
                                <div class="bg-purple-500 h-full rounded-full" style="width: ${totalPct}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `}).join('');'''

if replace_in_file('public/index.html', search_text, replace_text):
    print('Successfully replaced accounts rendering JS')
else:
    print('Failed to replace accounts rendering JS')
