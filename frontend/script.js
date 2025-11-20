document.addEventListener('DOMContentLoaded', () => {
    app.init();
});

const app = {
    state: {
        refreshInterval: null,
        logWs: null,
        publicKey: null,
    },
    api: {
        async get(endpoint) {
            const res = await fetch(endpoint);
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        },
        async post(endpoint, body) {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!res.ok) {
                 const error = await res.json().catch(() => ({ detail: 'Request failed' }));
                 throw new Error(error.detail);
            }
            if (endpoint === '/api/login') return { success: true };
            return res.json();
        },
        async put(endpoint, body) {
             const res = await fetch(endpoint, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!res.ok) {
                 const error = await res.json().catch(() => ({ detail: 'Request failed' }));
                 throw new Error(error.detail);
            }
            return res.json();
        },
        async del(endpoint) {
            const res = await fetch(endpoint, { method: 'DELETE' });
            if (!res.ok) {
                const error = await res.json().catch(() => ({ detail: 'Request failed' }));
                throw new Error(error.detail);
            }
            return res.json();
        }
    },

    ui: {
        // ----------------------------------------
        // Safely show/hide main views (login vs dashboard)
        // ----------------------------------------
        showView(viewId) {
            const idsToHide = ['login-view', 'dashboard-view'];
            idsToHide.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.classList.add('hidden');
            });
            const target = document.getElementById(viewId);
            if (target) target.classList.remove('hidden');
        },

        // ----------------------------------------
        // ANSI → HTML conversion (preserves colours in log output)
        // ----------------------------------------
        ansiToHtml(text) {
            const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            })[c]);

            const escaped = escapeHtml(text);
            const ansiRegex = /\x1b\[(\d+(?:;\d+)*)m/g;

            const sgrMap = {
                0: 'ansi-reset',
                1: 'ansi-bold',
                4: 'ansi-underline',
                30: 'ansi-black',
                31: 'ansi-red',
                32: 'ansi-green',
                33: 'ansi-yellow',
                34: 'ansi-blue',
                35: 'ansi-magenta',
                36: 'ansi-cyan',
                37: 'ansi-white',
                90: 'ansi-bright-black',
                91: 'ansi-bright-red',
                92: 'ansi-bright-green',
                93: 'ansi-bright-yellow',
                94: 'ansi-bright-blue',
                95: 'ansi-bright-magenta',
                96: 'ansi-bright-cyan',
                97: 'ansi-bright-white'
            };

            let result = '';
            let lastIndex = 0;
            const stack = [];

            let match;
            while ((match = ansiRegex.exec(escaped)) !== null) {
                const index = match.index;
                const codes = match[1].split(';').map(Number);

                result += escaped.substring(lastIndex, index);
                lastIndex = ansiRegex.lastIndex;

                if (codes.includes(0)) {
                    while (stack.length) {
                        result += '</span>';
                        stack.pop();
                    }
                    continue;
                }

                const classes = codes
                    .map(code => sgrMap[code])
                    .filter(Boolean);

                if (classes.length) {
                    result += `<span class="${classes.join(' ')}">`;
                    stack.push('</span>');
                }
            }

            result += escaped.substring(lastIndex);
            while (stack.length) result += stack.pop();

            return result;
        },

        // ----------------------------------------
        // Log handling
        // ----------------------------------------
        showLogModal(title) {
            const titleEl = document.getElementById('log-modal-title');
            const preEl = document.getElementById('log-pre');
            if (titleEl) titleEl.textContent = title;
            if (preEl) preEl.innerHTML = '';
            const modal = document.getElementById('log-modal');
            if (modal) modal.classList.remove('hidden');
        },
        hideLogModal() {
            const modal = document.getElementById('log-modal');
            if (modal) modal.classList.add('hidden');
            if (app.state.logWs) {
                app.state.logWs.close();
                app.state.logWs = null;
            }
        },
        appendLog(text) {
            const pre = document.getElementById('log-pre');
            if (!pre) return;
            pre.innerHTML += app.ui.ansiToHtml(text);
            pre.scrollTop = pre.scrollHeight;
        },
        
        copyLog() {
            const pre = document.getElementById('log-pre');
            if (!pre) return;
            navigator.clipboard.writeText(pre.innerText).then(() => alert('Log copied.'));
        },
        
        saveLog() {
            const pre = document.getElementById('log-pre');
            if (!pre) return;
            const blob = new Blob([pre.innerText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `vllm-log-${new Date().toISOString()}.txt`;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 0);
        },

        // ----------------------------------------
        // Modal Helpers
        // ----------------------------------------
        showEditModal() { document.getElementById('edit-modal').classList.remove('hidden'); },
        hideEditModal() { document.getElementById('edit-modal').classList.add('hidden'); },
        showAdminSettingsModal() { document.getElementById('admin-settings-modal').classList.remove('hidden'); },
        hideAdminSettingsModal() { document.getElementById('admin-settings-modal').classList.add('hidden'); },

        renderAdminSettings(settings) {
            const contentEl = document.getElementById('admin-settings-content');
            if (!contentEl) return;
            // ... (Simplified for brevity, same logic as before) ...
             let html = `<h4 class="text-md font-semibold mb-4">Change Password</h4>`;
             if (settings.is_password_env_managed) {
                html += `<div class="text-yellow-400 text-sm mb-4">Password managed by env var.</div>`;
             } else {
                html += `<form id="change-password-form" class="space-y-4">
                            <input type="password" id="current-password" placeholder="Current Password" class="w-full px-3 py-2 bg-gray-700 rounded">
                            <input type="password" id="new-password" placeholder="New Password" class="w-full px-3 py-2 bg-gray-700 rounded">
                            <input type="password" id="confirm-password" placeholder="Confirm New" class="w-full px-3 py-2 bg-gray-700 rounded">
                            <p id="password-change-error" class="text-red-400 text-sm hidden"></p>
                         </form>`;
             }
             contentEl.innerHTML = html;
             const saveBtn = document.getElementById('save-admin-settings-btn');
             saveBtn.disabled = settings.is_password_env_managed;
        },

        renderModelList(models) {
            const listEl = document.getElementById('model-list');
            if (!listEl) return;
            if (models.length === 0) {
                listEl.innerHTML = `<div class="bg-gray-800 p-6 rounded-lg text-center text-gray-400">No models found. Pull a new model to get started.</div>`;
                return;
            }
            listEl.innerHTML = models.map(m => {
                const statusMap = {
                    running: `<span class="bg-green-600 text-white">Running on port ${m.port}</span>`,
                    starting: `<span class="bg-blue-600 text-white">Starting...</span>`,
                    error: `<span class="bg-red-600 text-white" title="${m.error_message || ''}">Error</span>`,
                    completed: `<span class="bg-yellow-600 text-white">${m.download_status}</span>`
                };
                const statusBadge = statusMap[m.status_text] || `<span class="bg-gray-600 text-white">${m.status_text}</span>`;
                return `
                <div class="bg-gray-800 p-4 rounded-lg shadow-md flex items-center justify-between flex-wrap gap-4">
                    <div class="flex-grow min-w-0">
                        <h4 class="font-bold text-lg">${m.name}</h4>
                        <p class="text-sm text-gray-400">${m.hf_model_id}</p>
                        <div class="text-xs mt-2 flex flex-wrap gap-2 items-center">
                            <span class="inline-block bg-gray-700 rounded-full px-3 py-1 text-sm font-semibold text-gray-300">Size: ${m.size_gb.toFixed(2)} GB</span>
                            <span class="inline-block bg-gray-700 rounded-full px-3 py-1 text-sm font-semibold text-gray-300">Type: ${m.model_type}</span>
                            <div class="inline-block rounded-full px-3 py-1 text-sm font-semibold">${statusBadge}</div>
                        </div>
                        ${m.status_text === 'error' ? `<p class="text-red-400 text-xs mt-2 break-words">Error: ${m.error_message}</p>` : ''}
                    </div>
                    <div class="flex items-center space-x-2">
                        ${m.status_text === 'error' ? `<button onclick="app.clearError(${m.id})" class="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Clear</button>` : ''}
                        ${m.status_text !== 'starting' ? `<button onclick="app.openEditModal(${m.id})" class="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Edit</button>` : ''}
                        ${(m.status_text === 'running' || m.status_text === 'error') ? `<button onclick="app.showRuntimeLogs(${m.id})" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Logs</button>` : ''}
                        ${m.download_status === 'completed' && !m.is_running && m.status_text !== 'starting' ? `<button onclick="app.startModel(${m.id})" class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Start</button>` : ''}
                        ${m.status_text === 'running' ? `<button onclick="app.stopModel(${m.id})" class="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Stop</button>` : ''}
                        <button onclick="app.deleteModel(${m.id})" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Delete</button>
                    </div>
                </div>
            `}).join('');
        },

        renderSystemInfo(info) {
            const el = document.getElementById('system-info-card');
            if (!el) return;
            el.innerHTML = `
                <h3 class="text-lg font-semibold mb-2">System Information</h3>
                <p class="text-sm">vLLM: <strong class="text-indigo-400">${info.vllm_version}</strong></p>
                <button onclick="app.upgradeVLLM()" class="mt-4 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-md transition duration-300">Upgrade vLLM</button>
            `;
        },

        renderDashboardStats(stats) {
            const el = document.getElementById('stats-grid');
            if (!el) return;
            el.innerHTML = `
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <h4 class="text-sm font-medium text-gray-400">CPU</h4>
                    <p class="text-2xl font-bold">${stats.system_cpu_percent.toFixed(1)}%</p>
                </div>
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <h4 class="text-sm font-medium text-gray-400">RAM</h4>
                    <p class="text-2xl font-bold">${stats.system_memory_percent.toFixed(1)}%</p>
                </div>
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <h4 class="text-sm font-medium text-gray-400">Running</h4>
                    <p class="text-2xl font-bold">${stats.running_models}</p>
                </div>
                 <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <h4 class="text-sm font-medium text-gray-400">Total</h4>
                    <p class="text-2xl font-bold">${stats.total_models}</p>
                </div>
            `;
        },

        renderGpuList(gpus) {
            const el = document.getElementById('gpu-list');
            if (!el) return;
            if (!gpus || gpus.length === 0) {
                el.innerHTML = `<div class="bg-gray-800 p-6 rounded-lg text-center text-gray-400">No GPUs detected.</div>`;
                return;
            }
            el.innerHTML = gpus.map(gpu => {
                const processListHtml = gpu.processes.map(p => {
                    const isManaged = p.managed_model_id !== null;
                    const actionBtn = isManaged 
                        ? `<button onclick="app.stopModel(${p.managed_model_id})" class="bg-yellow-600 hover:bg-yellow-700 text-xs text-white font-bold py-1 px-2 rounded">Stop</button>`
                        : `<button onclick="app.killGpuProcess(${p.pid})" class="bg-red-600 hover:bg-red-700 text-xs text-white font-bold py-1 px-2 rounded">Kill</button>`;
                    
                    return `
                    <div class="flex items-center justify-between bg-gray-700 rounded p-2 mb-1">
                        <div class="truncate pr-2">
                            <span class="text-sm font-mono text-gray-200">${p.process_name}</span>
                            <span class="text-xs text-gray-400 ml-1">(PID: ${p.pid}, ${p.gpu_memory_usage.toFixed(0)} MB)</span>
                        </div>
                        <div class="flex-shrink-0">
                            ${actionBtn}
                        </div>
                    </div>
                `}).join('');

                return `
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <div class="flex justify-between items-center mb-2">
                        <h4 class="font-semibold">GPU ${gpu.id}: ${gpu.name}</h4>
                        <span class="text-sm text-gray-400">${gpu.temperature ? `${gpu.temperature}°C` : ''}</span>
                    </div>
                    <div class="mb-2">
                        <div class="flex justify-between text-xs mb-1">
                            <span>Mem: ${(gpu.memory_used_mb / 1024).toFixed(1)} / ${(gpu.memory_total_mb / 1024).toFixed(1)} GB</span>
                            <span>${gpu.utilization_percent.toFixed(0)}%</span>
                        </div>
                        <div class="w-full bg-gray-700 rounded-full h-2.5">
                            <div class="bg-indigo-600 h-2.5 rounded-full" style="width: ${((gpu.memory_used_mb / gpu.memory_total_mb) * 100).toFixed(0)}%"></div>
                        </div>
                    </div>
                    <div class="mt-3">
                        <h5 class="text-xs text-gray-400 mb-1">Processes:</h5>
                        ${processListHtml || '<div class="text-sm text-gray-500 italic">None</div>'}
                    </div>
                </div>
                `;
            }).join('');
        },

        renderHubResults(results) {
            const container = document.getElementById('browse-results');
            if (!container) return;
            if (!results || results.length === 0) {
                container.innerHTML = '<div class="text-center text-gray-400 mt-10">No models found.</div>';
                return;
            }

            container.innerHTML = results.map(m => `
                <div class="bg-gray-800 p-4 rounded border border-gray-700 flex justify-between items-center hover:bg-gray-750 transition">
                    <div class="flex-grow min-w-0 mr-4">
                        <h4 class="font-bold text-indigo-400 truncate">${m.id}</h4>
                        <div class="text-xs text-gray-400 flex space-x-3 mt-1">
                            <span>⬇️ ${this.formatNumber(m.downloads)}</span>
                            <span>❤️ ${this.formatNumber(m.likes)}</span>
                            <span class="bg-gray-700 px-1.5 rounded text-gray-300">${m.pipeline_tag || 'unknown'}</span>
                        </div>
                    </div>
                    <button onclick="app.selectModelFromHub('${m.id}')" class="bg-green-600 hover:bg-green-700 text-white text-sm font-bold py-2 px-4 rounded transition whitespace-nowrap">
                        Pull
                    </button>
                </div>
            `).join('');
        },
        
        formatNumber(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
            return num;
        }
    },

    // ------------------------------------------
    // App Logic
    // ------------------------------------------
    async init() {
        const loginForm = document.getElementById('login-form');
        if (loginForm) loginForm.addEventListener('submit', (e) => { e.preventDefault(); this.login(); });

        const togglePasswordBtn = document.getElementById('toggle-password-btn');
        if (togglePasswordBtn) togglePasswordBtn.addEventListener('click', () => { this.togglePasswordVisibility(); });

        const adminSettingsBtn = document.getElementById('admin-settings-btn');
        if (adminSettingsBtn) adminSettingsBtn.addEventListener('click', () => this.openAdminSettingsModal());

        const saveAdminSettingsBtn = document.getElementById('save-admin-settings-btn');
        if (saveAdminSettingsBtn) saveAdminSettingsBtn.addEventListener('click', () => this.changePassword());

        try {
            const auth = await this.api.get('/api/check-auth');
            if (auth.authenticated) {
                this.ui.showView('dashboard-view');
                document.getElementById('username-display').textContent = `Welcome, ${auth.username}`;
                this.loadDashboard();
            } else {
                this.ui.showView('login-view');
            }
        } catch (e) { this.ui.showView('login-view'); }
    },

    async login() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('login-error');
        errorEl.classList.add('hidden');
        try {
            const res = await this.api.post('/api/login', { username, password });
            if (res.success) await this.init();
        } catch (e) { errorEl.textContent = 'Login failed: ' + e.message; errorEl.classList.remove('hidden'); }
    },

    async logout() { await this.api.post('/api/logout', {}); await this.init(); },

    async loadDashboard() {
        try {
            const models = await this.api.get('/api/models');
            this.ui.renderModelList(models);
            this.refreshStats();
            if (!this.state.refreshInterval) {
                this.state.refreshInterval = setInterval(() => { this.refreshStats(); this.loadModels(); }, 5000);
            }
        } catch (e) {
            console.error("Dashboard load failed", e);
            if (this.state.refreshInterval) clearInterval(this.state.refreshInterval);
            this.state.refreshInterval = null;
            this.logout();
        }
    },

    async loadModels() {
        const models = await this.api.get('/api/models');
        this.ui.renderModelList(models);
    },

    async refreshStats() {
        try {
            const [stats, gpus, sysInfo] = await Promise.all([
                this.api.get('/api/dashboard/stats'),
                this.api.get('/api/gpus'),
                this.api.get('/api/system/info')
            ]);
            this.ui.renderDashboardStats(stats);
            this.ui.renderGpuList(gpus);
            this.ui.renderSystemInfo(sysInfo);
        } catch(e) {
            console.error("Stats refresh failed", e);
            clearInterval(this.state.refreshInterval);
            this.state.refreshInterval = null;
        }
    },

    _listenToLogs(wsPath, modalTitle, onSpecialMessage = null) {
        this.ui.showLogModal(modalTitle);
        if (this.state.logWs) this.state.logWs.close();

        const ws = new WebSocket(`ws://${window.location.host}${wsPath}`);
        this.state.logWs = ws;

        ws.onmessage = (event) => {
            const data = event.data;
            if (data.startsWith('---') && data.endsWith('---')) {
                if (onSpecialMessage) {
                    onSpecialMessage(data);
                } else {
                    const status = data.replaceAll('-', '').trim();
                    this.ui.appendLog(`\n\nℹ️ ${status}\n`);
                }
            } else {
                this.ui.appendLog(data);
            }
        };
        ws.onerror = () => this.ui.appendLog(`\n\n❌ WebSocket Error\n`);
        ws.onclose = () => {
            if (this.state.logWs === ws) this.state.logWs = null;
            if (wsPath.startsWith('/ws/pull') || wsPath.startsWith('/ws/upgrade')) this.loadDashboard();
        };
    },

    async pullModel() {
        const hf_model_id = document.getElementById('hf-model-id').value;
        if (!hf_model_id) return alert('Enter Model ID');
        try {
            const res = await this.api.post('/api/models/pull', { hf_model_id });
            this._listenToLogs(`/ws/pull/${res.model_id}`, `Downloading ${hf_model_id}`, (message) => {
                const status = message.replaceAll('-', '').trim();
                this.ui.appendLog(`\n\n✅ ${status}\n`);
                this.state.logWs?.close();
            });
        } catch (e) { alert('Download error: ' + e.message); }
    },

    async scanModelsFolder() {
        try {
            const res = await this.api.post('/api/models/scan');
            alert(res.message);
            this.loadDashboard();
        } catch (e) { alert('Scan failed: ' + e.message); }
    },

    async startModel(id) {
        try {
            const models = await this.api.get('/api/models');
            const model = models.find(m => m.id === id);
            await this.api.post(`/api/models/${id}/start`);
            this.loadModels();
            this._listenToLogs(`/ws/logs/${id}`, `Starting ${model.name}`, (message) => {
                const status = message.replaceAll('-', '').trim();
                const isSuccess = status.includes("SUCCESS");
                this.ui.appendLog(`\n\n${isSuccess ? '✅' : '❌'} ${status}\n`);
                setTimeout(() => { this.hideLogModal(); this.loadDashboard(); }, 1500);
            });
        } catch (e) { alert('Start failed: ' + e.message); this.loadModels(); }
    },

    async showRuntimeLogs(id) {
        try {
            const models = await this.api.get('/api/models');
            const model = models.find(m => m.id === id);
            this._listenToLogs(`/ws/logs/${id}`, `Logs for ${model.name}`);
        } catch (e) { alert('Logs error: ' + e.message); }
    },

    async stopModel(id) {
        try { await this.api.post(`/api/models/${id}/stop`); this.loadDashboard(); }
        catch (e) { alert('Stop failed: ' + e.message); }
    },

    async encryptPassword(password) {
        if (!this.state.publicKey) {
            try {
                const jwk = await this.api.get('/api/security/public-key');
                this.state.publicKey = await window.crypto.subtle.importKey("jwk", jwk, { name: "RSA-OAEP", hash: "SHA-256" }, true, ["encrypt"]);
            } catch (e) { throw new Error("Encryption error"); }
        }
        const encoded = new TextEncoder().encode(password);
        const encrypted = await window.crypto.subtle.encrypt({ name: "RSA-OAEP" }, this.state.publicKey, encoded);
        return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
    },

    async killGpuProcess(pid) {
        if (confirm(`KILL process ${pid}?`)) {
            try {
                await this.api.post(`/api/gpus/kill/${pid}`, {});
                alert('Killed.'); this.refreshStats();
            } catch (e) {
                if (e.message.includes('Sudo') || e.message.includes('Permission')) {
                    const password = prompt("Permission denied. Enter sudo password:");
                    if (password) {
                        try {
                             const enc = await this.encryptPassword(password);
                             await this.api.post(`/api/gpus/kill/${pid}`, { encrypted_sudo_password: enc });
                             alert('Killed via sudo.'); this.refreshStats();
                        } catch (e2) { alert('Sudo kill failed: ' + e2.message); }
                    }
                } else { alert('Kill failed: ' + e.message); }
            }
        }
    },

    async deleteModel(id) {
        if (confirm('Delete model files? Irreversible.')) {
            try { await this.api.del(`/api/models/${id}`); this.loadDashboard(); }
            catch (e) { alert('Delete failed: ' + e.message); }
        }
    },

    async clearError(id) {
        try { await this.api.post(`/api/models/${id}/clear_error`); this.loadDashboard(); }
        catch (e) { alert('Clear failed: ' + e.message); }
    },

    async upgradeVLLM() {
        if (confirm('Upgrade vLLM?')) {
            try {
                await this.api.post('/api/system/upgrade');
                this._listenToLogs('/ws/upgrade', 'Upgrading vLLM', (message) => {
                     const status = message.replaceAll('-', '').trim();
                     this.ui.appendLog(`\n\n✅ ${status}\n`);
                     this.state.logWs?.close();
                });
            } catch (e) { alert('Upgrade failed: ' + e.message); }
        }
    },

    togglePasswordVisibility() {
        const pass = document.getElementById('password');
        const open = document.getElementById('eye-open-icon');
        const closed = document.getElementById('eye-closed-icon');
        if (pass.type === 'password') { pass.type = 'text'; open.classList.add('hidden'); closed.classList.remove('hidden'); }
        else { pass.type = 'password'; open.classList.remove('hidden'); closed.classList.add('hidden'); }
    },

    async openEditModal(modelId) {
        try {
            const [models, gpus] = await Promise.all([this.api.get('/api/models'), this.api.get('/api/gpus')]);
            const model = models.find(m => m.id === modelId);
            if (!model) return alert('Model not found');
            
            const container = document.getElementById('gpu-selection-container');
            if (gpus.length === 0) container.innerHTML = '<span class="text-red-400 text-xs">No GPUs</span>';
            else {
                const current = (model.config.gpu_ids || "").split(',').map(s => s.trim());
                container.innerHTML = gpus.map(g => `
                    <label class="flex items-center space-x-2 cursor-pointer hover:bg-gray-600 p-1 rounded">
                        <input type="checkbox" class="gpu-checkbox form-checkbox h-4 w-4 text-indigo-600 bg-gray-800 border-gray-500 rounded" value="${g.id}" ${current.includes(String(g.id)) ? 'checked' : ''} onchange="app.updateTP()">
                        <span class="text-sm text-gray-200">GPU ${g.id}</span>
                    </label>
                `).join('');
            }

            document.getElementById('edit-model-id').value = model.id;
            document.getElementById('edit-modal-title').textContent = `Edit: ${model.name}`;
            document.getElementById('edit-gpu-mem').value = model.config.gpu_memory_utilization;
            document.getElementById('edit-tensor-parallel').value = model.config.tensor_parallel_size;
            document.getElementById('edit-max-len').value = model.config.max_model_len;
            document.getElementById('edit-dtype').value = model.config.dtype;
            document.getElementById('edit-quantization').value = model.config.quantization || '';
            document.getElementById('edit-trust-remote-code').checked = model.config.trust_remote_code;
            document.getElementById('edit-prefix-caching').checked = model.config.enable_prefix_caching;
            
            this.ui.showEditModal();
            this.updateTP();
        } catch (e) { alert('Edit error: ' + e.message); }
    },

    updateTP() {
        const count = document.querySelectorAll('.gpu-checkbox:checked').length;
        document.getElementById('edit-tensor-parallel').value = count > 0 ? count : 1;
    },

    async saveModelConfig() {
        const id = document.getElementById('edit-model-id').value;
        const gpus = Array.from(document.querySelectorAll('.gpu-checkbox:checked')).map(c => c.value).join(',');
        if (!gpus) return alert("Select at least one GPU");
        
        const config = {
            gpu_ids: gpus,
            gpu_memory_utilization: parseFloat(document.getElementById('edit-gpu-mem').value),
            tensor_parallel_size: document.querySelectorAll('.gpu-checkbox:checked').length,
            max_model_len: parseInt(document.getElementById('edit-max-len').value),
            dtype: document.getElementById('edit-dtype').value,
            quantization: document.getElementById('edit-quantization').value || null,
            trust_remote_code: document.getElementById('edit-trust-remote-code').checked,
            enable_prefix_caching: document.getElementById('edit-prefix-caching').checked
        };

        try { await this.api.put(`/api/models/${id}/config`, config); this.ui.hideEditModal(); this.loadModels(); }
        catch (e) { alert('Save failed: ' + e.message); }
    },

    // ----------------------------------------------------------------
    // Hub Browser & Recommended Models
    // ----------------------------------------------------------------
    openBrowseModal() {
        const modal = document.getElementById('browse-modal');
        if (modal) {
            modal.classList.remove('hidden');
            // Load recommended by default if empty or previously showing recommended
            const container = document.getElementById('browse-results');
            if (!container.innerHTML.includes('Pull') || container.innerHTML.includes('Recommended')) {
                this.loadRecommendedModels();
            }
        }
    },

    hideBrowseModal() { document.getElementById('browse-modal').classList.add('hidden'); },

    async loadRecommendedModels() {
        const container = document.getElementById('browse-results');
        container.innerHTML = '<div class="text-center text-gray-400 mt-10">Loading recommended models...</div>';
        
        try {
            // Fetch from static JSON file
            const res = await fetch('/static/models.json');
            if (!res.ok) throw new Error("Failed to load models.json");
            const data = await res.json();
            this.renderRecommendedModels(data);
        } catch (e) {
             container.innerHTML = `<div class="text-center text-red-400 mt-10">Could not load recommended models. Use search above.<br><span class="text-xs">${e.message}</span></div>`;
        }
    },

    renderRecommendedModels(categories) {
        const container = document.getElementById('browse-results');
        if (!container) return;
        
        let html = '';
        for (const [category, models] of Object.entries(categories)) {
            html += `<h4 class="text-indigo-400 font-bold text-md mt-6 mb-3 uppercase tracking-wider border-b border-gray-700 pb-1">${category}</h4>`;
            html += models.map(m => `
                <div class="bg-gray-800 p-4 rounded border border-gray-700 flex justify-between items-center hover:bg-gray-750 transition mb-2">
                    <div class="flex-grow min-w-0 mr-4">
                        <div class="flex items-center gap-2">
                            <h4 class="font-bold text-white text-lg">${m.name}</h4>
                            <span class="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300">${m.id}</span>
                        </div>
                        <p class="text-sm text-gray-400 mt-1">${m.desc}</p>
                    </div>
                    <button onclick="app.selectModelFromHub('${m.id}')" class="bg-purple-600 hover:bg-purple-700 text-white text-sm font-bold py-2 px-4 rounded transition whitespace-nowrap">
                        Pull
                    </button>
                </div>
            `).join('');
        }
        container.innerHTML = html;
    },

    async searchHub() {
        const query = document.getElementById('browse-search').value;
        if (!query) {
            // If search cleared, show recommended again
            return this.loadRecommendedModels();
        }
        
        const filter = document.getElementById('browse-filter').value;
        const container = document.getElementById('browse-results');
        container.innerHTML = '<div class="text-center text-gray-400 mt-10"><svg class="animate-spin h-8 w-8 text-indigo-500 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Searching Hugging Face...</div>';

        try {
            const params = new URLSearchParams();
            if (query) params.append('query', query);
            if (filter) params.append('filter_type', filter);

            const results = await this.api.get(`/api/hub/search?${params.toString()}`);
            this.ui.renderHubResults(results);
        } catch (e) {
            container.innerHTML = `<div class="text-center text-red-400 mt-10">Search failed: ${e.message}</div>`;
        }
    },

    selectModelFromHub(modelId) {
        this.hideBrowseModal();
        document.getElementById('hf-model-id').value = modelId;
        if (confirm(`Pull model '${modelId}' now?`)) {
            this.pullModel();
        }
    },

    hideLogModal() { this.ui.hideLogModal(); },
    copyLog() { this.ui.copyLog(); },
    saveLog() { this.ui.saveLog(); },
    hideEditModal() { this.ui.hideEditModal(); },
    openAdminSettingsModal() { this.ui.showAdminSettingsModal(); this.ui.renderAdminSettings({is_password_env_managed: false}); app.api.get('/api/admin/settings').then(s => this.ui.renderAdminSettings(s)); },
    hideAdminSettingsModal() { this.ui.hideAdminSettingsModal(); },

    async changePassword() {
        const cur = document.getElementById('current-password').value;
        const newP = document.getElementById('new-password').value;
        const conf = document.getElementById('confirm-password').value;
        const err = document.getElementById('password-change-error');
        err.classList.add('hidden');

        if (!newP || newP !== conf) { err.textContent = 'Passwords do not match'; err.classList.remove('hidden'); return; }
        if (!cur) { err.textContent = 'Current password required'; err.classList.remove('hidden'); return; }

        try {
            await this.api.post('/api/admin/change-password', { current_password: cur, new_password: newP });
            alert('Password changed'); this.hideAdminSettingsModal();
        } catch (e) { err.textContent = e.message; err.classList.remove('hidden'); }
    }
};
