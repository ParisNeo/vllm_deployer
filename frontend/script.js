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
        // Log handling – now uses ansiToHtml to keep colours
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

        // ----------------------------------------
        // Additional log utilities (copy & save)
        // ----------------------------------------
        copyLog() {
            const pre = document.getElementById('log-pre');
            if (!pre) return;
            const text = pre.innerText;
            if (!navigator.clipboard) {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed'; // avoid scrolling to bottom
                document.body.appendChild(textarea);
                textarea.focus();
                textarea.select();
                try {
                    const successful = document.execCommand('copy');
                    if (successful) {
                        alert('Log copied to clipboard.');
                    } else {
                        alert('Copy command failed. Please select the text manually.');
                    }
                } catch (err) {
                    alert('Copy failed. Please select the text manually.');
                }
                document.body.removeChild(textarea);
                return;
            }
            navigator.clipboard.writeText(text).then(() => {
                alert('Log copied to clipboard.');
            }).catch(() => {
                // Clipboard API failed – fallback
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                document.body.appendChild(textarea);
                textarea.focus();
                textarea.select();
                try {
                    const successful = document.execCommand('copy');
                    if (successful) {
                        alert('Log copied to clipboard (fallback).');
                    } else {
                        alert('Copy failed. Please select the text manually.');
                    }
                } catch (err) {
                    alert('Copy failed. Please select the text manually.');
                }
                document.body.removeChild(textarea);
            });
        },

        saveLog() {
            const pre = document.getElementById('log-pre');
            if (!pre) return;
            const text = pre.innerText;
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            a.download = `vllm-log-${timestamp}.txt`;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 0);
        },

        // ----------------------------------------
        // Remaining UI helpers (unchanged except for safety checks)
        // ----------------------------------------
        showEditModal() {
            const modal = document.getElementById('edit-modal');
            if (modal) modal.classList.remove('hidden');
        },
        hideEditModal() {
            const modal = document.getElementById('edit-modal');
            if (modal) modal.classList.add('hidden');
        },
        showAdminSettingsModal() {
            const modal = document.getElementById('admin-settings-modal');
            if (modal) modal.classList.remove('hidden');
        },
        hideAdminSettingsModal() {
            const modal = document.getElementById('admin-settings-modal');
            if (modal) modal.classList.add('hidden');
        },

        renderAdminSettings(settings) {
            const contentEl = document.getElementById('admin-settings-content');
            const saveBtn = document.getElementById('save-admin-settings-btn');
            if (!contentEl || !saveBtn) return;

            let html = `<h4 class="text-md font-semibold mb-4">Change Password</h4>`;

            if (settings.is_password_env_managed) {
                html += `<div class="bg-yellow-900/50 border border-yellow-700 text-yellow-200 px-4 py-3 rounded relative" role="alert">
                            <strong class="font-bold">Notice:</strong>
                            <span class="block sm:inline"> The admin password is set via an environment variable and cannot be changed from the UI.</span>
                         </div>`;
                saveBtn.disabled = true;
                saveBtn.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                if (settings.is_using_default_password) {
                    html += `<div class="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded relative mb-4" role="alert">
                                <strong class="font-bold">Security Alert:</strong>
                                <span class="block sm:inline"> You are using the default password. Please change it immediately.</span>
                             </div>`;
                }
                html += `<form id="change-password-form" class="space-y-4">
                            <div>
                                <label for="current-password" class="block text-sm font-medium text-gray-300">Current Password</label>
                                <input type="password" id="current-password" class="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md" autocomplete="current-password">
                            </div>
                            <div>
                                <label for="new-password" class="block text-sm font-medium text-gray-300">New Password</label>
                                <input type="password" id="new-password" class="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md" autocomplete="new-password">
                            </div>
                            <div>
                                <label for="confirm-password" class="block text-sm font-medium text-gray-300">Confirm New Password</label>
                                <input type="password" id="confirm-password" class="mt-1 w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md" autocomplete="new-password">
                            </div>
                            <p id="password-change-error" class="text-red-400 text-sm hidden"></p>
                         </form>`;
                saveBtn.disabled = false;
                saveBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }

            contentEl.innerHTML = html;
        },

        renderModelList(models) {
            const listEl = document.getElementById('model-list');
            if (!listEl) return;
            if (models.length === 0) {
                listEl.innerHTML = `<div class="bg-gray-800 p-6 rounded-lg text-center text-gray-400">No models found. Pull a new model or scan the models folder to get started.</div>`;
                return;
            }
            listEl.innerHTML = models.map(m => {
                const statusMap = {
                    running: `<span class="bg-green-600 text-white">Running on port ${m.port}</span>`,
                    starting: `<span class="bg-blue-600 text-white flex items-center"><svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Starting...</span>`,
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
                <p class="text-sm">vLLM Version: <strong class="text-indigo-400">${info.vllm_version}</strong></p>
                <p class="text-sm">Mode: <strong class="text-indigo-400">${info.dev_mode ? 'Development' : 'Stable'}</strong></p>
                <button onclick="app.upgradeVLLM()" class="mt-4 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-md transition duration-300">Upgrade vLLM</button>
            `;
        },

        renderDashboardStats(stats) {
            const el = document.getElementById('stats-grid');
            if (!el) return;
            el.innerHTML = `
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <h4 class="text-sm font-medium text-gray-400">CPU Usage</h4>
                    <p class="text-2xl font-bold">${stats.system_cpu_percent.toFixed(1)}%</p>
                </div>
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <h4 class="text-sm font-medium text-gray-400">RAM Usage</h4>
                    <p class="text-2xl font-bold">${stats.system_memory_percent.toFixed(1)}%</p>
                </div>
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <h4 class="text-sm font-medium text-gray-400">Running Models</h4>
                    <p class="text-2xl font-bold">${stats.running_models}</p>
                </div>
                 <div class="bg-gray-800 p-4 rounded-lg shadow-lg">
                    <h4 class="text-sm font-medium text-gray-400">Total Models</h4>
                    <p class="text-2xl font-bold">${stats.total_models}</p>
                </div>
            `;
        },

        renderGpuList(gpus) {
            const el = document.getElementById('gpu-list');
            if (!el) return;
            if (!gpus || gpus.length === 0) {
                el.innerHTML = `<div class="bg-gray-800 p-6 rounded-lg text-center text-gray-400">No GPUs detected or unable to fetch stats.</div>`;
                return;
            }
            el.innerHTML = gpus.map(gpu => {
                const processListHtml = gpu.processes.map(p => {
                    const isManaged = p.managed_model_id !== null;
                    const actionBtn = isManaged 
                        ? `<button onclick="app.stopModel(${p.managed_model_id})" class="bg-yellow-600 hover:bg-yellow-700 text-xs text-white font-bold py-1 px-2 rounded">Stop (Managed)</button>`
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
                            <span>Memory: ${(gpu.memory_used_mb / 1024).toFixed(2)} / ${(gpu.memory_total_mb / 1024).toFixed(2)} GB</span>
                            <span>Util: ${gpu.utilization_percent.toFixed(0)}%</span>
                        </div>
                        <div class="w-full bg-gray-700 rounded-full h-2.5">
                            <div class="bg-indigo-600 h-2.5 rounded-full" style="width: ${((gpu.memory_used_mb / gpu.memory_total_mb) * 100).toFixed(0)}%"></div>
                        </div>
                    </div>
                    <div class="mt-3">
                        <h5 class="text-xs text-gray-400 mb-1">Running Processes:</h5>
                        ${processListHtml || '<div class="text-sm text-gray-500 italic">No processes detected</div>'}
                    </div>
                </div>
                `;
            }).join('');
        }
    },

    // ------------------------------------------
    // Remaining app logic (init, login, startModel, etc.)
    // ------------------------------------------
    async init() {
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => { e.preventDefault(); this.login(); });
        }

        const togglePasswordBtn = document.getElementById('toggle-password-btn');
        if (togglePasswordBtn) {
            togglePasswordBtn.addEventListener('click', () => { this.togglePasswordVisibility(); });
        }

        const adminSettingsBtn = document.getElementById('admin-settings-btn');
        if (adminSettingsBtn) {
            adminSettingsBtn.addEventListener('click', () => this.openAdminSettingsModal());
        }

        const saveAdminSettingsBtn = document.getElementById('save-admin-settings-btn');
        if (saveAdminSettingsBtn) {
            saveAdminSettingsBtn.addEventListener('click', () => this.changePassword());
        }

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
            if (res.success) { await this.init(); }
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
            console.error("Failed to load dashboard", e);
            if (this.state.refreshInterval) clearInterval(this.state.refreshInterval); this.state.refreshInterval = null;
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
            console.error("Failed to refresh stats", e);
            clearInterval(this.state.refreshInterval); this.state.refreshInterval = null;
        }
    },

    _listenToLogs(wsPath, modalTitle, onSpecialMessage = null) {
        this.ui.showLogModal(modalTitle);
        if (this.state.logWs) { this.state.logWs.close(); }

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
            this._listenToLogs(`/ws/pull/${res.model_id}`, `Downloading ${hf_model_id}`, (message) => {
                const status = message.replaceAll('-', '').trim();
                this.ui.appendLog(`\n\n✅ ${status}\n`);
                this.state.logWs?.close();
            });
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
            const models = await this.api.get('/api/models');
            const model = models.find(m => m.id === id);
            if (!model) throw new Error('Model not found');
            
            await this.api.post(`/api/models/${id}/start`);
            this.loadModels(); // Update UI to show "starting"

            this._listenToLogs(`/ws/logs/${id}`, `Starting ${model.name}`, (message) => {
                const status = message.replaceAll('-', '').trim();
                const isSuccess = status.includes("SUCCESS");
                this.ui.appendLog(`\n\n${isSuccess ? '✅' : '❌'} ${status}\n`);
                
                setTimeout(() => {
                    this.hideLogModal();
                    this.loadDashboard();
                }, 1500);
            });
        } catch (e) {
            alert('Failed to start model: ' + e.message);
            this.loadModels();
        }
    },

    async showRuntimeLogs(id) {
        try {
            const models = await this.api.get('/api/models');
            const model = models.find(m => m.id === id);
            if (!model) throw new Error('Model not found');
            this._listenToLogs(`/ws/logs/${id}`, `Logs for ${model.name}`);
        } catch (e) {
            alert('Could not get logs: ' + e.message);
        }
    },

    async stopModel(id) {
        try {
            await this.api.post(`/api/models/${id}/stop`);
            this.loadDashboard();
        } catch (e) {
            alert('Failed to stop model: ' + e.message);
        }
    },
    
    // Helper to encrypt password using Web Crypto API
    async encryptPassword(password) {
        if (!this.state.publicKey) {
            // Fetch the JWK public key from server
            try {
                const jwk = await this.api.get('/api/security/public-key');
                this.state.publicKey = await window.crypto.subtle.importKey(
                    "jwk",
                    jwk,
                    {
                        name: "RSA-OAEP",
                        hash: "SHA-256"
                    },
                    true,
                    ["encrypt"]
                );
            } catch (e) {
                console.error("Failed to load encryption key:", e);
                throw new Error("Encryption not supported by server or network error.");
            }
        }

        const enc = new TextEncoder();
        const encoded = enc.encode(password);
        
        const encrypted = await window.crypto.subtle.encrypt(
            {
                name: "RSA-OAEP"
            },
            this.state.publicKey,
            encoded
        );
        
        // Convert ArrayBuffer to Base64
        return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
    },

    async killGpuProcess(pid) {
        if (confirm(`Are you sure you want to KILL process ${pid}? This may be an external process.`)) {
            try {
                // First attempt: Try without password
                await this.api.post(`/api/gpus/kill/${pid}`, {});
                alert('Process killed.');
                this.refreshStats();
            } catch (e) {
                // Check if it's a permission issue (403)
                if (e.message.includes('Sudo password required') || e.message.includes('Permission denied')) {
                    const password = prompt("Permission denied. This process requires root privileges.\nPlease enter sudo password (encrypted transmission):");
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
        if (confirm('Are you sure you want to delete this model and its files? This is irreversible.')) {
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
        if (confirm('This will upgrade vLLM and may require a manager restart. Proceed?')) {
            try {
                await this.api.post('/api/system/upgrade');
                this._listenToLogs('/ws/upgrade', 'Upgrading vLLM', (message) => {
                     const status = message.replaceAll('-', '').trim();
                     this.ui.appendLog(`\n\n✅ ${status}\n`);
                     this.state.logWs?.close();
                });
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
            const models = await this.api.get('/api/models');
            const model = models.find(m => m.id === modelId);
            if (!model) {
                alert('Model not found!');
                return;
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
        } catch (e) {
            alert('Could not fetch model details: ' + e.message);
        }
    },

    async saveModelConfig() {
        const modelId = document.getElementById('edit-model-id').value;
        const config = {
            gpu_ids: document.getElementById('edit-gpu-ids').value,
            gpu_memory_utilization: parseFloat(document.getElementById('edit-gpu-mem').value),
            tensor_parallel_size: parseInt(document.getElementById('edit-tensor-parallel').value),
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

    hideLogModal() {
        this.ui.hideLogModal();
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
