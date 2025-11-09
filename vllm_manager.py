#!/usr/bin/env python3
"""
vLLM Manager Pro - Advanced Web UI for vLLM Instance Management
Features: Authentication, Dashboard, GPU Management, Embedding Support
"""

import asyncio
import json
import os
import subprocess
import signal
import hashlib
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import psutil
import GPUtil

# ============================================
# Configuration
# ============================================

MANAGER_PORT = 9000
ADMIN_USERNAME = os.getenv("VLLM_ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = os.getenv("VLLM_ADMIN_PASSWORD_HASH", "")
MODEL_DIR = Path(os.getenv("MODEL_DIR", "./models"))
STATE_FILE = Path("vllm_manager_state.json")
SESSION_FILE = Path(".manager_sessions.json")
SESSION_TIMEOUT = 3600  # 1 hour

# Generate default password hash if not set
if not ADMIN_PASSWORD_HASH:
    default_password = "admin123"
    ADMIN_PASSWORD_HASH = hashlib.sha256(default_password.encode()).hexdigest()
    print(f"⚠️  WARNING: Using default password '{default_password}'")
    print("   Set VLLM_ADMIN_PASSWORD_HASH environment variable for production!")

# ============================================
# Data Models
# ============================================

class ModelType(str):
    TEXT = "text-generation"
    EMBEDDING = "embedding"

class ModelConfig(BaseModel):
    name: str
    path: str
    model_type: str = ModelType.TEXT
    port: int
    gpu_ids: str = "0"
    gpu_memory_utilization: float = Field(default=0.9, ge=0.1, le=1.0)
    tensor_parallel_size: int = Field(default=1, ge=1)
    max_model_len: int = Field(default=2048, ge=128)
    dtype: str = "auto"
    quantization: Optional[str] = None
    trust_remote_code: bool = False
    enable_prefix_caching: bool = False

class ModelStatus(BaseModel):
    name: str
    model_type: str
    status: str  # running, stopped, error, starting
    port: Optional[int] = None
    pid: Optional[int] = None
    gpu_ids: Optional[str] = None
    uptime: Optional[str] = None
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    request_count: int = 0
    last_accessed: Optional[str] = None

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

# ============================================
# Application Setup
# ============================================

app = FastAPI(
    title="vLLM Manager Pro",
    description="Advanced Web UI for vLLM Model Management",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

# Global state
running_models: Dict[str, dict] = {}
sessions: Dict[str, dict] = {}
start_time = datetime.now()

# ============================================
# Authentication
# ============================================

def hash_password(password: str) -> str:
    """Hash password with SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_session(username: str) -> str:
    """Create new session token"""
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "username": username,
        "created": datetime.now().isoformat(),
        "expires": (datetime.now() + timedelta(seconds=SESSION_TIMEOUT)).isoformat()
    }
    save_sessions()
    return token

def verify_session(token: Optional[str]) -> bool:
    """Verify session token"""
    if not token or token not in sessions:
        return False
    
    session = sessions[token]
    expires = datetime.fromisoformat(session["expires"])
    
    if datetime.now() > expires:
        del sessions[token]
        save_sessions()
        return False
    
    return True

def save_sessions():
    """Save sessions to file"""
    with open(SESSION_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)

def load_sessions():
    """Load sessions from file"""
    global sessions
    if SESSION_FILE.exists():
        with open(SESSION_FILE, 'r') as f:
            sessions = json.load(f)

async def get_current_user(request: Request):
    """Dependency for protected routes"""
    token = request.cookies.get("session_token")
    if not verify_session(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    return sessions[token]["username"]

# ============================================
# Utility Functions
# ============================================

def get_gpu_info() -> List[GPUInfo]:
    """Get GPU information"""
    gpus = []
    try:
        gpu_list = GPUtil.getGPUs()
        for gpu in gpu_list:
            # Find models using this GPU
            assigned_models = []
            for name, info in running_models.items():
                gpu_ids = info.get("gpu_ids", "0").split(",")
                if str(gpu.id) in gpu_ids:
                    assigned_models.append(name)
            
            gpus.append(GPUInfo(
                id=gpu.id,
                name=gpu.name,
                memory_total_mb=int(gpu.memoryTotal),
                memory_used_mb=int(gpu.memoryUsed),
                memory_free_mb=int(gpu.memoryFree),
                utilization_percent=float(gpu.load * 100),
                temperature=float(gpu.temperature) if gpu.temperature else None,
                assigned_models=assigned_models
            ))
    except Exception as e:
        print(f"Error getting GPU info: {e}")
    
    return gpus

def get_available_models() -> List[dict]:
    """Scan model directory for available models"""
    models = []
    
    if not MODEL_DIR.exists():
        return models
    
    for model_path in MODEL_DIR.iterdir():
        if not model_path.is_dir():
            continue
        
        # Check for config file
        yaml_config = model_path / "vllm_config.yaml"
        json_config = model_path / "config.json"
        
        if not yaml_config.exists() and not json_config.exists():
            continue
        
        # Detect model type
        model_type = ModelType.TEXT
        if json_config.exists():
            try:
                with open(json_config) as f:
                    config = json.load(f)
                    # Check for embedding model indicators
                    if any(key in config for key in ['pooling', 'sentence_transformers', 'embedding']):
                        model_type = ModelType.EMBEDDING
            except:
                pass
        
        models.append({
            "name": model_path.name,
            "path": str(model_path),
            "model_type": model_type,
            "config_file": str(yaml_config) if yaml_config.exists() else str(json_config),
            "is_running": model_path.name in running_models,
            "size_mb": sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file()) / (1024 * 1024)
        })
    
    return models

def get_process_info(pid: int) -> dict:
    """Get detailed process information"""
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            return {
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "create_time": proc.create_time(),
                "status": proc.status(),
                "num_threads": proc.num_threads()
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {}

async def check_model_health(port: int) -> bool:
    """Check if model server is healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{port}/health", timeout=2.0)
            return response.status_code == 200
    except:
        return False

def find_available_port(start_port: int = 8000) -> int:
    """Find an available port"""
    used_ports = {info["port"] for info in running_models.values()}
    port = start_port
    while port in used_ports or not is_port_available(port):
        port += 1
    return port

def is_port_available(port: int) -> bool:
    """Check if port is available"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False

def save_state():
    """Save current state to disk"""
    state = {
        name: {
            "port": info["port"],
            "pid": info["pid"],
            "gpu_ids": info["gpu_ids"],
            "model_type": info.get("model_type", ModelType.TEXT),
            "config": info["config"],
            "start_time": info["start_time"]
        }
        for name, info in running_models.items()
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def load_state():
    """Load state from disk"""
    global running_models
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            saved_state = json.load(f)
            
            for name, info in saved_state.items():
                pid = info.get("pid")
                if pid and psutil.pid_exists(pid):
                    try:
                        proc = psutil.Process(pid)
                        if "vllm" in " ".join(proc.cmdline()).lower():
                            running_models[name] = {
                                "process": None,
                                "pid": pid,
                                "port": info["port"],
                                "gpu_ids": info["gpu_ids"],
                                "model_type": info.get("model_type", ModelType.TEXT),
                                "config": info["config"],
                                "start_time": info["start_time"]
                            }
                            print(f"✓ Restored model: {name} (PID: {pid})")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

# ============================================
# Startup/Shutdown
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    load_sessions()
    load_state()
    print(f"✓ vLLM Manager Pro started on port {MANAGER_PORT}")
    print(f"✓ Admin username: {ADMIN_USERNAME}")
    print(f"✓ WebUI: http://localhost:{MANAGER_PORT}")
    print(f"✓ API Docs: http://localhost:{MANAGER_PORT}/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    save_state()
    save_sessions()

# ============================================
# Authentication Endpoints
# ============================================

@app.post("/api/login")
async def login(credentials: LoginRequest):
    """Login endpoint"""
    password_hash = hash_password(credentials.password)
    
    if credentials.username != ADMIN_USERNAME or password_hash != ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    token = create_session(credentials.username)
    
    response = JSONResponse(content={"success": True, "username": credentials.username})
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=SESSION_TIMEOUT,
        samesite="lax"
    )
    
    return response

@app.post("/api/logout")
async def logout(request: Request):
    """Logout endpoint"""
    token = request.cookies.get("session_token")
    if token in sessions:
        del sessions[token]
        save_sessions()
    
    response = JSONResponse(content={"success": True})
    response.delete_cookie("session_token")
    return response

@app.get("/api/check-auth")
async def check_auth(request: Request):
    """Check if user is authenticated"""
    token = request.cookies.get("session_token")
    is_authenticated = verify_session(token)
    
    return {
        "authenticated": is_authenticated,
        "username": sessions[token]["username"] if is_authenticated else None
    }

# ============================================
# Model Management Endpoints
# ============================================

@app.get("/api/models/available")
async def list_available_models(username: str = Depends(get_current_user)):
    """List all available models in the models directory"""
    models = get_available_models()
    return {"models": models}

@app.get("/api/models/running")
async def list_running_models(username: str = Depends(get_current_user)):
    """List all running models with status"""
    statuses = []
    
    for name, info in running_models.items():
        pid = info["pid"]
        proc_info = get_process_info(pid)
        
        uptime = None
        if proc_info.get("create_time"):
            uptime_seconds = datetime.now().timestamp() - proc_info["create_time"]
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime = f"{hours}h {minutes}m"
        
        is_healthy = await check_model_health(info["port"])
        
        statuses.append(ModelStatus(
            name=name,
            model_type=info.get("model_type", ModelType.TEXT),
            status="running" if is_healthy else "error",
            port=info["port"],
            pid=pid,
            gpu_ids=info["gpu_ids"],
            uptime=uptime,
            memory_usage_mb=proc_info.get("memory_mb"),
            cpu_percent=proc_info.get("cpu_percent")
        ))
    
    return {"models": statuses}

@app.post("/api/models/{model_name}/start")
async def start_model(
    model_name: str,
    config: Optional[ModelConfig] = None,
    username: str = Depends(get_current_user)
):
    """Start a model instance"""
    
    if model_name in running_models:
        raise HTTPException(status_code=400, detail=f"Model {model_name} is already running")
    
    model_path = MODEL_DIR / model_name
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    # Load or use provided config
    if config is None:
        yaml_config = model_path / "vllm_config.yaml"
        if yaml_config.exists():
            # Parse YAML (simplified)
            port = find_available_port()
            gpu_ids = "0"
            gpu_memory = 0.9
            tensor_parallel = 1
            max_len = 2048
            dtype = "auto"
            model_type = ModelType.TEXT
        else:
            raise HTTPException(status_code=404, detail="No configuration found")
    else:
        port = config.port if config.port else find_available_port()
        gpu_ids = config.gpu_ids
        gpu_memory = config.gpu_memory_utilization
        tensor_parallel = config.tensor_parallel_size
        max_len = config.max_model_len
        dtype = config.dtype
        model_type = config.model_type
    
    # Build command based on model type
    if model_type == ModelType.EMBEDDING:
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", str(model_path),
            "--port", str(port),
            "--task", "embedding"
        ]
    else:
        cmd = [
            "vllm", "serve",
            str(model_path),
            "--port", str(port),
            "--host", "0.0.0.0",
            "--gpu-memory-utilization", str(gpu_memory),
            "--tensor-parallel-size", str(tensor_parallel),
            "--max-model-len", str(max_len),
            "--dtype", dtype
        ]
    
    # Set environment
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu_ids
    
    try:
        # Start process
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait for startup
        await asyncio.sleep(3)
        
        if process.poll() is not None:
            raise HTTPException(status_code=500, detail="Failed to start model")
        
        # Store process info
        running_models[model_name] = {
            "process": process,
            "pid": process.pid,
            "port": port,
            "gpu_ids": gpu_ids,
            "model_type": model_type,
            "config": config.dict() if config else {},
            "start_time": datetime.now().isoformat()
        }
        
        save_state()
        
        return {
            "success": True,
            "message": f"Model {model_name} started successfully",
            "name": model_name,
            "port": port,
            "pid": process.pid,
            "model_type": model_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting model: {str(e)}")

@app.post("/api/models/{model_name}/stop")
async def stop_model(model_name: str, username: str = Depends(get_current_user)):
    """Stop a running model"""
    
    if model_name not in running_models:
        raise HTTPException(status_code=404, detail=f"Model {model_name} is not running")
    
    info = running_models[model_name]
    pid = info["pid"]
    
    try:
        if info.get("process"):
            info["process"].terminate()
            try:
                info["process"].wait(timeout=10)
            except subprocess.TimeoutExpired:
                info["process"].kill()
        else:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                proc.kill()
        
        del running_models[model_name]
        save_state()
        
        return {
            "success": True,
            "message": f"Model {model_name} stopped successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping model: {str(e)}")

@app.post("/api/models/{model_name}/restart")
async def restart_model(model_name: str, username: str = Depends(get_current_user)):
    """Restart a running model"""
    
    if model_name not in running_models:
        raise HTTPException(status_code=404, detail=f"Model {model_name} is not running")
    
    # Stop
    await stop_model(model_name, username)
    await asyncio.sleep(2)
    
    # Start with previous config
    config_dict = running_models.get(model_name, {}).get("config", {})
    config = ModelConfig(**config_dict) if config_dict else None
    
    return await start_model(model_name, config, username)

@app.delete("/api/models/stop-all")
async def stop_all_models(username: str = Depends(get_current_user)):
    """Stop all running models"""
    stopped = []
    errors = []
    
    for name in list(running_models.keys()):
        try:
            await stop_model(name, username)
            stopped.append(name)
        except Exception as e:
            errors.append({"model": name, "error": str(e)})
    
    return {
        "success": True,
        "stopped": stopped,
        "errors": errors
    }

# ============================================
# GPU Management Endpoints
# ============================================

@app.get("/api/gpus")
async def list_gpus(username: str = Depends(get_current_user)):
    """Get GPU information"""
    gpus = get_gpu_info()
    return {"gpus": gpus}

@app.post("/api/models/{model_name}/assign-gpu")
async def assign_gpu(
    model_name: str,
    gpu_ids: str,
    username: str = Depends(get_current_user)
):
    """Reassign model to different GPU(s)"""
    
    if model_name not in running_models:
        raise HTTPException(status_code=404, detail=f"Model {model_name} is not running")
    
    # This requires restart
    info = running_models[model_name]
    config_dict = info.get("config", {})
    config_dict["gpu_ids"] = gpu_ids
    config = ModelConfig(**config_dict)
    
    # Restart with new GPU assignment
    await stop_model(model_name, username)
    await asyncio.sleep(2)
    await start_model(model_name, config, username)
    
    return {
        "success": True,
        "message": f"Model {model_name} reassigned to GPU(s) {gpu_ids}"
    }

# ============================================
# Dashboard Endpoints
# ============================================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(username: str = Depends(get_current_user)):
    """Get dashboard statistics"""
    
    available_models = get_available_models()
    gpus = get_gpu_info()
    
    uptime_seconds = (datetime.now() - start_time).total_seconds()
    uptime = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"
    
    stats = DashboardStats(
        total_models=len(available_models),
        running_models=len(running_models),
        stopped_models=len(available_models) - len(running_models),
        total_gpus=len(gpus),
        total_memory_mb=sum(gpu.memory_total_mb for gpu in gpus),
        used_memory_mb=sum(gpu.memory_used_mb for gpu in gpus),
        system_cpu_percent=psutil.cpu_percent(interval=0.1),
        system_memory_percent=psutil.virtual_memory().percent,
        uptime=uptime
    )
    
    return stats

# ============================================
# Web UI
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main web UI"""
    return HTML_TEMPLATE

# ============================================
# HTML Template (embedded)
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>vLLM Manager Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        .login-container h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .btn:hover {
            background: #5568d3;
        }
        
        .dashboard {
            display: none;
        }
        
        .dashboard.active {
            display: block;
        }
        
        .header {
            background: white;
            padding: 20px 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #333;
            font-size: 28px;
        }
        
        .header .user-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .header .user-name {
            color: #666;
            font-weight: 500;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .stat-card .label {
            color: #888;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .stat-card .value {
            color: #333;
            font-size: 32px;
            font-weight: 700;
        }
        
        .stat-card .subtext {
            color: #999;
            font-size: 12px;
            margin-top: 5px;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        .panel {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .panel h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 20px;
        }
        
        .model-list {
            max-height: 500px;
            overflow-y: auto;
        }
        
        .model-item {
            padding: 15px;
            border: 2px solid #f0f0f0;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: border-color 0.3s;
        }
        
        .model-item:hover {
            border-color: #667eea;
        }
        
        .model-info h3 {
            color: #333;
            font-size: 16px;
            margin-bottom: 5px;
        }
        
        .model-info .meta {
            color: #999;
            font-size: 12px;
        }
        
        .model-actions {
            display: flex;
            gap: 10px;
        }
        
        .btn-small {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-start {
            background: #10b981;
            color: white;
        }
        
        .btn-start:hover {
            background: #059669;
        }
        
        .btn-stop {
            background: #ef4444;
            color: white;
        }
        
        .btn-stop:hover {
            background: #dc2626;
        }
        
        .btn-restart {
            background: #f59e0b;
            color: white;
        }
        
        .btn-restart:hover {
            background: #d97706;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .status-running {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-stopped {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .gpu-item {
            padding: 15px;
            border: 2px solid #f0f0f0;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        
        .gpu-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        
        .gpu-name {
            font-weight: 600;
            color: #333;
        }
        
        .gpu-util {
            color: #667eea;
            font-weight: 600;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s;
        }
        
        .gpu-memory {
            font-size: 12px;
            color: #888;
        }
        
        .error {
            color: #ef4444;
            padding: 10px;
            background: #fee2e2;
            border-radius: 6px;
            margin-top: 10px;
            font-size: 14px;
        }
        
        @media (max-width: 968px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <!-- Login Screen -->
    <div id="loginScreen" class="login-container">
        <h1>🚀 vLLM Manager Pro</h1>
        <form id="loginForm">
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="password" required autocomplete="current-password">
            </div>
            <button type="submit" class="btn">Login</button>
            <div id="loginError" class="error" style="display: none;"></div>
        </form>
    </div>
    
    <!-- Dashboard -->
    <div id="dashboard" class="dashboard container">
        <div class="header">
            <h1>🚀 vLLM Manager Pro</h1>
            <div class="user-info">
                <span class="user-name" id="userName"></span>
                <button class="btn-small btn-stop" onclick="logout()">Logout</button>
            </div>
        </div>
        
        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Models</div>
                <div class="value" id="totalModels">0</div>
            </div>
            <div class="stat-card">
                <div class="label">Running</div>
                <div class="value" id="runningModels">0</div>
                <div class="subtext">Active instances</div>
            </div>
            <div class="stat-card">
                <div class="label">GPUs</div>
                <div class="value" id="totalGPUs">0</div>
                <div class="subtext" id="gpuMemory">0 MB used</div>
            </div>
            <div class="stat-card">
                <div class="label">System</div>
                <div class="value" id="cpuUsage">0%</div>
                <div class="subtext" id="memUsage">RAM: 0%</div>
            </div>
        </div>
        
        <!-- Main Grid -->
        <div class="main-grid">
            <!-- Available Models -->
            <div class="panel">
                <h2>📦 Available Models</h2>
                <div class="model-list" id="availableModels">
                    <p style="color: #999;">Loading...</p>
                </div>
            </div>
            
            <!-- Running Models -->
            <div class="panel">
                <h2>▶️ Running Models</h2>
                <div class="model-list" id="runningModels">
                    <p style="color: #999;">No models running</p>
                </div>
            </div>
        </div>
        
        <!-- GPU Panel -->
        <div class="panel" style="margin-top: 20px;">
            <h2>🎮 GPU Status</h2>
            <div id="gpuList">
                <p style="color: #999;">Loading...</p>
            </div>
        </div>
    </div>
    
    <script>
        let refreshInterval = null;
        
        // Login
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                if (response.ok) {
                    document.getElementById('loginScreen').style.display = 'none';
                    document.getElementById('dashboard').classList.add('active');
                    document.getElementById('userName').textContent = username;
                    startDashboard();
                } else {
                    document.getElementById('loginError').textContent = 'Invalid username or password';
                    document.getElementById('loginError').style.display = 'block';
                }
            } catch (error) {
                document.getElementById('loginError').textContent = 'Connection error';
                document.getElementById('loginError').style.display = 'block';
            }
        });
        
        // Logout
        async function logout() {
            await fetch('/api/logout', { method: 'POST' });
            location.reload();
        }
        
        // Start dashboard
        function startDashboard() {
            refreshDashboard();
            refreshInterval = setInterval(refreshDashboard, 5000);
        }
        
        // Refresh dashboard
        async function refreshDashboard() {
            await Promise.all([
                updateStats(),
                updateAvailableModels(),
                updateRunningModels(),
                updateGPUs()
            ]);
        }
        
        // Update stats
        async function updateStats() {
            try {
                const response = await fetch('/api/dashboard/stats');
                const stats = await response.json();
                
                document.getElementById('totalModels').textContent = stats.total_models;
                document.getElementById('runningModels').textContent = stats.running_models;
                document.getElementById('totalGPUs').textContent = stats.total_gpus;
                document.getElementById('cpuUsage').textContent = stats.system_cpu_percent.toFixed(1) + '%';
                document.getElementById('memUsage').textContent = 'RAM: ' + stats.system_memory_percent.toFixed(1) + '%';
                document.getElementById('gpuMemory').textContent = 
                    (stats.used_memory_mb / 1024).toFixed(1) + ' / ' + 
                    (stats.total_memory_mb / 1024).toFixed(1) + ' GB used';
            } catch (error) {
                console.error('Error updating stats:', error);
            }
        }
        
        // Update available models
        async function updateAvailableModels() {
            try {
                const response = await fetch('/api/models/available');
                const data = await response.json();
                
                const container = document.getElementById('availableModels');
                
                if (data.models.length === 0) {
                    container.innerHTML = '<p style="color: #999;">No models found</p>';
                    return;
                }
                
                container.innerHTML = data.models.map(model => `
                    <div class="model-item">
                        <div class="model-info">
                            <h3>${model.name}</h3>
                            <div class="meta">
                                ${model.model_type} • ${(model.size_mb / 1024).toFixed(2)} GB
                                ${model.is_running ? '<span class="status-badge status-running">Running</span>' : ''}
                            </div>
                        </div>
                        <div class="model-actions">
                            ${!model.is_running ? `
                                <button class="btn-small btn-start" onclick="startModel('${model.name}')">Start</button>
                            ` : ''}
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error updating available models:', error);
            }
        }
        
        // Update running models
        async function updateRunningModels() {
            try {
                const response = await fetch('/api/models/running');
                const data = await response.json();
                
                const container = document.getElementById('runningModels');
                
                if (data.models.length === 0) {
                    container.innerHTML = '<p style="color: #999;">No models running</p>';
                    return;
                }
                
                container.innerHTML = data.models.map(model => `
                    <div class="model-item">
                        <div class="model-info">
                            <h3>${model.name}</h3>
                            <div class="meta">
                                Port: ${model.port} • GPU: ${model.gpu_ids} • Uptime: ${model.uptime || 'N/A'}
                                <br>Memory: ${(model.memory_usage_mb || 0).toFixed(0)} MB • CPU: ${(model.cpu_percent || 0).toFixed(1)}%
                            </div>
                        </div>
                        <div class="model-actions">
                            <button class="btn-small btn-restart" onclick="restartModel('${model.name}')">Restart</button>
                            <button class="btn-small btn-stop" onclick="stopModel('${model.name}')">Stop</button>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error updating running models:', error);
            }
        }
        
        // Update GPUs
        async function updateGPUs() {
            try {
                const response = await fetch('/api/gpus');
                const data = await response.json();
                
                const container = document.getElementById('gpuList');
                
                if (data.gpus.length === 0) {
                    container.innerHTML = '<p style="color: #999;">No GPUs detected</p>';
                    return;
                }
                
                container.innerHTML = data.gpus.map(gpu => `
                    <div class="gpu-item">
                        <div class="gpu-header">
                            <span class="gpu-name">GPU ${gpu.id}: ${gpu.name}</span>
                            <span class="gpu-util">${gpu.utilization_percent.toFixed(0)}% Util</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${(gpu.memory_used_mb / gpu.memory_total_mb * 100).toFixed(1)}%"></div>
                        </div>
                        <div class="gpu-memory">
                            ${(gpu.memory_used_mb / 1024).toFixed(2)} / ${(gpu.memory_total_mb / 1024).toFixed(2)} GB
                            ${gpu.temperature ? ` • ${gpu.temperature}°C` : ''}
                            ${gpu.assigned_models.length > 0 ? ` • Models: ${gpu.assigned_models.join(', ')}` : ''}
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error updating GPUs:', error);
            }
        }
        
        // Start model
        async function startModel(name) {
            try {
                const response = await fetch(`/api/models/${name}/start`, { method: 'POST' });
                if (response.ok) {
                    await refreshDashboard();
                } else {
                    alert('Failed to start model');
                }
            } catch (error) {
                alert('Error starting model: ' + error.message);
            }
        }
        
        // Stop model
        async function stopModel(name) {
            if (!confirm(`Stop model ${name}?`)) return;
            
            try {
                const response = await fetch(`/api/models/${name}/stop`, { method: 'POST' });
                if (response.ok) {
                    await refreshDashboard();
                } else {
                    alert('Failed to stop model');
                }
            } catch (error) {
                alert('Error stopping model: ' + error.message);
            }
        }
        
        // Restart model
        async function restartModel(name) {
            try {
                const response = await fetch(`/api/models/${name}/restart`, { method: 'POST' });
                if (response.ok) {
                    await refreshDashboard();
                } else {
                    alert('Failed to restart model');
                }
            } catch (error) {
                alert('Error restarting model: ' + error.message);
            }
        }
        
        // Check auth on page load
        async function checkAuth() {
            try {
                const response = await fetch('/api/check-auth');
                const data = await response.json();
                
                if (data.authenticated) {
                    document.getElementById('loginScreen').style.display = 'none';
                    document.getElementById('dashboard').classList.add('active');
                    document.getElementById('userName').textContent = data.username;
                    startDashboard();
                }
            } catch (error) {
                console.error('Auth check failed:', error);
            }
        }
        
        // Initialize
        checkAuth();
    </script>
</body>
</html>
"""

# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    # Check for GPU support
    try:
        GPUtil.getGPUs()
    except:
        print("⚠️  Warning: GPUtil not available or no GPUs detected")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=MANAGER_PORT,
        log_level="info"
    )
