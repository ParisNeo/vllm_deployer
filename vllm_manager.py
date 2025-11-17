#!/usr/bin/env python3
"""
vLLM Manager Pro - Advanced Web UI for vLLM Instance Management
Features: DB Backend, UI-based model pulling, Authentication, GPU Management
"""

import asyncio
import json
import os
import subprocess
import signal
import hashlib
import secrets
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from threading import Thread
import queue

from fastapi import FastAPI, HTTPException, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import psutil
import GPUtil
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from huggingface_hub import snapshot_download, HfApi
from huggingface_hub.utils import HfFolder

# ============================================
# Configuration
# ============================================

MANAGER_PORT = int(os.getenv("MANAGER_PORT", 9000))
ADMIN_USERNAME = os.getenv("VLLM_ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = os.getenv("VLLM_ADMIN_PASSWORD_HASH", "")
MODEL_DIR = Path(os.getenv("MODEL_DIR", "./models"))
DATABASE_URL = "sqlite:///vllm_manager.db"
SESSION_FILE = Path(".manager_sessions.json")
SESSION_TIMEOUT = 3600  # 1 hour

# Ensure model dir exists
MODEL_DIR.mkdir(exist_ok=True)

# Generate default password hash if not set
if not ADMIN_PASSWORD_HASH:
    default_password = "admin123"
    ADMIN_PASSWORD_HASH = hashlib.sha256(default_password.encode()).hexdigest()
    print(f"⚠️  WARNING: Using default password '{default_password}'")
    print("   Set VLLM_ADMIN_PASSWORD_HASH environment variable for production!")

# ============================================
# Database Setup
# ============================================

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ModelType:
    TEXT = "text-generation"
    EMBEDDING = "embedding"

class Model(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    hf_model_id = Column(String)
    path = Column(String)
    model_type = Column(String, default=ModelType.TEXT)
    config = Column(JSON, default=lambda: {
        "gpu_memory_utilization": 0.9,
        "tensor_parallel_size": 1,
        "max_model_len": 4096,
        "dtype": "auto",
        "quantization": None,
        "trust_remote_code": False,
        "enable_prefix_caching": False,
    })
    download_status = Column(String, default="not_downloaded")
    download_log = Column(Text, default="")
    size_gb = Column(Float, default=0.0)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================
# Pydantic Models
# ============================================

class ModelConfigUpdate(BaseModel):
    gpu_memory_utilization: float = Field(default=0.9, ge=0.1, le=1.0)
    tensor_parallel_size: int = Field(default=1, ge=1)
    max_model_len: int = Field(default=4096, ge=128)
    dtype: str = "auto"
    quantization: Optional[str] = None
    trust_remote_code: bool = False
    enable_prefix_caching: bool = False

class ModelStatus(BaseModel):
    id: int
    name: str
    hf_model_id: str
    model_type: str
    config: dict
    download_status: str
    size_gb: float
    is_running: bool
    status_text: str = "stopped"
    port: Optional[int] = None
    pid: Optional[int] = None
    gpu_ids: Optional[str] = None
    uptime: Optional[str] = None
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None

class GPUInfo(BaseModel):
    id: int
    name: str
    memory_total_mb: int
    memory_used_mb: int
    memory_free_mb: int
    utilization_percent: float
    temperature: Optional[float] = None
    assigned_models: List[str] = []

class DashboardStats(BaseModel):
    total_models: int
    running_models: int
    stopped_models: int
    total_gpus: int
    total_memory_mb: int
    used_memory_mb: int
    system_cpu_percent: float
    system_memory_percent: float
    uptime: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PullModelRequest(BaseModel):
    hf_model_id: str

# ============================================
# Application Setup
# ============================================

app = FastAPI(
    title="vLLM Manager Pro",
    description="Advanced Web UI for vLLM Model Management",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
running_models: Dict[int, dict] = {} # model_id -> process info
sessions: Dict[str, dict] = {}
download_tasks: Dict[int, dict] = {} # model_id -> {thread, log_queue}
start_time = datetime.now()

# ============================================
# Authentication
# ============================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "username": username,
        "created": datetime.now().isoformat(),
        "expires": (datetime.now() + timedelta(seconds=SESSION_TIMEOUT)).isoformat()
    }
    save_sessions()
    return token

def verify_session(token: Optional[str]) -> bool:
    if not token or token not in sessions:
        return False
    session = sessions[token]
    if datetime.now() > datetime.fromisoformat(session["expires"]):
        del sessions[token]
        save_sessions()
        return False
    return True

def save_sessions():
    with open(SESSION_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)

def load_sessions():
    global sessions
    if SESSION_FILE.exists():
        with open(SESSION_FILE, 'r') as f:
            sessions = json.load(f)

async def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not verify_session(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return sessions[token]["username"]

# ============================================
# Model Downloading
# ============================================

class LogQueueHandler:
    def __init__(self, q):
        self.q = q
    def write(self, text):
        self.q.put(text)
    def flush(self):
        pass

def download_model_task(db_id: int, hf_model_id: str, model_name: str):
    log_q = queue.Queue()
    download_tasks[db_id]['log_queue'] = log_q

    def log(message):
        log_q.put(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")

    try:
        db = SessionLocal()
        model = db.query(Model).filter(Model.id == db_id).first()
        if not model:
            log(f"ERROR: Model with ID {db_id} not found in DB.")
            return

        log(f"Starting download for {hf_model_id}...")
        model.download_status = "downloading"
        db.commit()

        model_path = MODEL_DIR / model_name
        
        token = HfFolder.get_token()
        snapshot_download(
            repo_id=hf_model_id,
            local_dir=model_path,
            local_dir_use_symlinks=False,
            token=token
        )

        log("Download complete. Calculating size...")
        total_size = sum(f.stat().st_size for f in model_path.glob('**/*') if f.is_file())
        size_gb = total_size / (1024**3)

        model.download_status = "completed"
        model.path = str(model_path)
        model.size_gb = size_gb
        
        # Detect model type
        config_path = model_path / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                if any(key in config for key in ['pooling', 'sentence_transformers', 'embedding']):
                    model.model_type = ModelType.EMBEDDING
                    log("Detected embedding model type.")

        db.commit()
        log("Model setup complete and saved to database.")

    except Exception as e:
        log(f"ERROR: {str(e)}")
        if 'db' in locals() and db.is_active:
            model = db.query(Model).filter(Model.id == db_id).first()
            if model:
                model.download_status = "error"
                model.download_log = model.download_log + f"\nERROR: {str(e)}"
                db.commit()
    finally:
        log_q.put(None) # Sentinel to indicate completion
        if 'db' in locals() and db.is_active:
            db.close()


# ============================================
# Utility Functions
# ============================================

def get_gpu_info() -> List[GPUInfo]:
    gpus = []
    try:
        gpu_list = GPUtil.getGPUs()
        for gpu in gpu_list:
            assigned = [m['name'] for m in running_models.values() if str(gpu.id) in m.get("gpu_ids", "0").split(",")]
            gpus.append(GPUInfo(
                id=gpu.id, name=gpu.name, memory_total_mb=int(gpu.memoryTotal),
                memory_used_mb=int(gpu.memoryUsed), memory_free_mb=int(gpu.memoryFree),
                utilization_percent=float(gpu.load * 100), temperature=float(gpu.temperature) if gpu.temperature else None,
                assigned_models=assigned
            ))
    except Exception as e:
        print(f"Error getting GPU info: {e}")
    return gpus

def get_process_info(pid: int) -> dict:
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            return {"memory_mb": proc.memory_info().rss / 1024**2, "cpu_percent": proc.cpu_percent(interval=0.1)}
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {}

async def check_model_health(port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"http://localhost:{port}/health", timeout=2.0)
            return res.status_code == 200
    except:
        return False

def find_available_port(start_port: int = 8000) -> int:
    used_ports = {info["port"] for info in running_models.values()}
    port = start_port
    while port in used_ports:
        port += 1
    return port

# ============================================
# Startup/Shutdown
# ============================================

@app.on_event("startup")
async def startup_event():
    load_sessions()
    print(f"✓ vLLM Manager Pro started on port {MANAGER_PORT}")
    print(f"✓ WebUI: http://localhost:{MANAGER_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    save_sessions()

# ============================================
# API Endpoints
# ============================================

@app.post("/api/login")
async def login(credentials: LoginRequest):
    if credentials.username != ADMIN_USERNAME or hash_password(credentials.password) != ADMIN_PASSWORD_HASH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_session(credentials.username)
    response = JSONResponse(content={"success": True, "username": credentials.username})
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=SESSION_TIMEOUT, samesite="lax")
    return response

@app.post("/api/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token in sessions:
        del sessions[token]
        save_sessions()
    response = JSONResponse(content={"success": True})
    response.delete_cookie("session_token")
    return response

@app.get("/api/check-auth")
async def check_auth(request: Request):
    token = request.cookies.get("session_token")
    is_auth = verify_session(token)
    return {"authenticated": is_auth, "username": sessions[token]["username"] if is_auth else None}

# --- Model Management ---

@app.get("/api/models", response_model=List[ModelStatus])
async def list_models(db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    db_models = db.query(Model).all()
    statuses = []
    for m in db_models:
        is_running = m.id in running_models
        status = ModelStatus(
            id=m.id, name=m.name, hf_model_id=m.hf_model_id, model_type=m.model_type,
            config=m.config, download_status=m.download_status, size_gb=m.size_gb,
            is_running=is_running
        )
        if is_running:
            info = running_models[m.id]
            status.status_text = "running"
            status.port, status.pid, status.gpu_ids = info["port"], info["pid"], info["gpu_ids"]
            proc_info = get_process_info(info['pid'])
            status.memory_usage_mb = proc_info.get("memory_mb")
            status.cpu_percent = proc_info.get("cpu_percent")
        statuses.append(status)
    return statuses

@app.post("/api/models/pull")
async def pull_model(req: PullModelRequest, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    hf_model_id = req.hf_model_id
    model_name = hf_model_id.split('/')[-1]

    if db.query(Model).filter(Model.name == model_name).first():
        raise HTTPException(status_code=400, detail="Model already exists.")

    new_model = Model(name=model_name, hf_model_id=hf_model_id)
    db.add(new_model)
    db.commit()
    db.refresh(new_model)

    thread = Thread(target=download_model_task, args=(new_model.id, hf_model_id, model_name))
    download_tasks[new_model.id] = {'thread': thread}
    thread.start()

    return {"success": True, "message": "Download started.", "model_id": new_model.id}

@app.websocket("/ws/pull/{model_id}")
async def pull_model_ws(websocket: WebSocket, model_id: int):
    await websocket.accept()
    if model_id not in download_tasks:
        await websocket.send_text("ERROR: Task not found.")
        await websocket.close()
        return

    log_q = download_tasks[model_id].get('log_queue')
    if not log_q:
        await websocket.send_text("ERROR: Log queue not ready.")
        await websocket.close()
        return

    try:
        while True:
            log_line = log_q.get()
            if log_line is None: # Sentinel
                break
            await websocket.send_text(log_line)
        await websocket.send_text("---DOWNLOAD-COMPLETE---")
    except WebSocketDisconnect:
        pass
    finally:
        if model_id in download_tasks:
            del download_tasks[model_id]

@app.put("/api/models/{model_id}/config")
async def update_model_config(model_id: int, config: ModelConfigUpdate, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    model.config = config.dict()
    db.commit()
    return {"success": True, "message": "Configuration updated."}

@app.delete("/api/models/{model_id}")
async def delete_model(model_id: int, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    if model_id in running_models:
        raise HTTPException(status_code=400, detail="Cannot delete a running model.")
    
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if model.path and Path(model.path).exists():
        shutil.rmtree(model.path)
    
    db.delete(model)
    db.commit()
    return {"success": True, "message": "Model deleted."}

@app.post("/api/models/{model_id}/start")
async def start_model(model_id: int, gpu_ids: str = "0", db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    if model_id in running_models:
        raise HTTPException(status_code=400, detail="Model is already running")
    
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model or model.download_status != "completed":
        raise HTTPException(status_code=404, detail="Model not found or not downloaded")

    config = model.config
    port = find_available_port()
    
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", str(model.path),
        "--port", str(port),
        "--host", "0.0.0.0",
        "--gpu-memory-utilization", str(config['gpu_memory_utilization']),
        "--tensor-parallel-size", str(config['tensor_parallel_size']),
        "--max-model-len", str(config['max_model_len']),
        "--dtype", config['dtype'],
    ]
    if config.get('quantization'):
        cmd.extend(["--quantization", config['quantization']])
    if config.get('trust_remote_code'):
        cmd.append("--trust-remote-code")
    if config.get('enable_prefix_caching'):
        cmd.append("--enable-prefix-caching")

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu_ids
    
    process = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid)
    await asyncio.sleep(5) # Give it time to start

    if process.poll() is not None:
        raise HTTPException(status_code=500, detail="Failed to start model process")

    running_models[model.id] = {
        "process": process, "pid": process.pid, "port": port, "gpu_ids": gpu_ids, 
        "name": model.name, "start_time": datetime.now().isoformat()
    }
    return {"success": True, "message": "Model started"}

@app.post("/api/models/{model_id}/stop")
async def stop_model(model_id: int, username: str = Depends(get_current_user)):
    if model_id not in running_models:
        raise HTTPException(status_code=404, detail="Model is not running")
    
    info = running_models[model_id]
    os.killpg(os.getpgid(info["pid"]), signal.SIGTERM)
    
    del running_models[model_id]
    return {"success": True, "message": "Model stopped"}

# --- Dashboard & GPU ---

@app.get("/api/gpus", response_model=List[GPUInfo])
async def list_gpus(username: str = Depends(get_current_user)):
    return get_gpu_info()

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    total_models = db.query(Model).count()
    gpus = get_gpu_info()
    uptime = str(datetime.now() - start_time).split('.')[0]
    
    return DashboardStats(
        total_models=total_models, running_models=len(running_models),
        stopped_models=total_models - len(running_models),
        total_gpus=len(gpus),
        total_memory_mb=sum(g.memory_total_mb for g in gpus),
        used_memory_mb=sum(g.memory_used_mb for g in gpus),
        system_cpu_percent=psutil.cpu_percent(interval=0.1),
        system_memory_percent=psutil.virtual_memory().percent, uptime=uptime
    )

# ============================================
# Web UI
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root():
    # Return login page or dashboard
    return HTML_TEMPLATE

# Simple embedded HTML for single-file deployment
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>vLLM Manager Pro</title>
    <!-- Simple styling -->
    <style>
        body { font-family: sans-serif; background-color: #f0f2f5; color: #333; }
        .container { max-width: 1200px; margin: auto; padding: 20px; }
        .hidden { display: none; }
        /* Add more styles for login, dashboard, modals etc. */
    </style>
</head>
<body>
    <div id="app">
        <!-- Login View -->
        <div id="login-view">
            <h2>Login</h2>
            <input id="username" placeholder="Username">
            <input id="password" type="password" placeholder="Password">
            <button onclick="login()">Login</button>
        </div>

        <!-- Dashboard View -->
        <div id="dashboard-view" class="hidden">
            <h1>vLLM Manager</h1>
            <button onclick="logout()">Logout</button>
            
            <!-- Pull Model -->
            <div>
                <h3>Pull New Model</h3>
                <input id="hf-model-id" placeholder="HuggingFace Model ID (e.g., facebook/opt-125m)">
                <button onclick="pullModel()">Pull Model</button>
            </div>

            <!-- Model List -->
            <h3>Managed Models</h3>
            <div id="model-list"></div>
        </div>
        
        <!-- Pull Log Modal -->
        <div id="pull-log-modal" class="hidden">
            <h3>Downloading Model...</h3>
            <pre id="pull-log"></pre>
        </div>
    </div>

<script>
    const api = {
        async get(endpoint) { return fetch(endpoint).then(res => res.json()); },
        async post(endpoint, body) {
            return fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            }).then(res => res.json());
        },
        async put(endpoint, body) { /* ... */ },
        async del(endpoint) { /* ... */ }
    };

    function showView(viewId) {
        document.getElementById('login-view').classList.add('hidden');
        document.getElementById('dashboard-view').classList.add('hidden');
        document.getElementById(viewId).classList.remove('hidden');
    }

    async function login() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const res = await api.post('/api/login', { username, password });
        if (res.success) {
            showView('dashboard-view');
            loadDashboard();
        } else {
            alert('Login failed');
        }
    }

    async function logout() {
        await api.post('/api/logout', {});
        showView('login-view');
    }

    async function pullModel() {
        const hf_model_id = document.getElementById('hf-model-id').value;
        const res = await api.post('/api/models/pull', { hf_model_id });
        if (res.success) {
            listenForPullLogs(res.model_id);
            loadDashboard();
        } else {
            alert('Error: ' + res.detail);
        }
    }
    
    function listenForPullLogs(modelId) {
        document.getElementById('pull-log-modal').classList.remove('hidden');
        const logEl = document.getElementById('pull-log');
        logEl.textContent = '';
        
        const ws = new WebSocket(`ws://${window.location.host}/ws/pull/${modelId}`);
        ws.onmessage = (event) => {
            if (event.data === '---DOWNLOAD-COMPLETE---') {
                ws.close();
                document.getElementById('pull-log-modal').classList.add('hidden');
                loadDashboard();
            } else {
                logEl.textContent += event.data;
            }
        };
        ws.onclose = () => {
             setTimeout(() => {
                document.getElementById('pull-log-modal').classList.add('hidden');
                loadDashboard();
             }, 2000);
        };
    }

    async function loadDashboard() {
        const models = await api.get('/api/models');
        const listEl = document.getElementById('model-list');
        listEl.innerHTML = models.map(m => `
            <div>
                <strong>${m.name}</strong> (${m.hf_model_id}) - Status: ${m.download_status}
                ${m.is_running ? `(Running on port ${m.port})` : ''}
                
                ${m.download_status === 'completed' && !m.is_running ? `<button onclick="startModel(${m.id})">Start</button>` : ''}
                ${m.is_running ? `<button onclick="stopModel(${m.id})">Stop</button>` : ''}
                <button onclick="deleteModel(${m.id})">Delete</button>
            </div>
        `).join('');
    }

    async function startModel(id) {
        await api.post(`/api/models/${id}/start`);
        loadDashboard();
    }
    async function stopModel(id) {
        await api.post(`/api/models/${id}/stop`);
        loadDashboard();
    }
    async function deleteModel(id) {
        if(confirm('Are you sure you want to delete this model and its files?')) {
            await fetch(`/api/models/${id}`, {method: 'DELETE'});
            loadDashboard();
        }
    }

    // Initial check
    api.get('/api/check-auth').then(res => {
        if (res.authenticated) {
            showView('dashboard-view');
            loadDashboard();
        } else {
            showView('login-view');
        }
    });

</script>
</body>
</html>
"""

# ============================================
# Main Execution
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=MANAGER_PORT)
