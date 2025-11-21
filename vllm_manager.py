"""
vLLM Manager Pro - Advanced Web UI for vLLM Instance Management
Features: DB Backend, UI-based model pulling, UI-based upgrades, Authentication, GPU Management, Secure Sudo, HF Hub Browser
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
import csv
import io
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
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
from huggingface_hub import snapshot_download, HfFolder, HfApi

# Cryptography for secure sudo password handling
try:
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("WARNING: 'cryptography' library not found. Secure password handling disabled.")

# ========================================================
# Configuration
# ========================================================

MANAGER_PORT = int(os.getenv("MANAGER_PORT", 9000))
ADMIN_USERNAME = os.getenv("VLLM_ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH_FROM_ENV = os.getenv("VLLM_ADMIN_PASSWORD_HASH")
IS_PASSWORD_ENV_MANAGED = bool(ADMIN_PASSWORD_HASH_FROM_ENV)
MODEL_DIR = Path(os.getenv("MODEL_DIR", "./models"))
DATABASE_URL = "sqlite:///vllm_manager.db"
SESSION_FILE = Path(".manager_sessions.json")
SESSION_TIMEOUT = 3600  # 1 hour

MODEL_DIR.mkdir(exist_ok=True)

# ========================================================
# Security: RSA Key Generation (Transient)
# ========================================================
rsa_private_key = None
rsa_public_jwk = None

if HAS_CRYPTO:
    rsa_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    pub_nums = rsa_private_key.public_key().public_numbers()
    
    def int_to_base64(value):
        value_hex = format(value, 'x')
        if len(value_hex) % 2 == 1:
            value_hex = '0' + value_hex
        value_bytes = bytes.fromhex(value_hex)
        return base64.urlsafe_b64encode(value_bytes).decode('utf-8').rstrip('=')

    rsa_public_jwk = {
        "kty": "RSA",
        "n": int_to_base64(pub_nums.n),
        "e": int_to_base64(pub_nums.e),
        "alg": "RSA-OAEP-256",
        "ext": True,
        "key_ops": ["encrypt"]
    }

def decrypt_password(encrypted_b64: str) -> str:
    if not HAS_CRYPTO or not rsa_private_key:
        raise Exception("Encryption not available on server.")
    try:
        encrypted_bytes = base64.b64decode(encrypted_b64)
        decrypted = rsa_private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted.decode('utf-8')
    except Exception as e:
        raise Exception("Decryption failed. Keys may have changed or data is corrupt.")


# ========================================================
# Database Setup
# ========================================================

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


# ========================================================
# Pydantic Models
# ========================================================

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
    error_message: Optional[str] = None


class GPUProcess(BaseModel):
    pid: int
    process_name: str
    gpu_memory_usage: float
    managed_model_id: Optional[int] = None


class GPUInfo(BaseModel):
    id: int
    name: str
    memory_total_mb: int
    memory_used_mb: int
    utilization_percent: float
    temperature: Optional[float]
    processes: List[GPUProcess] = []


class DashboardStats(BaseModel):
    total_models: int
    running_models: int
    system_cpu_percent: float
    system_memory_percent: float


class LoginRequest(BaseModel):
    username: str
    password: str


class PullModelRequest(BaseModel):
    hf_model_id: str


class SystemInfo(BaseModel):
    vllm_version: str
    dev_mode: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AdminSettings(BaseModel):
    is_password_env_managed: bool
    is_using_default_password: bool


class KillProcessRequest(BaseModel):
    encrypted_sudo_password: Optional[str] = None


# ========================================================
# Log Broadcasting
# ========================================================
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


# ========================================================
# App Setup & Global State
# ========================================================
app = FastAPI(title="vLLM Manager Pro", version="3.4.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

running_models: Dict[int, dict] = {}
model_states: Dict[int, dict] = {}
sessions: Dict[str, dict] = {}
download_tasks: Dict[int, dict] = {}
upgrade_task: Dict = {}
log_broadcasters: Dict[int, LogBroadcaster] = {}

# ========================================================
# Authentication & Sessions
# ========================================================
# ... (Same as before) ...
def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def save_sessions():
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f)

def load_sessions():
    global sessions
    if SESSION_FILE.exists():
        with open(SESSION_FILE, "r") as f:
            sessions = json.load(f)

def create_session(u: str) -> str:
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "username": u,
        "created": datetime.now().isoformat(),
        "expires": (datetime.now() + timedelta(seconds=SESSION_TIMEOUT)).isoformat(),
    }
    save_sessions()
    return token

def verify_session(t: Optional[str]) -> bool:
    if not t or t not in sessions:
        return False
    if datetime.now() > datetime.fromisoformat(sessions[t]["expires"]):
        del sessions[t]
        save_sessions()
        return False
    return True

async def get_current_user(r: Request):
    token = r.cookies.get("session_token")
    if not verify_session(token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    return sessions[token]["username"]


# ========================================================
# Background Tasks & Utilities
# ========================================================

async def health_check_task(model_id, port, process, model_name, gpu_ids, broadcaster):
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
                            print(f"Model '{model_name}' (ID: {model_id}) started successfully.")
                            broadcaster.push("---START SUCCESS---")
                            return
                except httpx.RequestError: pass
                await asyncio.sleep(2)
        raise RuntimeError("Health check timed out.")
    except Exception as e:
        if process.poll() is None:
            try: os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except: pass
        model_states[model_id] = {"status": "error", "message": str(e)}
        print(f"Error starting model: {str(e)}")
        broadcaster.push(f"---START FAILURE---\n{str(e)}")

def download_model_task(db_id, hf_model_id, model_name):
    log_q = queue.Queue()
    download_tasks[db_id] = {"log_queue": log_q}
    def log(m): log_q.put(f"[{datetime.now().strftime('%H:%M:%S')}] {m}\n")
    try:
        db = SessionLocal()
        model = db.query(Model).filter(Model.id == db_id).first()
        if not model: return
        log(f"Starting download for {hf_model_id}...")
        model.download_status = "downloading"
        db.commit()
        model_path = MODEL_DIR / model_name
        snapshot_download(repo_id=hf_model_id, local_dir=model_path, local_dir_use_symlinks=False, token=HfFolder.get_token())
        log("Download complete.")
        total_size = sum(f.stat().st_size for f in model_path.glob("**/*") if f.is_file())
        model.download_status = "completed"
        model.path = str(model_path)
        model.size_gb = total_size / (1024 ** 3)
        config_path = model_path / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                if any(k in json.load(f) for k in ["pooling", "sentence_transformers", "embedding"]):
                    model.model_type = ModelType.EMBEDDING
                    log("Detected embedding model.")
        db.commit()
        model_states.pop(db_id, None)
    except Exception as e:
        log(f"ERROR: {str(e)}")
        if "db" in locals() and db.is_active:
            model = db.query(Model).filter(Model.id == db_id).first()
            if model:
                model.download_status = "error"
                db.commit()
                model_states[db_id] = {"status": "error", "message": str(e)}
    finally:
        log_q.put("---DOWNLOAD COMPLETE---")
        log_q.put(None)
        if "db" in locals() and db.is_active: db.close()

def upgrade_vllm_task():
    log_q = queue.Queue()
    upgrade_task["log_queue"] = log_q
    def log(m): log_q.put(f"[{datetime.now().strftime('%H:%M:%S')}] {m}\n")
    try:
        log("Starting vLLM upgrade...")
        venv_python = sys.executable
        install_dir = Path(__file__).parent.resolve()
        dev_mode, _ = get_system_info_sync()
        if dev_mode:
            cmd = [venv_python, "-m", "pip", "install", "-e", "."]
            cwd = install_dir / "vllm-source"
            if not cwd.exists(): raise FileNotFoundError("vllm-source dir not found")
            log("Pulling git..."); subprocess.run(["git", "pull"], cwd=cwd, check=True)
        else:
            cmd = [venv_python, "-m", "pip", "install", "--upgrade", "vllm"]
            cwd = install_dir
        log(f"Exec: {' '.join(cmd)}")
        with subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as p:
            for l in iter(p.stdout.readline, ""): log(l)
        log("Upgrade complete. Restart required.")
    except Exception as e: log(f"ERROR: {str(e)}")
    finally:
        log_q.put("---UPGRADE COMPLETE---")
        log_q.put(None)
        upgrade_task.clear()

def get_system_info_sync():
    install_info_path = Path(__file__).parent.resolve() / ".install_info"
    dev = False; ver = "Unknown"
    if install_info_path.exists():
        with open(install_info_path) as f:
            for l in f:
                if "DEV_MODE=true" in l: dev = True
                if l.startswith("VLLM_VERSION="): ver = l.strip().split("=")[1]
    return dev, ver

def find_available_port(start=8000):
    p = start
    while p in {i["port"] for i in running_models.values()}: p += 1
    return p

def get_gpu_processes_from_nvidia_smi() -> Dict[int, List[dict]]:
    gpu_map = {}; processes = collections.defaultdict(list)
    try:
        res_map = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader,nounits"], capture_output=True, text=True)
        if res_map.returncode == 0:
            for r in csv.reader(io.StringIO(res_map.stdout)):
                if len(r) >= 2: gpu_map[r[1].strip()] = int(r[0].strip())
        res_apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,gpu_uuid,used_memory", "--format=csv,noheader,nounits"], capture_output=True, text=True)
        if res_apps.returncode == 0:
            for r in csv.reader(io.StringIO(res_apps.stdout)):
                if len(r) >= 4:
                    try:
                        pid, name, uuid, mem = int(r[0]), r[1].strip(), r[2].strip(), float(r[3] or 0)
                        idx = gpu_map.get(uuid)
                        if idx is not None: processes[idx].append({"pid": pid, "process_name": name, "gpu_memory_usage": mem})
                    except: continue
    except: pass
    return processes


# ========================================================
# API Endpoints
# ========================================================

@app.on_event("startup")
async def startup_event(): load_sessions()

@app.post("/api/login")
async def login(req: LoginRequest, db: SessionLocal = Depends(get_db)):
    if req.username != ADMIN_USERNAME or hash_password(req.password) != get_admin_password_info(db)["hash"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_session(req.username)
    res = JSONResponse({"success": True})
    res.set_cookie("session_token", token, httponly=True, max_age=SESSION_TIMEOUT, samesite="lax")
    return res

@app.post("/api/logout")
async def logout(request: Request):
    if t := request.cookies.get("session_token"):
        if t in sessions: del sessions[t]; save_sessions()
    res = JSONResponse({"success": True})
    res.delete_cookie("session_token")
    return res

@app.get("/api/check-auth")
async def check_auth(request: Request):
    token = request.cookies.get("session_token")
    return {"authenticated": verify_session(token), "username": sessions[token]["username"] if verify_session(token) else None}

@app.get("/api/security/public-key")
async def get_public_key():
    if not HAS_CRYPTO: raise HTTPException(501, "Encryption not available")
    return rsa_public_jwk

@app.get("/api/models", response_model=List[ModelStatus])
async def list_models(db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    db_models = db.query(Model).all()
    res = []
    for m in db_models:
        s = ModelStatus(id=m.id, name=m.name, hf_model_id=m.hf_model_id, model_type=m.model_type, config=m.config, download_status=m.download_status, size_gb=m.size_gb, is_running=False, status_text=m.download_status)
        if m.id in running_models:
            i = running_models[m.id]
            s.is_running = True; s.status_text = "running"; s.port = i["port"]; s.pid = i["pid"]; s.gpu_ids = i["gpu_ids"]
        elif m.id in model_states:
            st = model_states[m.id]
            s.status_text = st["status"]
            if st["status"] == "error": s.error_message = st.get("message")
        res.append(s)
    return res

@app.put("/api/models/{model_id}/config")
async def update_model_config(model_id: int, config: ModelConfigUpdate, db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m: raise HTTPException(404, "Model not found")
    if m.id in running_models: raise HTTPException(400, "Stop model first")
    m.config = config.dict(); db.commit()
    return {"success": True}

@app.post("/api/models/{model_id}/start")
async def start_model(model_id: int, db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    if model_id in running_models: raise HTTPException(400, "Already running")
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m or m.download_status != "completed": raise HTTPException(404, "Not ready")
    cfg = m.config; port = find_available_port(); gpu_ids = cfg.get("gpu_ids", "0")
    cmd = [sys.executable, "-m", "vllm.entrypoints.openai.api_server", "--model", str(m.path), "--served-model-name", m.name, "--port", str(port), "--host", "0.0.0.0", "--gpu-memory-utilization", str(cfg["gpu_memory_utilization"]), "--tensor-parallel-size", str(cfg["tensor_parallel_size"]), "--max-model-len", str(cfg["max_model_len"]), "--dtype", cfg["dtype"]]
    if q := cfg.get("quantization"): cmd.extend(["--quantization", q])
    if cfg.get("trust_remote_code"): cmd.append("--trust-remote-code")
    if cfg.get("enable_prefix_caching"): cmd.append("--enable-prefix-caching")
    env = os.environ.copy(); env["CUDA_VISIBLE_DEVICES"] = gpu_ids
    bc = LogBroadcaster(); log_broadcasters[model_id] = bc
    proc = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    def stream(p, b):
        for l in iter(p.stdout.readline, ""): b.push(l)
    Thread(target=stream, args=(proc, bc), daemon=True).start()
    model_states[model_id] = {"status": "starting"}
    asyncio.create_task(health_check_task(m.id, port, proc, m.name, gpu_ids, bc))
    return {"success": True}

@app.post("/api/models/{model_id}/stop")
async def stop_model(model_id: int, u=Depends(get_current_user)):
    if model_id in model_states: del model_states[model_id]
    if model_id not in running_models: raise HTTPException(404, "Not running")
    try: os.killpg(os.getpgid(running_models[model_id]["pid"]), signal.SIGTERM)
    except: pass
    del running_models[model_id]
    if model_id in log_broadcasters: del log_broadcasters[model_id]
    return {"success": True}

@app.post("/api/models/{model_id}/clear_error")
async def clear_error_state(model_id: int, u=Depends(get_current_user)):
    if model_id in model_states: del model_states[model_id]
    db = SessionLocal()
    m = db.query(Model).filter(Model.id == model_id).first()
    if m and m.download_status == "error": m.download_status = "completed"; db.commit()
    db.close()
    return {"success": True}

@app.get("/api/dashboard/stats")
async def get_stats(db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    return DashboardStats(total_models=db.query(Model).count(), running_models=len(running_models), system_cpu_percent=psutil.cpu_percent(0.1), system_memory_percent=psutil.virtual_memory().percent)

@app.get("/api/gpus", response_model=List[GPUInfo])
async def get_gpu_info(u=Depends(get_current_user)):
    nv_procs = get_gpu_processes_from_nvidia_smi()
    res = []
    try:
        for g in GPUtil.getGPUs():
            plist = []
            if g.id in nv_procs:
                for p in nv_procs[g.id]:
                    mid = next((k for k, v in running_models.items() if v["pid"] == p["pid"]), None)
                    plist.append(GPUProcess(pid=p["pid"], process_name=p["process_name"], gpu_memory_usage=p["gpu_memory_usage"], managed_model_id=mid))
            res.append(GPUInfo(id=g.id, name=g.name, memory_total_mb=int(g.memoryTotal), memory_used_mb=int(g.memoryUsed), utilization_percent=float(g.load*100), temperature=g.temperature, processes=plist))
    except: pass
    return res

@app.post("/api/gpus/kill/{pid}")
async def kill_gpu(pid: int, req: KillProcessRequest = None, u=Depends(get_current_user)):
    if not req: req = KillProcessRequest()
    if mid := next((k for k, v in running_models.items() if v["pid"] == pid), None): return await stop_model(mid, u)
    try:
        os.kill(pid, signal.SIGTERM)
        return {"success": True, "message": f"Killed {pid}"}
    except PermissionError:
        if os.name == 'nt': raise HTTPException(403, "Permission denied (Windows)")
        if not req.encrypted_sudo_password: raise HTTPException(403, "Sudo password required")
        try:
            sp = decrypt_password(req.encrypted_sudo_password)
            subprocess.run(["sudo", "-S", "kill", "-9", str(pid)], input=f"{sp}\n", check=True, capture_output=True, text=True)
            return {"success": True, "message": f"Killed {pid} with sudo"}
        except Exception as e: raise HTTPException(500, f"Sudo failed: {str(e)}")
    except Exception as e: raise HTTPException(500, str(e))

@app.post("/api/models/scan")
async def scan_models(db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    if not MODEL_DIR.exists(): raise HTTPException(404, "No model dir")
    existing = {m[0] for m in db.query(Model.name).all()}; count = 0
    for e in os.scandir(MODEL_DIR):
        if e.is_dir() and e.name not in existing:
            p = Path(e.path)
            if (p/"config.json").exists():
                try:
                    with open(p/"config.json") as f: mt = ModelType.EMBEDDING if "embedding" in json.load(f).get("model_type", "") else ModelType.TEXT
                    s = sum(f.stat().st_size for f in p.glob("**/*") if f.is_file())
                    db.add(Model(name=e.name, hf_model_id=f"local/{e.name}", path=str(p), model_type=mt, download_status="completed", size_gb=s/1024**3))
                    count+=1
                except: pass
    if count: db.commit()
    return {"success": True, "message": f"Imported {count} models"}

@app.delete("/api/models/{model_id}")
async def delete_model(model_id: int, db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    if model_id in running_models: raise HTTPException(400, "Running")
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m: raise HTTPException(404, "Not found")
    if m.path and Path(m.path).exists(): shutil.rmtree(m.path)
    db.delete(m); db.commit()
    return {"success": True}

@app.post("/api/models/pull")
async def pull_model(req: PullModelRequest, db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    name = req.hf_model_id.split("/")[-1]
    if db.query(Model).filter(Model.name == name).first(): raise HTTPException(400, "Exists")
    m = Model(name=name, hf_model_id=req.hf_model_id); db.add(m); db.commit(); db.refresh(m)
    Thread(target=download_model_task, args=(m.id, req.hf_model_id, name)).start()
    return {"success": True, "model_id": m.id}

@app.get("/api/system/info")
async def sys_info(u=Depends(get_current_user)):
    d, v = get_system_info_sync()
    return SystemInfo(dev_mode=d, vllm_version=v)

@app.post("/api/system/upgrade")
async def upgrade_sys(u=Depends(get_current_user)):
    if upgrade_task: raise HTTPException(400, "In progress")
    Thread(target=upgrade_vllm_task).start()
    return {"success": True}

@app.get("/api/admin/settings")
async def admin_settings(db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    return AdminSettings(is_password_env_managed=IS_PASSWORD_ENV_MANAGED, is_using_default_password=get_admin_password_info(db)["source"] == "default")

@app.post("/api/admin/change-password")
async def change_pw(req: ChangePasswordRequest, db: SessionLocal = Depends(get_db), u=Depends(get_current_user)):
    if IS_PASSWORD_ENV_MANAGED: raise HTTPException(400, "Env managed")
    if hash_password(req.current_password) != get_admin_password_info(db)["hash"]: raise HTTPException(403, "Bad password")
    if not req.new_password: raise HTTPException(400, "Empty password")
    s = db.query(Setting).filter(Setting.key == "admin_password_hash").first()
    if not s: s = Setting(key="admin_password_hash", value=hash_password(req.new_password)); db.add(s)
    else: s.value = hash_password(req.new_password)
    db.commit()
    return {"success": True}

# --- Updated Hub Search Endpoint ---
@app.get("/api/hub/search")
async def search_hub(
    query: Optional[str] = None, 
    limit: int = 20, 
    sort: str = "downloads", 
    filter_type: Optional[str] = None,
    u=Depends(get_current_user)
):
    api = HfApi()
    # Enable 'full' metadata to get siblings for size calculation
    search_params = {
        "filter": "text-generation",
        "sort": sort,
        "direction": -1,
        "limit": limit,
        "full": True
    }
    
    search_text = query or ""
    if filter_type == "awq": search_text += " awq"
    elif filter_type == "gptq": search_text += " gptq"
    elif filter_type == "gguf": search_text += " gguf"
    elif filter_type == "compressed-tensors": search_text += " compressed-tensors"
    
    if search_text.strip():
        search_params["search"] = search_text.strip()

    try:
        models = api.list_models(**search_params)
        results = []
        for m in models:
            # Calculate size in GB from siblings if available
            size_gb = 0.0
            if m.siblings:
                total_bytes = sum(s.rfilename.endswith(('.bin', '.safetensors', '.pt')) and 0 or 0 for s in m.siblings)
                # HfApi list_models siblings often don't contain size unless fetched specifically.
                # Actually, 'full=True' gives siblings but maybe not sizes in all versions.
                # Let's try to use 'safetensors' metadata if present or just skip if too slow.
                # To keep it fast, we might not get exact size. 
                # We'll assume 0 if not easily available to avoid slow individual calls.
                pass

            results.append({
                "id": m.modelId,
                "likes": m.likes,
                "downloads": m.downloads,
                "tags": m.tags,
                "pipeline_tag": m.pipeline_tag,
                # "size_gb": size_gb 
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/pull/{model_id}")
async def ws_pull(ws: WebSocket, model_id: int):
    await ws.accept()
    if model_id not in download_tasks: return await ws.close()
    q = download_tasks[model_id]["log_queue"]
    try:
        while (l := await asyncio.to_thread(q.get)) is not None: await ws.send_text(l)
    except: pass
    finally: 
        if model_id in download_tasks: del download_tasks[model_id]

@app.websocket("/ws/logs/{model_id}")
async def ws_logs(ws: WebSocket, model_id: int):
    await ws.accept()
    if model_id not in log_broadcasters: return await ws.close(1008)
    b = log_broadcasters[model_id]; await b.subscribe(ws)
    try:
        while True: await ws.receive_text()
    except: b.unsubscribe(ws)

@app.websocket("/ws/upgrade")
async def ws_upgrade(ws: WebSocket):
    await ws.accept()
    if not upgrade_task: return await ws.close()
    q = upgrade_task["log_queue"]
    try:
        while (l := await asyncio.to_thread(q.get)) is not None: await ws.send_text(l)
    except: pass

app.mount("/static", StaticFiles(directory="frontend"), name="static")
@app.get("/")
async def index(r: Request): return FileResponse("frontend/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=MANAGER_PORT)
