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
import collections
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from threading import Thread
import queue

from fastapi import FastAPI, HTTPException, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
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
ADMIN_PASSWORD_HASH_FROM_ENV = os.getenv("VLLM_ADMIN_PASSWORD_HASH")
IS_PASSWORD_ENV_MANAGED = bool(ADMIN_PASSWORD_HASH_FROM_ENV)
MODEL_DIR = Path(os.getenv("MODEL_DIR", "./models"))
DATABASE_URL = "sqlite:///vllm_manager.db"
SESSION_FILE = Path(".manager_sessions.json")
SESSION_TIMEOUT = 3600  # 1 hour

MODEL_DIR.mkdir(exist_ok=True)

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
        "gpu_ids": "0", "gpu_memory_utilization": 0.9, "tensor_parallel_size": 1, 
        "max_model_len": 4096, "dtype": "auto", "quantization": None, 
        "trust_remote_code": False, "enable_prefix_caching": False,
    })
    download_status = Column(String, default="not_downloaded")
    size_gb = Column(Float, default=0.0)

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(Text)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_admin_password_info(db: SessionLocal) -> dict:
    if ADMIN_PASSWORD_HASH_FROM_ENV:
        return {"hash": ADMIN_PASSWORD_HASH_FROM_ENV, "source": "env"}
    
    password_setting = db.query(Setting).filter(Setting.key == "admin_password_hash").first()
    if password_setting:
        return {"hash": password_setting.value, "source": "db"}
        
    return {"hash": hashlib.sha256("admin123".encode()).hexdigest(), "source": "default"}

# ============================================
# Pydantic Models
# ============================================

class ModelConfigUpdate(BaseModel):
    gpu_ids: str
    gpu_memory_utilization: float
    tensor_parallel_size: int
    max_model_len: int
    dtype: str
    quantization: Optional[str]
    trust_remote_code: bool
    enable_prefix_caching: bool

class ModelStatus(BaseModel):
    id: int; name: str; hf_model_id: str; model_type: str; config: dict
    download_status: str; size_gb: float; is_running: bool
    status_text: str = "stopped"; port: Optional[int] = None; pid: Optional[int] = None
    gpu_ids: Optional[str] = None; error_message: Optional[str] = None

class GPUInfo(BaseModel):
    id: int; name: str; memory_total_mb: int; memory_used_mb: int
    utilization_percent: float; temperature: Optional[float]; assigned_models: List[str]

class DashboardStats(BaseModel):
    total_models: int; running_models: int; system_cpu_percent: float; system_memory_percent: float

class LoginRequest(BaseModel): username: str; password: str
class PullModelRequest(BaseModel): hf_model_id: str
class SystemInfo(BaseModel): vllm_version: str; dev_mode: bool
class ChangePasswordRequest(BaseModel): current_password: str; new_password: str
class AdminSettings(BaseModel): is_password_env_managed: bool; is_using_default_password: bool

# ============================================
# Log Broadcasting
# ============================================
class LogBroadcaster:
    def __init__(self):
        self.subscribers: List[WebSocket] = []
        self.log_cache = collections.deque(maxlen=200)
        self._loop = asyncio.get_event_loop()

    async def subscribe(self, websocket: WebSocket):
        self.subscribers.append(websocket)
        if self.log_cache:
            await websocket.send_text("--- Log History ---\n" + "".join(self.log_cache))

    def unsubscribe(self, websocket: WebSocket):
        if websocket in self.subscribers:
            self.subscribers.remove(websocket)

    def push(self, message: str):
        self.log_cache.append(message)
        asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)

    async def _broadcast(self, message: str):
        for sub in list(self.subscribers):
            try:
                await sub.send_text(message)
            except Exception:
                self.unsubscribe(sub)

# ============================================
# App Setup & Global State
# ============================================
app = FastAPI(title="vLLM Manager Pro", version="3.2.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

running_models: Dict[int, dict] = {}
model_states: Dict[int, dict] = {}
sessions: Dict[str, dict] = {}
download_tasks: Dict[int, dict] = {}
upgrade_task: Dict = {}
log_broadcasters: Dict[int, LogBroadcaster] = {}

# ============================================
# Authentication & Sessions
# ============================================

def hash_password(p: str) -> str: return hashlib.sha256(p.encode()).hexdigest()

def save_sessions():
    with open(SESSION_FILE, 'w') as f: json.dump(sessions, f)

def load_sessions():
    global sessions
    if SESSION_FILE.exists():
        with open(SESSION_FILE, 'r') as f: sessions = json.load(f)

def create_session(u: str) -> str:
    token = secrets.token_urlsafe(32); sessions[token] = {"username": u, "created": datetime.now().isoformat(), "expires": (datetime.now() + timedelta(seconds=SESSION_TIMEOUT)).isoformat()}; save_sessions(); return token

def verify_session(t: Optional[str]) -> bool:
    if not t or t not in sessions: return False
    if datetime.now() > datetime.fromisoformat(sessions[t]["expires"]): del sessions[t]; save_sessions(); return False
    return True

async def get_current_user(r: Request):
    token = r.cookies.get("session_token")
    if not verify_session(token): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    return sessions[token]["username"]

# ============================================
# Background Tasks & Utilities
# ============================================

async def health_check_task(model_id: int, port: int, process: subprocess.Popen, model_name: str, gpu_ids: str, broadcaster: LogBroadcaster):
    try:
        await asyncio.sleep(5)
        if process.poll() is not None:
            raise RuntimeError("Process died unexpectedly.")

        async with httpx.AsyncClient() as client:
            for _ in range(45):
                if process.poll() is not None:
                    raise RuntimeError("Process terminated during health checks.")
                try:
                    res = await client.get(f"http://127.0.0.1:{port}/v1/models", timeout=2.0)
                    if res.status_code == 200:
                        data = res.json()
                        model_names_in_response = [m["id"] for m in data.get("data", [])]
                        if model_name in model_names_in_response:
                            running_models[model_id] = {"process": process, "pid": process.pid, "port": port, "gpu_ids": gpu_ids, "name": model_name}
                            if model_id in model_states: del model_states[model_id]
                            print(f"Model '{model_name}' (ID: {model_id}) started successfully on port {port}.")
                            broadcaster.push("---START SUCCESS---")
                            return
                except httpx.RequestError: pass
                await asyncio.sleep(2)
        raise RuntimeError("Health check timed out after 90 seconds. Model server may have failed to load the model.")
    except Exception as e:
        if process.poll() is None:
            try: os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except ProcessLookupError: pass
        
        full_error_message = f"Startup failed: {str(e)}. Check logs for details."
        model_states[model_id] = {"status": "error", "message": full_error_message}
        print(f"Error starting model '{model_name}' (ID: {model_id}): {full_error_message}")
        broadcaster.push(f"---START FAILURE---\n{full_error_message}")

def download_model_task(db_id: int, hf_model_id: str, model_name: str):
    log_q = queue.Queue(); download_tasks[db_id] = {'log_queue': log_q}
    def log(message): log_q.put(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
    try:
        db = SessionLocal()
        model = db.query(Model).filter(Model.id == db_id).first()
        if not model: log(f"ERROR: Model with ID {db_id} not found in DB."); return
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
        if 'db' in locals() and db.is_active and (model := db.query(Model).filter(Model.id == db_id).first()):
             model.download_status = "error"; db.commit()
    finally:
        log_q.put("---DOWNLOAD COMPLETE---"); log_q.put(None)
        if 'db' in locals() and db.is_active: db.close()

def upgrade_vllm_task():
    log_q = queue.Queue(); upgrade_task['log_queue'] = log_q
    def log(message): log_q.put(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
    try:
        log("Starting vLLM upgrade..."); venv_python = sys.executable; install_dir = Path(__file__).parent.resolve()
        dev_mode, _ = get_system_info_sync()
        command, cwd = ([venv_python, "-m", "pip", "install", "-e", "."], install_dir / "vllm-source") if dev_mode else ([venv_python, "-m", "pip", "install", "--upgrade", "vllm"], install_dir)
        if dev_mode:
            log("Dev mode: upgrading from git...")
            if not cwd.exists(): raise FileNotFoundError("vllm-source directory not found")
            git_proc = subprocess.run(["git", "pull"], cwd=cwd, capture_output=True, text=True)
            log(git_proc.stdout)
            if git_proc.returncode != 0: log(f"ERROR:\n{git_proc.stderr}"); raise subprocess.CalledProcessError(git_proc.returncode, git_proc.args, stderr=git_proc.stderr)
        else: log("Stable mode: upgrading from PyPI...")
        log(f"Executing: {' '.join(str(c) for c in command)}")
        with subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
            for line in iter(process.stdout.readline, ''): log(line)
        if process.returncode != 0: raise subprocess.CalledProcessError(process.returncode, command)
        log("\n✅ Upgrade complete! Please RESTART the manager to apply changes.")
    except Exception as e: log(f"\n❌ ERROR: {str(e)}")
    finally: log_q.put("---UPGRADE COMPLETE---"); log_q.put(None); upgrade_task.clear()

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
    port = start_port
    while port in {info["port"] for info in running_models.values()}: port += 1
    return port

# ============================================
# API Endpoints
# ============================================

@app.on_event("startup")
async def startup_event(): load_sessions()

@app.post("/api/login")
async def login(req: LoginRequest, db: SessionLocal = Depends(get_db)):
    admin_password_hash = get_admin_password_info(db)["hash"]
    if req.username != ADMIN_USERNAME or hash_password(req.password) != admin_password_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_session(req.username); res = JSONResponse({"success": True}); res.set_cookie("session_token", token, httponly=True, max_age=SESSION_TIMEOUT, samesite="lax"); return res

@app.post("/api/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token");
    if token in sessions: del sessions[token]; save_sessions()
    res = JSONResponse({"success": True}); res.delete_cookie("session_token"); return res

@app.get("/api/check-auth")
async def check_auth(request: Request):
    token = request.cookies.get("session_token"); is_auth = verify_session(token)
    return {"authenticated": is_auth, "username": sessions[token]["username"] if is_auth else None}

@app.get("/api/models", response_model=List[ModelStatus])
async def list_models(db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    db_models = db.query(Model).all(); statuses = []
    for m in db_models:
        status = ModelStatus(id=m.id, name=m.name, hf_model_id=m.hf_model_id, model_type=m.model_type, config=m.config, download_status=m.download_status, size_gb=m.size_gb, is_running=False)
        if m.id in running_models:
            info = running_models[m.id]
            status.is_running = True; status.status_text = "running"; status.port, status.pid, status.gpu_ids = info["port"], info["pid"], info["gpu_ids"]
        elif m.id in model_states:
            state = model_states[m.id]
            status.status_text = state['status']
            if state['status'] == 'error': status.error_message = state.get('message', 'Unknown error.')
        else: status.status_text = m.download_status
        statuses.append(status)
    return statuses

@app.put("/api/models/{model_id}/config")
async def update_model_config(model_id: int, config: ModelConfigUpdate, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model: raise HTTPException(404, "Model not found")
    if model.id in running_models or (model_id in model_states and model_states[model_id]['status'] == 'starting'):
        raise HTTPException(400, "Cannot edit a model that is running or starting. Please stop it first.")
    model.config = config.dict(); db.commit(); return {"success": True}

@app.post("/api/models/{model_id}/start")
async def start_model(model_id: int, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    if model_id in running_models or (model_id in model_states and model_states[model_id]['status'] == 'starting'):
        raise HTTPException(400, "Model is already running or starting")
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model or model.download_status != "completed": raise HTTPException(404, "Model not downloaded or found.")
    
    config = model.config
    port = find_available_port()
    gpu_ids = config.get("gpu_ids", "0")
    
    cmd = [ sys.executable, "-m", "vllm.entrypoints.openai.api_server", 
            "--model", str(model.path), 
            "--served-model-name", model.name,
            "--port", str(port),
            "--host", "0.0.0.0", 
            "--gpu-memory-utilization", str(config['gpu_memory_utilization']),
            "--tensor-parallel-size", str(config['tensor_parallel_size']), 
            "--max-model-len", str(config['max_model_len']),
            "--dtype", config['dtype']]
    if config.get('quantization'): cmd.extend(["--quantization", config['quantization']])
    if config.get('trust_remote_code'): cmd.append("--trust-remote-code")
    if config.get('enable_prefix_caching'): cmd.append("--enable-prefix-caching")
    env = os.environ.copy(); env["CUDA_VISIBLE_DEVICES"] = gpu_ids
    
    broadcaster = LogBroadcaster(); log_broadcasters[model_id] = broadcaster
    process = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    def stream_output(proc, bc):
        for line in iter(proc.stdout.readline, ''): bc.push(line)
    
    Thread(target=stream_output, args=(process, broadcaster), daemon=True).start()
    model_states[model_id] = {"status": "starting"}
    asyncio.create_task(health_check_task(model.id, port, process, model.name, gpu_ids, broadcaster))
    return {"success": True, "message": "Model start initiated."}

@app.post("/api/models/{model_id}/stop")
async def stop_model(model_id: int, username: str = Depends(get_current_user)):
    if model_id in model_states: del model_states[model_id]
    if model_id not in running_models: raise HTTPException(404, "Model is not running")
    try: os.killpg(os.getpgid(running_models[model_id]["pid"]), signal.SIGTERM)
    except ProcessLookupError: pass
    del running_models[model_id]
    if model_id in log_broadcasters: del log_broadcasters[model_id]
    return {"success": True}

@app.post("/api/models/{model_id}/clear_error")
async def clear_error_state(model_id: int, username: str = Depends(get_current_user)):
    if model_id in model_states and model_states[model_id]['status'] == 'error':
        del model_states[model_id]
        if model_id in log_broadcasters:
            del log_broadcasters[model_id]
        return {"success": True}
    raise HTTPException(status_code=404, detail="No error state to clear for this model.")

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    return DashboardStats(total_models=db.query(Model).count(), running_models=len(running_models),
                          system_cpu_percent=psutil.cpu_percent(interval=0.1), system_memory_percent=psutil.virtual_memory().percent)

@app.get("/api/gpus", response_model=List[GPUInfo])
async def get_gpu_info(username: str = Depends(get_current_user)):
    try:
        return [GPUInfo(id=g.id, name=g.name, memory_total_mb=int(g.memoryTotal), memory_used_mb=int(g.memoryUsed),
                        utilization_percent=float(g.load * 100), temperature=float(g.temperature) if g.temperature else None,
                        assigned_models=[m['name'] for m in running_models.values() if str(g.id) in m.get("gpu_ids", "0").split(",")])
                for g in GPUtil.getGPUs()]
    except Exception as e: print(f"Could not get GPU info: {e}"); return []

@app.post("/api/models/scan")
async def scan_models_folder(db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    if not MODEL_DIR.exists(): raise HTTPException(status_code=404, detail="Models directory not found.")
    existing_model_names, imported_count = {m[0] for m in db.query(Model.name).all()}, 0
    for entry in os.scandir(MODEL_DIR):
        if entry.is_dir() and entry.name not in existing_model_names:
            model_path = Path(entry.path)
            if not (model_path / "config.json").exists(): continue
            try:
                with open(model_path / "config.json") as f:
                    model_type = ModelType.EMBEDDING if any(k in json.load(f) for k in ['pooling', 'sentence_transformers', 'embedding']) else ModelType.TEXT
                total_size = sum(f.stat().st_size for f in model_path.glob('**/*') if f.is_file())
                db.add(Model(name=entry.name, hf_model_id=f"local/{entry.name}", path=str(model_path), model_type=model_type, download_status="completed", size_gb=total_size / (1024**3)))
                imported_count += 1
            except Exception as ex:
                print(ex)
    if imported_count > 0: db.commit()
    return {"success": True, "message": f"Successfully imported {imported_count} new model(s)." if imported_count > 0 else "No new models found to import."}

@app.delete("/api/models/{model_id}")
async def delete_model(model_id: int, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    if model_id in running_models: raise HTTPException(400, "Cannot delete a running model.")
    if model_id in model_states: del model_states[model_id]
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model: raise HTTPException(404, "Model not found")
    if model.path and Path(model.path).exists(): shutil.rmtree(model.path)
    db.delete(model); db.commit()
    return {"success": True}

@app.post("/api/models/pull")
async def pull_model(req: PullModelRequest, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    model_name = req.hf_model_id.split('/')[-1]
    if db.query(Model).filter(Model.name == model_name).first(): raise HTTPException(400, "Model already exists.")
    new_model = Model(name=model_name, hf_model_id=req.hf_model_id); db.add(new_model); db.commit(); db.refresh(new_model)
    Thread(target=download_model_task, args=(new_model.id, req.hf_model_id, model_name)).start()
    return {"success": True, "model_id": new_model.id}

@app.get("/api/system/info", response_model=SystemInfo)
async def get_system_info(username: str = Depends(get_current_user)):
    dev_mode, vllm_version = get_system_info_sync()
    return SystemInfo(dev_mode=dev_mode, vllm_version=vllm_version)

@app.post("/api/system/upgrade")
async def upgrade_vllm(username: str = Depends(get_current_user)):
    if upgrade_task: raise HTTPException(400, "Upgrade already in progress.")
    Thread(target=upgrade_vllm_task).start()
    return {"success": True}

@app.get("/api/admin/settings", response_model=AdminSettings)
async def get_admin_settings(db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    return AdminSettings(is_password_env_managed=IS_PASSWORD_ENV_MANAGED, is_using_default_password=get_admin_password_info(db)["source"] == "default")

@app.post("/api/admin/change-password")
async def change_password(req: ChangePasswordRequest, db: SessionLocal = Depends(get_db), username: str = Depends(get_current_user)):
    if IS_PASSWORD_ENV_MANAGED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is managed by an environment variable.")
    if hash_password(req.current_password) != get_admin_password_info(db)["hash"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Incorrect current password.")
    if not req.new_password: raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password cannot be empty.")
    new_hash = hash_password(req.new_password)
    if not (pw_setting := db.query(Setting).filter(Setting.key == "admin_password_hash").first()):
        pw_setting = Setting(key="admin_password_hash", value=new_hash); db.add(pw_setting)
    else: pw_setting.value = new_hash
    db.commit()
    return {"success": True, "message": "Password updated successfully."}

@app.websocket("/ws/pull/{model_id}")
async def pull_model_ws(websocket: WebSocket, model_id: int):
    await websocket.accept()
    if model_id not in download_tasks or 'log_queue' not in download_tasks[model_id]: await websocket.close(); return
    log_q = download_tasks[model_id].get('log_queue')
    try:
        while (log_line := await asyncio.to_thread(log_q.get)) is not None:
            await websocket.send_text(log_line)
    except WebSocketDisconnect: pass
    finally:
        if model_id in download_tasks: del download_tasks[model_id]
        
@app.websocket("/ws/logs/{model_id}")
async def model_logs_ws(websocket: WebSocket, model_id: int):
    await websocket.accept()
    if model_id not in log_broadcasters:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION); return
    broadcaster = log_broadcasters[model_id]
    await broadcaster.subscribe(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.unsubscribe(websocket)

@app.websocket("/ws/upgrade")
async def upgrade_vllm_ws(websocket: WebSocket):
    await websocket.accept()
    if not upgrade_task or 'log_queue' not in upgrade_task: await websocket.close(); return
    log_q = upgrade_task['log_queue']
    try:
        while (log_line := await asyncio.to_thread(log_q.get)) is not None:
            await websocket.send_text(log_line)
    except WebSocketDisconnect: pass

# ============================================
# Frontend Serving
# ============================================

app.mount("/static", StaticFiles(directory="frontend"), name="static")
@app.get("/")
async def read_index(request: Request): return FileResponse('frontend/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=MANAGER_PORT)
    
