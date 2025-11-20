document.addEventListener('DOMContentLoaded', () => {
    app.init();
});

const app = {
    state: {
        refreshInterval: null,
        logWs: null,
        publicKey: null,
        browseLimit: 20,
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

    // Helper moved to app scope to fix "app.formatNumber is not a function"
    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return num;
    },

    ui: {
        showView(viewId) {
            ['login-view', 'dashboard-view'].forEach(id => document.getElementById(id).classList.add('hidden'));
            document.getElementById(viewId).classList.remove('hidden');
        },

        ansiToHtml(text) {
            const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
            const escaped = escapeHtml(text);
            const ansiRegex = /\x1b\[(\d+(?:;\d+)*)m/g;
            const sgrMap = { 0:'ansi-reset', 1:'ansi-bold', 4:'ansi-underline', 30:'ansi-black', 31:'ansi-red', 32:'ansi-green', 33:'ansi-yellow', 34:'ansi-blue', 35:'ansi-magenta', 36:'ansi-cyan', 37:'ansi-white', 90:'ansi-bright-black', 91:'ansi-bright-red', 92:'ansi-bright-green', 93:'ansi-bright-yellow', 94:'ansi-bright-blue', 95:'ansi-bright-magenta', 96:'ansi-bright-cyan', 97:'ansi-bright-white' };
            
            let result = '';
            let lastIndex = 0;
            const stack = [];
            let match;

            while ((match = ansiRegex.exec(escaped)) !== null) {
                const index = match.index;
                const codes = match[1].split(';').map(Number);
                result += escaped.substring(lastIndex, index);
                lastIndex = ansiRegex.lastIndex;
                if (codes.includes(0)) { while (stack.length) { result += '</span>'; stack.pop(); } continue; }
                const classes = codes.map(code => sgrMap[code]).filter(Boolean);
                if (classes.length) { result += `<span class="${classes.join(' ')}">`; stack.push('</span>'); }
            }
            result += escaped.substring(lastIndex);
            while (stack.length) result += stack.pop();
            return result;
        },

        showLogModal(title) {
            document.getElementById('log-modal-title').textContent = title;
            document.getElementById('log-pre').innerHTML = '';
            document.getElementById('log-modal').classList.remove('hidden');
        },
        hideLogModal() {
            document.getElementById('log-modal').classList.add('hidden');
            if (app.state.logWs) { app.state.logWs.close(); app.state.logWs = null; }
        },
        appendLog(text) {
            const pre = document.getElementById('log-pre');
            pre.innerHTML += app.ui.ansiToHtml(text);
            pre.scrollTop = pre.scrollHeight;
        },
        copyLog() {
            const text = document.getElementById('log-pre').innerText;
            navigator.clipboard.writeText(text).then(() => alert('Log copied.'));
        },
        saveLog() {
            const text = document.getElementById('log-pre').innerText;
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `vllm-log-${new Date().toISOString()}.txt`;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 0);
        },

        showEditModal() { document.getElementById('edit-modal').classList.remove('hidden'); },
        hideEditModal() { document.getElementById('edit-modal').classList.add('hidden'); },
        showAdminSettingsModal() { document.getElementById('admin-settings-modal').classList.remove('hidden'); },
        hideAdminSettingsModal() { document.getElementById('admin-settings-modal').classList.add('hidden'); },

        renderAdminSettings(settings) {
            const contentEl = document.getElementById('admin-settings-content');
            let html = `<h4 class="text-md font-semibold mb-4">Change Password</h4>`;
            if (settings.is_password_env_managed) {
                html += `<div class="bg-yellow-900/50 p-3 rounded text-yellow-200 text-sm">Password managed by environment variable.</div>`;
            } else {
                html += `<form id="change-password-form" class="space-y-4">
                            <input type="password" id="current-password" placeholder="Current Password" class="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600">
                            <input type="password" id="new-password" placeholder="New Password" class="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600">
                            <input type="password" id="confirm-password" placeholder="Confirm New" class="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600">
                            <p id="password-change-error" class="text-red-400 text-sm hidden"></p>
                         </form>`;
            }
            contentEl.innerHTML = html;
            document.getElementById('save-admin-settings-btn').disabled = settings.is_password_env_managed;
        },

        renderModelList(models) {
            const listEl = document.getElementById('model-list');
            if (models.length === 0) {
                listEl.innerHTML = `<div class="bg-gray-800 p-6 rounded-lg text-center text-gray-400">No models found. Pull a new model to get started.</div>`;
                return;
            }
            listEl.innerHTML = models.map(m => {
                const statusColors = { running: 'bg-green-600', starting: 'bg-blue-600', error: 'bg-red-600', completed: 'bg-yellow-600' };
                const badgeColor = statusColors[m.status_text] || 'bg-gray-600';
                const quant = m.config && m.config.quantization ? m.config.quantization : 'None';
                return `
                <div class="bg-gray-800 p-4 rounded-lg shadow-md flex flex-wrap gap-4 items-center justify-between">
                    <div class="flex-grow min-w-0">
                        <h4 class="font-bold text-lg text-white">${m.name}</h4>
                        <p class="text-sm text-gray-400">${m.hf_model_id}</p>
                        <div class="flex flex-wrap gap-2 mt-2 text-xs">
                            <span class="bg-gray-700 px-2 py-1 rounded text-gray-300">Size: ${m.size_gb.toFixed(1)} GB</span>
                            <span class="bg-gray-700 px-2 py-1 rounded text-gray-300">Quant: ${quant}</span>
                            <span class="bg-gray-700 px-2 py-1 rounded text-gray-300">Type: ${m.model_type}</span>
                            <span class="px-2 py-1 rounded text-white ${badgeColor}">${m.status_text}</span>
                            ${m.port ? `<span class="bg-gray-700 px-2 py-1 rounded text-gray-300">Port: ${m.port}</span>` : ''}
                        </div>
                        ${m.error_message ? `<p class="text-red-400 text-xs mt-1">${m.error_message}</p>` : ''}
                    </div>
                    <div class="flex gap-2">
                        ${m.status_text === 'error' ? `<button onclick="app.clearError(${m.id})" class="bg-gray-600 hover:bg-gray-500 text-white px-3 py-1 rounded text-sm">Clear</button>` : ''}
                        ${m.status_text !== 'starting' ? `<button onclick="app.openEditModal(${m.id})" class="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm">Edit</button>` : ''}
                        <button onclick="app.showRuntimeLogs(${m.id})" class="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded text-sm">Logs</button>
                        ${m.status_text === 'running' 
                            ? `<button onclick="app.stopModel(${m.id})" class="bg-yellow-600 hover:bg-yellow-500 text-white px-3 py-1 rounded text-sm">Stop</button>` 
                            : `<button onclick="app.startModel(${m.id})" class="bg-green-600 hover:bg-green-500 text-white px-3 py-1 rounded text-sm" ${m.download_status !== 'completed' ? 'disabled' : ''}>Start</button>`}
                        <button onclick="app.deleteModel(${m.id})" class="bg-red-600 hover:bg-red-500 text-white px-3 py-1 rounded text-sm">Delete</button>
                    </div>
                </div>`;
            }).join('');
        },

        renderGpuList(gpus) {
            const list = document.getElementById('gpu-list');
            if (!gpus || gpus.length === 0) { list.innerHTML = '<div class="text-gray-400 p-4 text-center bg-gray-800 rounded">No GPUs</div>'; return; }
            list.innerHTML = gpus.map(g => `
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg border border-gray-700">
                    <div class="flex justify-between mb-2">
                        <span class="font-bold text-white">GPU ${g.id}: ${g.name}</span>
                        <span class="text-gray-400 text-sm">${g.temperature || 0}°C</span>
                    </div>
                    <div class="h-2 bg-gray-700 rounded-full overflow-hidden mb-1">
                        <div class="h-full bg-indigo-500" style="width: ${(g.memory_used_mb/g.memory_total_mb)*100}%"></div>
                    </div>
                    <div class="flex justify-between text-xs text-gray-400 mb-3">
                        <span>${(g.memory_used_mb/1024).toFixed(1)} / ${(g.memory_total_mb/1024).toFixed(1)} GB</span>
                        <span>${g.utilization_percent.toFixed(0)}% Load</span>
                    </div>
                    <div class="space-y-1">
                        ${g.processes.length ? g.processes.map(p => `
                            <div class="flex justify-between items-center bg-gray-700/50 p-1.5 rounded text-xs">
                                <span class="truncate max-w-[120px]" title="${p.process_name}">${p.process_name}</span>
                                <div class="flex items-center gap-2">
                                    <span class="text-gray-400">${p.gpu_memory_usage.toFixed(0)}MB</span>
                                    ${p.managed_model_id 
                                        ? `<button onclick="app.stopModel(${p.managed_model_id})" class="text-yellow-400 hover:text-yellow-300 font-bold">Stop</button>` 
                                        : `<button onclick="app.killGpuProcess(${p.pid})" class="text-red-400 hover:text-red-300 font-bold">Kill</button>`}
                                </div>
                            </div>
                        `).join('') : '<div class="text-xs text-gray-500 italic">Idle</div>'}
                    </div>
                </div>
            `).join('');
        },

        renderDashboardStats(stats) {
            document.getElementById('stats-grid').innerHTML = `
                <div class="bg-gray-800 p-4 rounded shadow border border-gray-700"><div class="text-gray-400 text-sm">CPU</div><div class="text-2xl font-bold">${stats.system_cpu_percent.toFixed(1)}%</div></div>
                <div class="bg-gray-800 p-4 rounded shadow border border-gray-700"><div class="text-gray-400 text-sm">RAM</div><div class="text-2xl font-bold">${stats.system_memory_percent.toFixed(1)}%</div></div>
                <div class="bg-gray-800 p-4 rounded shadow border border-gray-700"><div class="text-gray-400 text-sm">Running</div><div class="text-2xl font-bold">${stats.running_models}</div></div>
                <div class="bg-gray-800 p-4 rounded shadow border border-gray-700"><div class="text-gray-400 text-sm">Total</div><div class="text-2xl font-bold">${stats.total_models}</div></div>
            `;
        },

        renderSystemInfo(info) {
            document.getElementById('system-info-card').innerHTML = `
                <h3 class="font-bold mb-2 text-lg">System</h3>
                <div class="text-sm text-gray-300 space-y-1">
                    <div>vLLM: <span class="text-indigo-400">${info.vllm_version}</span></div>
                    <div>Mode: <span class="text-indigo-400">${info.dev_mode ? 'Dev' : 'Prod'}</span></div>
                </div>
                <button onclick="app.upgradeVLLM()" class="mt-3 w-full bg-indigo-600 hover:bg-indigo-500 text-white py-1.5 rounded text-sm font-bold">Upgrade vLLM</button>
            `;
        },

        renderHubResults(results, append = false) {
            const container = document.getElementById('browse-results');
            if (!container) return;
            
            if (!append && (!results || results.length === 0)) {
                container.innerHTML = `
                    <div class="text-center text-gray-400 mt-10">
                        <p>No models found.</p>
                        <button onclick="app.loadRecommendedModels()" class="mt-2 text-indigo-400 hover:text-indigo-300 underline">View Recommended</button>
                    </div>`;
                return;
            }

            const html = results.map(m => `
                <div class="bg-gray-800 p-3 rounded border border-gray-700 flex justify-between items-center mb-2 hover:bg-gray-750">
                    <div class="min-w-0 mr-2">
                        <div class="font-bold text-indigo-300 text-sm truncate">${m.id}</div>
                        <div class="text-xs text-gray-500 mt-0.5 flex gap-3">
                            <span>⬇ ${app.formatNumber(m.downloads)}</span>
                            <span>♥ ${app.formatNumber(m.likes)}</span>
                            <span>${m.pipeline_tag || 'text-gen'}</span>
                        </div>
                    </div>
                    <button onclick="app.selectModelFromHub('${m.id}')" class="bg-green-700 hover:bg-green-600 text-white text-xs font-bold py-1.5 px-3 rounded">Pull</button>
                </div>
            `).join('');

            if (append) {
                const oldBtn = document.getElementById('load-more-btn-container');
                if (oldBtn) oldBtn.remove();
                container.insertAdjacentHTML('beforeend', html);
            } else {
                container.innerHTML = `
                    <div class="flex justify-between items-center mb-3">
                        <h4 class="text-white font-bold">Hub Search Results</h4>
                        <button onclick="app.loadRecommendedModels()" class="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded">Back to Recommended</button>
                    </div>
                    ${html}`;
            }

            if (results.length > 0) {
                container.insertAdjacentHTML('beforeend', `
                    <div id="load-more-btn-container" class="text-center mt-4 pb-2">
                        <button onclick="app.searchHub(false, true)" class="bg-gray-700 hover:bg-gray-600 text-white text-sm font-bold py-2 px-6 rounded-full transition">
                            Load More
                        </button>
                    </div>
                `);
            }
        },

        renderRecommendedModels(categories) {
             const container = document.getElementById('browse-results');
             if (!container) return;
             
             let html = '<div class="text-center text-gray-500 text-xs mb-4">Hand-picked state-of-the-art models for you</div>';
             for (const [category, models] of Object.entries(categories)) {
                 html += `<h4 class="text-indigo-400 font-bold text-md mt-6 mb-3 uppercase tracking-wider border-b border-gray-700 pb-1">${category}</h4>`;
                 html += models.map(m => `
                    <div class="bg-gray-800 p-4 rounded border border-gray-700 flex justify-between items-center hover:bg-gray-750 transition mb-2">
                        <div class="flex-grow min-w-0 mr-4">
                            <div class="flex items-center gap-2">
                                <h4 class="font-bold text-white text-lg">${m.name}</h4>
                                <span class="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300">${m.id}</span>
                                <span class="text-xs bg-blue-900 text-blue-200 px-2 py-0.5 rounded">${m.size || 'Unknown'}</span>
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
        }
    },

    // Logic
    async init() {
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', e => { e.preventDefault(); this.login(); });
            return;
        }
        document.getElementById('admin-settings-btn').onclick = () => this.openAdminSettingsModal();
        document.getElementById('save-admin-settings-btn').onclick = () => this.changePassword();
        
        try {
            const auth = await this.api.get('/api/check-auth');
            if (auth.authenticated) {
                this.ui.showView('dashboard-view');
                document.getElementById('username-display').textContent = auth.username;
                this.loadDashboard();
            } else {
                this.ui.showView('login-view');
            }
        } catch (e) { this.ui.showView('login-view'); }
    },

    async login() {
        const u = document.getElementById('username').value;
        const p = document.getElementById('password').value;
        try {
            const res = await this.api.post('/api/login', { username: u, password: p });
            if (res.success) location.reload();
        } catch (e) {
            document.getElementById('login-error').textContent = e.message;
            document.getElementById('login-error').classList.remove('hidden');
        }
    },

    async logout() { await this.api.post('/api/logout', {}); location.reload(); },

    async loadDashboard() {
        this.loadModels();
        this.refreshStats();
        if (this.state.refreshInterval) clearInterval(this.state.refreshInterval);
        this.state.refreshInterval = setInterval(() => { this.refreshStats(); this.loadModels(); }, 5000);
    },

    async loadModels() {
        try {
            const models = await this.api.get('/api/models');
            const sorted = this.sortModels(models);
            this.ui.renderModelList(sorted);
        } catch (e) { console.error(e); }
    },

    sortModels(models) {
        const sortMethod = document.getElementById('model-sort').value;
        return models.sort((a, b) => {
            if (sortMethod === 'date_desc') return b.id - a.id;
            if (sortMethod === 'date_asc') return a.id - b.id;
            if (sortMethod === 'name_asc') return a.name.localeCompare(b.name);
            if (sortMethod === 'size_desc') return b.size_gb - a.size_gb;
            if (sortMethod === 'size_asc') return a.size_gb - b.size_gb;
            if (sortMethod === 'type') return a.model_type.localeCompare(b.model_type);
            if (sortMethod === 'quant') {
                const qA = (a.config && a.config.quantization) ? a.config.quantization : 'zzz';
                const qB = (b.config && b.config.quantization) ? b.config.quantization : 'zzz';
                return qA.localeCompare(qB);
            }
            return 0;
        });
    },

    async refreshStats() {
        try {
            const [stats, gpus, sys] = await Promise.all([
                this.api.get('/api/dashboard/stats'),
                this.api.get('/api/gpus'),
                this.api.get('/api/system/info')
            ]);
            this.ui.renderDashboardStats(stats);
            this.ui.renderGpuList(gpus);
            this.ui.renderSystemInfo(sys);
        } catch (e) { console.error(e); }
    },

    _listenToLogs(wsPath, modalTitle) {
        this.ui.showLogModal(modalTitle);
        if (this.state.logWs) { this.state.logWs.close(); }

        const ws = new WebSocket(`ws://${window.location.host}${wsPath}`);
        this.state.logWs = ws;

        ws.onmessage = (event) => {
            this.ui.appendLog(event.data);
        };
        ws.onclose = () => {
            if (this.state.logWs === ws) { 
                this.state.logWs = null;
            }
            if (wsPath.startsWith('/ws/pull') || wsPath.startsWith('/ws/upgrade')) {
                this.loadDashboard();
            }
        };
    },

    async pullModel() {
        const hf_model_id = document.getElementById('hf-model-id').value;
        if (!hf_model_id) return alert('Please enter a HuggingFace Model ID.');
        try {
            const res = await this.api.post('/api/models/pull', { hf_model_id });
            this._listenToLogs(`/ws/pull/${res.model_id}`, `Downloading ${hf_model_id}`);
        } catch (e) {
            alert('Error starting download: ' + e.message);
        }
    },

    async scanModelsFolder() {
        try {
            const res = await this.api.post('/api/models/scan');
            alert(res.message);
            this.loadDashboard();
        } catch (e) {
            alert('Failed to scan models folder: ' + e.message);
        }
    },

    async startModel(id) {
        try {
            await this.api.post(`/api/models/${id}/start`);
            this.loadModels(); 
            this._listenToLogs(`/ws/logs/${id}`, `Starting Model ${id}`);
        } catch (e) {
            alert('Failed to start model: ' + e.message);
            this.loadModels();
        }
    },

    async showRuntimeLogs(id) {
        this._listenToLogs(`/ws/logs/${id}`, `Logs for Model ${id}`);
    },

    async stopModel(id) {
        try {
            await this.api.post(`/api/models/${id}/stop`);
            this.loadDashboard();
        } catch (e) {
            alert('Failed to stop model: ' + e.message);
        }
    },
    
    async encryptPassword(password) {
        if (!this.state.publicKey) {
            try {
                const jwk = await this.api.get('/api/security/public-key');
                this.state.publicKey = await window.crypto.subtle.importKey(
                    "jwk", jwk, { name: "RSA-OAEP", hash: "SHA-256" }, true, ["encrypt"]
                );
            } catch (e) { throw new Error("Encryption error"); }
        }
        const enc = new TextEncoder().encode(password);
        const encrypted = await window.crypto.subtle.encrypt(
            { name: "RSA-OAEP" }, this.state.publicKey, enc
        );
        return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
    },

    async killGpuProcess(pid) {
        if (confirm(`Kill process ${pid}?`)) {
            try {
                await this.api.post(`/api/gpus/kill/${pid}`, {});
                alert('Process killed.');
                this.refreshStats();
            } catch (e) {
                if (e.message.includes('Sudo') || e.message.includes('Permission')) {
                    const password = prompt("Permission denied. Enter sudo password:");
                    if (password) {
                        try {
                             const encryptedPass = await this.encryptPassword(password);
                             await this.api.post(`/api/gpus/kill/${pid}`, { encrypted_sudo_password: encryptedPass });
                             alert('Process killed via sudo.');
                             this.refreshStats();
                        } catch (e2) {
                            alert('Failed to kill process: ' + e2.message);
                        }
                    }
                } else {
                    alert('Failed to kill process: ' + e.message);
                }
            }
        }
    },

    async deleteModel(id) {
        if (confirm('Delete model? This is irreversible.')) {
            try {
                await this.api.del(`/api/models/${id}`);
                this.loadDashboard();
            } catch (e) {
                alert('Failed to delete model: ' + e.message);
            }
        }
    },

    async clearError(id) {
        try {
            await this.api.post(`/api/models/${id}/clear_error`);
            this.loadDashboard();
        } catch (e) {
            alert('Failed to clear error state: ' + e.message);
        }
    },

    async upgradeVLLM() {
        if (confirm('Upgrade vLLM?')) {
            try {
                await this.api.post('/api/system/upgrade');
                this._listenToLogs('/ws/upgrade', 'Upgrading vLLM');
            } catch (e) {
                alert('Failed to start upgrade: ' + e.message);
            }
        }
    },

    togglePasswordVisibility() {
        const passwordInput = document.getElementById('password');
        const eyeOpen = document.getElementById('eye-open-icon');
        const eyeClosed = document.getElementById('eye-closed-icon');
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            eyeOpen.classList.add('hidden');
            eyeClosed.classList.remove('hidden');
        } else {
            passwordInput.type = 'password';
            eyeOpen.classList.remove('hidden');
            eyeClosed.classList.add('hidden');
        }
    },

    async openEditModal(modelId) {
        try {
            const [models, gpus] = await Promise.all([
                this.api.get('/api/models'),
                this.api.get('/api/gpus')
            ]);
            
            const model = models.find(m => m.id === modelId);
            if (!model) {
                alert('Model not found!');
                return;
            }

            const gpuContainer = document.getElementById('gpu-selection-container');
            if (gpus.length === 0) {
                gpuContainer.innerHTML = '<span class="text-red-400 text-xs">No GPUs detected!</span>';
            } else {
                const currentGpuIds = (model.config.gpu_ids || "").split(',').map(s => s.trim());
                gpuContainer.innerHTML = gpus.map(g => `
                    <label class="flex items-center space-x-2 cursor-pointer hover:bg-gray-600 p-1 rounded">
                        <input type="checkbox" 
                               class="gpu-checkbox form-checkbox h-4 w-4 text-indigo-600 bg-gray-800 border-gray-500 rounded focus:ring-indigo-500" 
                               value="${g.id}" 
                               ${currentGpuIds.includes(String(g.id)) ? 'checked' : ''}
                               onchange="app.updateTensorParallelFromSelection()">
                        <span class="text-sm text-gray-200">GPU ${g.id}</span>
                    </label>
                `).join('');
            }

            document.getElementById('edit-model-id').value = model.id;
            document.getElementById('edit-modal-title').textContent = `Edit: ${model.name}`;
            document.getElementById('edit-gpu-ids').value = model.config.gpu_ids || '0';
            document.getElementById('edit-gpu-mem').value = model.config.gpu_memory_utilization;
            document.getElementById('edit-tensor-parallel').value = model.config.tensor_parallel_size;
            document.getElementById('edit-max-len').value = model.config.max_model_len;
            document.getElementById('edit-dtype').value = model.config.dtype;
            document.getElementById('edit-quantization').value = model.config.quantization || '';
            document.getElementById('edit-trust-remote-code').checked = model.config.trust_remote_code;
            document.getElementById('edit-prefix-caching').checked = model.config.enable_prefix_caching;
            
            this.ui.showEditModal();
            this.updateTensorParallelFromSelection();

        } catch (e) {
            alert('Could not fetch model details: ' + e.message);
        }
    },

    updateTensorParallelFromSelection() {
        const checkboxes = document.querySelectorAll('.gpu-checkbox:checked');
        const count = checkboxes.length;
        const tpInput = document.getElementById('edit-tensor-parallel');
        tpInput.value = count > 0 ? count : 1;
    },

    async saveModelConfig() {
        const modelId = document.getElementById('edit-model-id').value;
        
        const checkboxes = document.querySelectorAll('.gpu-checkbox:checked');
        const selectedGpuIds = Array.from(checkboxes).map(cb => cb.value).join(',');
        
        if (!selectedGpuIds) {
            alert("Please select at least one GPU.");
            return;
        }

        const config = {
            gpu_ids: selectedGpuIds,
            gpu_memory_utilization: parseFloat(document.getElementById('edit-gpu-mem').value),
            tensor_parallel_size: checkboxes.length,
            max_model_len: parseInt(document.getElementById('edit-max-len').value),
            dtype: document.getElementById('edit-dtype').value,
            quantization: document.getElementById('edit-quantization').value || null,
            trust_remote_code: document.getElementById('edit-trust-remote-code').checked,
            enable_prefix_caching: document.getElementById('edit-prefix-caching').checked
        };

        try {
            await this.api.put(`/api/models/${modelId}/config`, config);
            this.ui.hideEditModal();
            this.loadModels();
        } catch (e) {
            alert('Failed to save configuration: ' + e.message);
        }
    },

    openBrowseModal() {
        document.getElementById('browse-modal').classList.remove('hidden');
        const container = document.getElementById('browse-results');
        if (!container.innerHTML.trim() || container.innerHTML.includes('Search failed') || container.innerHTML.includes('No models found')) {
            this.loadRecommendedModels();
        }
    },

    hideBrowseModal() {
        document.getElementById('browse-modal').classList.add('hidden');
    },

    async loadRecommendedModels() {
        const container = document.getElementById('browse-results');
        container.innerHTML = '<div class="text-center text-gray-400 mt-4">Loading recommended models...</div>';
        
        try {
            const res = await fetch('/static/models.json');
            if (!res.ok) throw new Error("Failed to load recommended models.");
            const data = await res.json();
            this.ui.renderRecommendedModels(data);
        } catch (e) {
             container.innerHTML = `<div class="text-center text-red-400 mt-4">Error loading recommendations: ${e.message}</div>`;
        }
    },

    async searchHub(reset = true, append = false) {
        const query = document.getElementById('browse-search').value.trim();
        const filter = document.getElementById('browse-filter').value;
        const sort = document.getElementById('browse-sort').value;
        
        if (!query && !filter && !append) {
            return this.loadRecommendedModels();
        }

        if (reset) this.state.browseLimit = 20;
        if (append) this.state.browseLimit += 20;

        const container = document.getElementById('browse-results');
        if (!append) {
            container.innerHTML = '<div class="text-center text-gray-400 mt-10"><svg class="animate-spin h-8 w-8 text-indigo-500 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Searching Hugging Face...</div>';
        } else {
            const btn = document.getElementById('load-more-btn-container');
            if (btn) btn.innerHTML = '<span class="text-sm text-gray-400">Loading...</span>';
        }

        try {
            const params = new URLSearchParams();
            if (query) params.append('query', query);
            if (filter) params.append('filter_type', filter);
            params.append('sort', sort);
            params.append('limit', this.state.browseLimit);
            
            const results = await this.api.get(`/api/hub/search?${params.toString()}`);
            this.ui.renderHubResults(results, append);
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

    hideLogModal() {
        this.ui.hideLogModal();
    },

    copyLog() {
        this.ui.copyLog();
    },
    
    saveLog() {
        this.ui.saveLog();
    },

    hideEditModal() {
        this.ui.hideEditModal();
    },

    async openAdminSettingsModal() {
        try {
            const settings = await this.api.get('/api/admin/settings');
            this.ui.renderAdminSettings(settings);
            this.ui.showAdminSettingsModal();
        } catch (e) {
            alert('Could not load admin settings: ' + e.message);
        }
    },

    hideAdminSettingsModal() {
        this.ui.hideAdminSettingsModal();
    },

    async changePassword() {
        const currentPassword = document.getElementById('current-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const errorEl = document.getElementById('password-change-error');
        
        if (!errorEl) return;
        errorEl.classList.add('hidden');

        if (!newPassword || newPassword !== confirmPassword) {
            errorEl.textContent = 'New passwords do not match or are empty.';
            errorEl.classList.remove('hidden');
            return;
        }
        if (!currentPassword) {
            errorEl.textContent = 'Current password is required.';
            errorEl.classList.remove('hidden');
            return;
        }

        try {
            await this.api.post('/api/admin/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            });
            alert('Password changed successfully!');
            this.hideAdminSettingsModal();
        } catch (e) {
            errorEl.textContent = 'Failed to change password: ' + e.message;
            errorEl.classList.remove('hidden');
        }
    }
};
