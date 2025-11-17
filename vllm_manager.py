#!/usr/bin/env python3
"""
vLLM Manager Pro - Advanced Web UI for vLLM Instance Management
Features: DB Backend, UI-based model pulling, UI-based upgrades, Authentication, GPU Management
"""

import asyncio
import json
import os
import subprocess
import signal
import hashlib
import secrets
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from threading import Thread
import queue

from fastapi import FastAPI, HTTPException, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import psutil
import GPUtil
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from huggingface_hub import snapshot_download, HfFolder

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

MODEL_DIR.mkdir(exist_ok=True)

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
        "gpu_memory_utilization": 0.9, "tensor_parallel_size": 1, "max_model_len": 4096,
        "dtype": "auto", "quantization": None, "trust_remote_code": False,
        "enable_prefix_caching": False,
    })
    download_status = Column(String, default="not_downloaded")
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
    gpu_memory_utilization: float
    tensor_parallel_size: int
    max_model_len: int
    dtype: str
    quantization: Optional[str]
    trust_remote_code: bool
    enable_prefix_caching: bool

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

class GPUInfo(BaseModel):
    id: int
    name: str
    memory_total_mb: int
    memory_used_mb: int
    utilization_percent: float
    temperature: Optional[float]
    assigned_models: List[str]

class LoginRequest(BaseModel):
    username: str
    password: str

class PullModelRequest(BaseModel):
    hf_model_id: str
    
class SystemInfo(BaseModel):
    vllm_version: str
    dev_mode: bool

# ============================================
# App Setup
# ============================================

app = FastAPI(title="vLLM Manager Pro", version="3.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Global state
running_models: Dict[int, dict] = {}
sessions: Dict[str, dict] = {}
download_tasks: Dict[int, dict] = {}
upgrade_task: Dict = {}
start_time = datetime.now()

# ============================================
# Authentication
# ============================================

def hash_password(password: str) -> str: return hashlib.sha256(password.encode()).hexdigest()

def save_sessions():
    with open(SESSION_FILE, 'w') as f: json.dump(sessions, f, indent=2)

def load_sessions():
    global sessions
    if SESSION_FILE.exists():
        with open(SESSION_FILE, 'r') as f: sessions = json.load(f)

def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "username": username, "created": datetime.now().isoformat(),
        "expires": (datetime.now() + timedelta(seconds=SESSION_TIMEOUT)).isoformat()
    }
    save_sessions()
    return token

def verify_session(token: Optional[str]) -> bool:
    if not token or token not in sessions: return False
    session = sessions[token]
    if datetime.now() > datetime.fromisoformat(session["expires"]):
        del sessions[token]
        save_sessions()
        return False
    return True

async def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not verify_session(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return sessions[token]["username"]

# ============================================
# Background Tasks (Download & Upgrade)
# ============================================

def download_model_task(db_id: int, hf_model_id: str, model_name: str):
    log_q = queue.Queue()
    download_tasks[db_id]['log_queue'] = log_q
    def log(message): log_q.put(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
    try:
        db = SessionLocal()
        model = db.query(Model).filter(Model.id == db_id).first()
        if not model:
            log(f"ERROR: Model with ID {db_id} not found in DB."); return
        log(f"Starting download for {hf_model_id}..."); model.download_status = "downloading"; db.commit()
        model_path = MODEL_DIR / model_name
        snapshot_download(repo_id=hf_model_id, local_dir=model_path, local_dir_use_symlinks=False, token=HfFolder.get_token())
        log("Download complete. Calculating size...")
        total_size = sum(f.stat().st_size for f in model_path.glob('**/*') if f.is_file())
        model.download_status = "completed"; model.path = str(model_path); model.size_gb = total_size / (1024**3)
        config_path = model_path / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                if any(k in json.load(f) for k in ['pooling', 'sentence_transformers', 'embedding']):
                    model.model_type = ModelType.EMBEDDING; log("Detected embedding model type.")
        db.commit(); log("Model setup complete.")
    except Exception as e:
        log(f"ERROR: {str(e)}")
        if 'db' in locals() and db.is_active:
            model = db.query(Model).filter(Model.id == db_id).first()
            if model: model.download_status = "error"; db.commit()
    finally:
        log_q.put(None)
        if 'db' in locals() and db.is_active: db.close()

def upgrade_vllm_task():
    log_q = queue.Queue(); upgrade_task['log_queue'] = log_q
    def log(message): log_q.put(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
    try:
        log("Starting vLLM upgrade..."); venv_python = sys.executable; install_dir = Path(__file__).parent.resolve()
        dev_mode, _ = get_system_info_sync()
        if dev_mode:
            log("Dev mode: upgrading from git..."); vllm_source_dir = install_dir / "vllm-source"
            if not vllm_source_dir.exists(): raise FileNotFoundError("vllm-source directory not found")
            log("Running 'git pull'..."); git_proc = subprocess.run(["git", "pull"], cwd=vllm_source_dir, capture_output=True, text=True)
            log(git_proc.stdout);
            if git_proc.returncode != 0: log(f"ERROR:\n{git_proc.stderr}"); raise subprocess.CalledProcessError(git_proc.returncode, git_proc.args, stderr=git_proc.stderr)
            command = [venv_python, "-m", "pip", "install", "-e", "."]; cwd = vllm_source_dir
        else:
            log("Stable mode: upgrading from PyPI..."); command = [venv_python, "-m", "pip", "install", "--upgrade", "vllm"]; cwd = install_dir
        log(f"Executing: {' '.join(str(c) for c in command)}")
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(process.stdout.readline, ''): log(line.strip())
        process.wait()
        if process.returncode != 0: raise subprocess.CalledProcessError(process.returncode, command)
        log("\n✅ Upgrade complete! Please RESTART the manager to apply changes.")
    except Exception as e:
        log(f"\n❌ ERROR: {str(e)}")
    finally:
        log_q.put(None); upgrade_task.clear()

# ============================================
# Utilities
# ============================================

def get_system_info_sync():
    install_info_path = Path(__file__).parent.resolve() / ".install_info"
    dev_mode = False; vllm_version = "Unknown"
    if install_info_path.exists():
        with open(install_info_path, 'r') as f:
            for line in f:
                if "DEV_MODE=true" in line: dev_mode = True
                if line.startswith("VLLM_VERSION="): vllm_version = line.strip().split("=")[1]
    return dev_mode, vllm_version

def find_available_port(start_port: int = 8000) -> int:
    used_ports = {info["port"] for info in running_models.values()}
    port = start_port
    while port in used_ports: port += 1
    return port

# ============================================
# API Endpoints
# ============================================

@app.on_event("startup")
async def startup_event(): load_sessions()

@app.post("/api/login")
async def login(req: LoginRequest):
    if req.username != ADMIN_USERNAME or hash_password(req.password) != ADMIN_PASSWORD_HASH:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_session(req.username)
    res = FileResponse("frontend/index.html"); res.set_cookie(key="session_token", value=token, httponly=True, max_age=SESSION_TIMEOUT, samesite="lax")
    return res

@app.post("/api/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token in sessions: del sessions[token]; save_sessions()
    res = FileResponse("frontend/index.html"); res.delete_cookie("session_token")
    return res

@app.get("/api/check-auth")
async def check_auth(request: Request):
    token = request.cookies.get("session_token"); is_auth = verify_session(token)
    return {"authenticated": is_auth, "username": sessions[token]["username"] if is_auth else None}

@app.get("/api/models", response_model=List[ModelStatus])
async def list_models(db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    db_models = db.query(Model).all()
    statuses = []
    for m in db_models:
        is_running = m.id in running_models
        status = ModelStatus(id=m.id, name=m.name, hf_model_id=m.hf_model_id, model_type=m.model_type,
                             config=m.config, download_status=m.download_status, size_gb=m.size_gb, is_running=is_running)
        if is_running:
            info = running_models[m.id]
            status.status_text = "running"; status.port, status.pid, status.gpu_ids = info["port"], info["pid"], info["gpu_ids"]
        statuses.append(status)
    return statuses

@app.post("/api/models/pull")
async def pull_model(req: PullModelRequest, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    model_name = req.hf_model_id.split('/')[-1]
    if db.query(Model).filter(Model.name == model_name).first(): raise HTTPException(400, "Model already exists.")
    new_model = Model(name=model_name, hf_model_id=req.hf_model_id); db.add(new_model); db.commit(); db.refresh(new_model)
    thread = Thread(target=download_model_task, args=(new_model.id, req.hf_model_id, model_name))
    download_tasks[new_model.id] = {'thread': thread}; thread.start()
    return {"success": True, "model_id": new_model.id}

@websocket_endpoint("/ws/pull/{model_id}")
async def pull_model_ws(websocket: WebSocket, model_id: int):
    await websocket.accept()
    if model_id not in download_tasks or 'log_queue' not in download_tasks[model_id]:
        await websocket.close(); return
    log_q = download_tasks[model_id].get('log_queue')
    try:
        while True:
            log_line = log_q.get()
            if log_line is None: break
            await websocket.send_text(log_line)
        await websocket.send_text("---DOWNLOAD-COMPLETE---")
    finally:
        if model_id in download_tasks: del download_tasks[model_id]

@app.delete("/api/models/{model_id}")
async def delete_model(model_id: int, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    if model_id in running_models: raise HTTPException(400, "Cannot delete a running model.")
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model: raise HTTPException(404, "Model not found")
    if model.path and Path(model.path).exists(): shutil.rmtree(model.path)
    db.delete(model); db.commit()
    return {"success": True}

@app.post("/api/models/{model_id}/start")
async def start_model(model_id: int, gpu_ids: str = "0", db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    if model_id in running_models: raise HTTPException(400, "Model is already running")
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model or model.download_status != "completed": raise HTTPException(404, "Model not downloaded")
    config = model.config; port = find_available_port()
    cmd = [ "python", "-m", "vllm.entrypoints.openai.api_server", "--model", str(model.path), "--port", str(port),
            "--host", "0.0.0.0", "--gpu-memory-utilization", str(config['gpu_memory_utilization']),
            "--tensor-parallel-size", str(config['tensor_parallel_size']), "--max-model-len", str(config['max_model_len']),
            "--dtype", config['dtype']]
    if config.get('quantization'): cmd.extend(["--quantization", config['quantization']])
    if config.get('trust_remote_code'): cmd.append("--trust-remote-code")
    env = os.environ.copy(); env["CUDA_VISIBLE_DEVICES"] = gpu_ids
    process = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid)
    await asyncio.sleep(5)
    if process.poll() is not None: raise HTTPException(500, "Failed to start model")
    running_models[model.id] = {"process": process, "pid": process.pid, "port": port, "gpu_ids": gpu_ids, "name": model.name}
    return {"success": True}

@app.post("/api/models/{model_id}/stop")
async def stop_model(model_id: int, username: str = Depends(get_current_user)):
    if model_id not in running_models: raise HTTPException(404, "Model is not running")
    info = running_models[model_id]; os.killpg(os.getpgid(info["pid"]), signal.SIGTERM); del running_models[model_id]
    return {"success": True}

@app.get("/api/system/info", response_model=SystemInfo)
async def get_system_info(username: str = Depends(get_current_user)):
    dev_mode, vllm_version = get_system_info_sync()
    return SystemInfo(dev_mode=dev_mode, vllm_version=vllm_version)

@app.post("/api/system/upgrade")
async def upgrade_vllm(username: str = Depends(get_current_user)):
    if upgrade_task: raise HTTPException(400, "Upgrade already in progress.")
    thread = Thread(target=upgrade_vllm_task); upgrade_task['thread'] = thread; thread.start()
    return {"success": True}

@app.websocket("/ws/upgrade")
async def upgrade_vllm_ws(websocket: WebSocket):
    await websocket.accept()
    if not upgrade_task or 'log_queue' not in upgrade_task: await websocket.close(); return
    log_q = upgrade_task['log_queue']
    try:
        while True:
            log_line = log_q.get()
            if log_line is None: break
            await websocket.send_text(log_line)
        await websocket.send_text("---UPGRADE-COMPLETE---")
    except WebSocketDisconnect: pass

# ============================================
# Frontend Serving
# ============================================

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index(request: Request):
    token = request.cookies.get("session_token")
    if verify_session(token):
        return FileResponse('frontend/index.html')
    return FileResponse('frontend/index.html') # Let JS handle login redirect

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=MANAGER_PORT)
