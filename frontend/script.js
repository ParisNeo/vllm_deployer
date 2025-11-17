document.addEventListener('DOMContentLoaded', () => {
    app.init();
});

const app = {
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
            if (endpoint === '/api/login' && res.redirected) return { success: true };
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        },
        async del(endpoint) {
            const res = await fetch(endpoint, { method: 'DELETE' });
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        }
    },

    ui: {
        showView(viewId) {
            document.getElementById('login-view').classList.add('hidden');
            document.getElementById('dashboard-view').classList.add('hidden');
            document.getElementById(viewId).classList.remove('hidden');
        },
        renderModelList(models) {
            const listEl = document.getElementById('model-list');
            if (models.length === 0) {
                listEl.innerHTML = `<div class="bg-gray-800 p-6 rounded-lg text-center text-gray-400">No models found. Pull a new model to get started.</div>`;
                return;
            }
            listEl.innerHTML = models.map(m => `
                <div class="bg-gray-800 p-4 rounded-lg shadow-md flex items-center justify-between flex-wrap gap-4">
                    <div class="flex-grow">
                        <h4 class="font-bold text-lg">${m.name}</h4>
                        <p class="text-sm text-gray-400">${m.hf_model_id}</p>
                        <div class="text-xs mt-2">
                            <span class="inline-block bg-gray-700 rounded-full px-3 py-1 text-sm font-semibold text-gray-300 mr-2">Size: ${m.size_gb.toFixed(2)} GB</span>
                            <span class="inline-block bg-gray-700 rounded-full px-3 py-1 text-sm font-semibold text-gray-300 mr-2">Type: ${m.model_type}</span>
                             <span class="inline-block ${m.is_running ? 'bg-green-600' : 'bg-yellow-600'} rounded-full px-3 py-1 text-sm font-semibold text-white">${m.is_running ? `Running on port ${m.port}`: m.download_status}</span>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        ${m.download_status === 'completed' && !m.is_running ? `<button onclick="app.startModel(${m.id})" class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Start</button>` : ''}
                        ${m.is_running ? `<button onclick="app.stopModel(${m.id})" class="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Stop</button>` : ''}
                        <button onclick="app.deleteModel(${m.id})" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-3 rounded-md text-sm transition">Delete</button>
                    </div>
                </div>
            `).join('');
        },
        renderSystemInfo(info) {
            const el = document.getElementById('system-info-card');
            el.innerHTML = `
                <h3 class="text-lg font-semibold mb-2">System Information</h3>
                <p class="text-sm">vLLM Version: <strong class="text-indigo-400">${info.vllm_version}</strong></p>
                <p class="text-sm">Mode: <strong class="text-indigo-400">${info.dev_mode ? 'Development' : 'Stable'}</strong></p>
                <button onclick="app.upgradeVLLM()" class="mt-4 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-md transition duration-300">Upgrade vLLM</button>
            `;
        },
        showLogModal(title) {
            document.getElementById('log-modal-title').textContent = title;
            document.getElementById('log-pre').textContent = '';
            document.getElementById('log-modal').classList.remove('hidden');
        },
        hideLogModal() {
            document.getElementById('log-modal').classList.add('hidden');
        },
        appendLog(text) {
            const pre = document.getElementById('log-pre');
            pre.textContent += text;
            pre.scrollTop = pre.scrollHeight;
        }
    },

    async init() {
        try {
            const auth = await this.api.get('/api/check-auth');
            if (auth.authenticated) {
                this.ui.showView('dashboard-view');
                document.getElementById('username-display').textContent = `Welcome, ${auth.username}`;
                this.loadDashboard();
            } else {
                this.ui.showView('login-view');
            }
        } catch (e) {
            this.ui.showView('login-view');
        }
    },

    async login() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('login-error');
        try {
            const res = await this.api.post('/api/login', { username, password });
            if (res.success) {
                window.location.reload();
            }
        } catch (e) {
            errorEl.textContent = 'Login failed. Please check your credentials.';
            errorEl.classList.remove('hidden');
        }
    },

    async logout() {
        await this.api.post('/api/logout', {});
        window.location.reload();
    },

    async loadDashboard() {
        try {
            const models = await this.api.get('/api/models');
            this.ui.renderModelList(models);
            const sysInfo = await this.api.get('/api/system/info');
            this.ui.renderSystemInfo(sysInfo);
        } catch (e) {
            console.error("Failed to load dashboard data", e);
            alert("Failed to load dashboard data. Your session may have expired.");
            this.logout();
        }
    },
    
    listenForLogs(wsPath, modalTitle) {
        this.ui.showLogModal(modalTitle);
        const ws = new WebSocket(`ws://${window.location.host}${wsPath}`);
        ws.onmessage = (event) => {
            if (event.data.startsWith('---') && event.data.endsWith('---')) {
                this.ui.appendLog(`\n\n✅ ${event.data.replaceAll('-', '')} COMPLETE\n`);
                ws.close();
            } else {
                this.ui.appendLog(event.data);
            }
        };
        ws.onerror = (err) => this.ui.appendLog(`\n\n❌ WebSocket Error: ${err}\n`);
        ws.onclose = () => {
            this.loadDashboard();
        };
    },

    async pullModel() {
        const hf_model_id = document.getElementById('hf-model-id').value;
        if (!hf_model_id) return alert('Please enter a HuggingFace Model ID.');
        try {
            const res = await this.api.post('/api/models/pull', { hf_model_id });
            this.listenForLogs(`/ws/pull/${res.model_id}`, `Downloading ${hf_model_id}`);
        } catch (e) {
            alert('Error starting download: ' + e.message);
        }
    },

    async startModel(id) {
        try {
            await this.api.post(`/api/models/${id}/start`);
            this.loadDashboard();
        } catch (e) {
            alert('Failed to start model: ' + e.message);
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

    async upgradeVLLM() {
        if (confirm('This will upgrade vLLM and may require a manager restart. Proceed?')) {
            try {
                await this.api.post('/api/system/upgrade');
                this.listenForLogs('/ws/upgrade', 'Upgrading vLLM');
            } catch (e) {
                alert('Failed to start upgrade: ' + e.message);
            }
        }
    },

    hideLogModal() {
        this.ui.hideLogModal();
    }
};
