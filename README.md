# vLLM Deployer

[![GitHub](https://img.shields.io/badge/GitHub-ParisNeo%2Fvllm__deployer-blue?logo=github)](https://github.com/ParisNeo/vllm_deployer)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![vLLM](https://img.shields.io/badge/vLLM-latest-orange.svg)](https://docs.vllm.ai)

**Fast, scalable, and user-friendly deployment solution for serving Large Language Models with vLLM.**

vLLM Deployer provides a complete toolkit for installing, configuring, and managing vLLM model serving infrastructure with an intuitive command-line interface and optional REST API management layer.

## ✨ Features

- 🚀 **One-Command Installation** - Automated setup with virtual environment management
- 🔧 **Dual Installation Modes** - Stable (PyPI) or Development (from source)
- 📦 **Automatic Model Configuration** - Download and configure models with a single command
- ⚙️ **Management API** - FastAPI-based interface for dynamic model lifecycle management
- 🎯 **Multi-GPU Support** - Efficient GPU resource allocation and management
- 🔄 **Easy Upgrades** - Simple upgrade path for both stable and dev installations
- 🐧 **Linux Native** - Full support for Ubuntu, Debian, and other modern distributions
- 💻 **Windows via WSL2** - Complete Windows support through WSL with GPU acceleration
- 🛠️ **Optional systemd Integration** - Production-ready service management
- 📊 **Real-time Monitoring** - Track model status, resource usage, and performance
- 🔒 **Process Isolation** - Each model runs in its own process for stability
- 📚 **Comprehensive Documentation** - Detailed guides for every use case

## 📋 Table of Contents

- [Requirements](#requirements)
- [Platform Support](#platform-support)
- [Understanding Models](#understanding-models)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Windows/WSL Setup](#windowswsl-setup)
- [Finding and Installing Models](#finding-and-installing-models)
- [Configuration](#configuration)
- [Usage](#usage)
- [Management Interface](#management-interface)
- [Multi-Model Serving](#multi-model-serving)
- [Service Management](#service-management)
- [Upgrading](#upgrading)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 📦 Requirements

### Core Requirements
- **Operating System**: Linux (Ubuntu 20.04+, Debian 11+) or Windows 10/11 with WSL2
- **Python**: 3.9, 3.10, 3.11, or 3.12
- **GPU** (recommended): NVIDIA GPU with compute capability 7.0+ (V100, T4, RTX 20xx, A100, L4, H100)
- **CUDA**: 12.1+ (for GPU acceleration)
- **Disk Space**: Varies by model (minimum 10GB recommended)
- **RAM**: 16GB+ recommended

### Optional Requirements
- **systemd**: For automatic service management (Linux/WSL)
- **Git**: For development installation mode
- **huggingface-cli**: For private model downloads (installed automatically)

## 🖥️ Platform Support

### ✅ Linux (Full Native Support)
All features work out of the box on modern Linux distributions.

### ✅ Windows (via WSL2)
Complete support through Windows Subsystem for Linux with:
- GPU acceleration via CUDA on WSL
- Native performance
- Seamless Windows integration

See [Windows/WSL Setup](#windowswsl-setup) for detailed instructions.

### ⚠️ macOS
vLLM does not officially support macOS. Consider cloud-based alternatives.

## 🧠 Understanding Models

Before starting, it's important to understand model sizes and GPU requirements.

### GPU Memory Requirements

**Rule of thumb for FP16 models:**
- 1B parameters ≈ 2GB VRAM
- 7B parameters ≈ 14GB VRAM
- 13B parameters ≈ 26GB VRAM
- 70B parameters ≈ 140GB VRAM

**Quantized models (GPTQ, AWQ)** use ~4-bit precision, reducing memory by ~75%.

### Model Size Categories

#### 🟢 Small Models (125M - 3B)
**Perfect for testing, development, or resource-constrained environments**

| Model | Parameters | VRAM | Best For |
|-------|-----------|------|----------|
| `facebook/opt-125m` | 125M | ~250MB | Quick testing |
| `facebook/opt-1.3b` | 1.3B | ~2.5GB | Development |
| `microsoft/phi-2` | 2.7B | ~5GB | High quality, small footprint |
| `stabilityai/stablelm-3b-4e1t` | 3B | ~6GB | General purpose |

#### 🟡 Medium Models (7B - 13B)
**Production-ready with excellent quality-to-resource ratio**

| Model | Parameters | VRAM | Best For |
|-------|-----------|------|----------|
| `mistralai/Mistral-7B-Instruct-v0.2` | 7B | ~14GB | Chat, instruction following |
| `meta-llama/Llama-2-7b-chat-hf` | 7B | ~14GB | Conversational AI |
| `teknium/OpenHermes-2.5-Mistral-7B` | 7B | ~14GB | Versatile assistant |
| `NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO` | 47B | ~94GB | High performance |

#### 🔴 Large Models (30B+)
**Maximum capability, requires significant resources**

| Model | Parameters | VRAM | Best For |
|-------|-----------|------|----------|
| `meta-llama/Llama-2-70b-chat-hf` | 70B | ~140GB | Enterprise applications |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | 47B | ~94GB | Advanced reasoning |

## 🚀 Quick Start

**Get running in 3 commands:**

```
# 1. Install vLLM Deployer
git clone https://github.com/ParisNeo/vllm_deployer.git
cd vllm_deployer
bash install_vllm.sh

# 2. Download a model (automatically configured)
./pull_model.sh facebook/opt-125m

# 3. Start serving
./run.sh
```

That's it! Your model is now running at `http://localhost:8000`.

## 📥 Installation

### Standard Installation (Stable)

```
# Clone the repository
git clone https://github.com/ParisNeo/vllm_deployer.git
cd vllm_deployer

# Install to current directory
bash install_vllm.sh

# Or specify installation directory
bash install_vllm.sh /opt/vllm
```

### Development Installation (Latest Features)

```
# Install from source
bash install_vllm.sh --dev

# Or with custom path
bash install_vllm.sh --dev /opt/vllm
```

### What Gets Installed

The installer will:
1. ✅ Validate Python version (3.9+)
2. ✅ Create isolated virtual environment
3. ✅ Install vLLM (stable or dev)
4. ✅ Install management interface (FastAPI, Uvicorn, etc.)
5. ✅ Copy all deployment scripts
6. ✅ Create configuration files (.env)
7. ✅ Generate quick start guide (QUICKSTART.txt)

### Installation Options

```
# Syntax
bash install_vllm.sh [--dev] [install_dir] [model_dir]

# Examples
bash install_vllm.sh                           # Current directory, stable
bash install_vllm.sh --dev                     # Current directory, dev mode
bash install_vllm.sh /opt/vllm                 # Specific directory
bash install_vllm.sh /opt/vllm /data/models    # Custom model directory
bash install_vllm.sh --dev ~/vllm ~/models     # Dev mode, custom paths
```

## 💻 Windows/WSL Setup

vLLM does not run natively on Windows, but works excellently through WSL2.

### Prerequisites

- Windows 10 version 2004+ or Windows 11
- NVIDIA GPU (optional but recommended)

### Step 1: Install WSL2

Open PowerShell as Administrator:

```
# Install WSL with Ubuntu
wsl --install

# Or install Ubuntu 22.04 specifically
wsl --install -d Ubuntu-22.04

# Ensure WSL2 is the default
wsl --set-default-version 2
```

Restart your computer if prompted.

### Step 2: Launch Ubuntu

1. Open Ubuntu from Start menu
2. Create username and password when prompted
3. Update system packages:

```
sudo apt update && sudo apt upgrade -y
```

### Step 3: Enable GPU Support (For NVIDIA GPUs)

**On Windows (not in WSL):**
1. Download and install the latest NVIDIA drivers from [nvidia.com](https://www.nvidia.com/Download/index.aspx)
2. Install drivers version 470.76 or later

**Verify in WSL:**

```
nvidia-smi
```

If you see your GPU information, GPU support is working!

### Step 4: Install CUDA Toolkit in WSL

```
# Install build essentials
sudo apt install -y build-essential python3-dev python3-pip python3-venv git

# Add CUDA repository
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update

# Install CUDA toolkit
sudo apt install -y cuda-toolkit-12-4
```

### Step 5: Install vLLM Deployer

```
# Navigate to home directory
cd ~

# Clone repository
git clone https://github.com/ParisNeo/vllm_deployer.git
cd vllm_deployer

# Run installation
bash install_vllm.sh ~/vllm_app
```

### Step 6: Access from Windows

**Find your WSL IP:**
```
hostname -I
```

**Access options:**
- From Windows browser: `http://<WSL_IP>:8000`
- Or simply: `http://localhost:8000` (Windows 11 auto-forwards)

### WSL Performance Tips

#### File System Location
⚠️ **Important**: Store models in Linux filesystem for best performance

```
# ✅ Good - Fast performance
~/vllm_app/models/

# ❌ Avoid - Very slow
/mnt/c/Users/YourName/models/
```

Access WSL files from Windows Explorer: `\\wsl$\Ubuntu-22.04\home\username\`

#### Memory Configuration

WSL2 uses dynamic memory. For large models, configure limits:

Create `C:\Users\<YourUsername>\.wslconfig`:

```
[wsl2]
memory=32GB          # Adjust based on your RAM
processors=8         # Number of CPU cores
swap=8GB             # Swap space
```

Restart WSL: `wsl --shutdown` (in PowerShell)

#### Auto-Start on Windows Boot

WSL doesn't auto-start. Options:
1. Create Windows scheduled task
2. Use Windows Terminal with auto-run configuration
3. Manually start when needed

### WSL Troubleshooting

**GPU not detected:**
```
# Verify driver on Windows
# From PowerShell:
nvidia-smi

# Update WSL kernel
wsl --update
```

**Slow performance:**
- Ensure files are in Linux filesystem (`/home/...`), not `/mnt/c/`
- Verify WSL2 is being used: `wsl -l -v`
- Check `.wslconfig` resource allocation

**Network issues:**
```
# From PowerShell (Administrator)
wsl --shutdown
Get-NetAdapter | Where-Object Name -like "*WSL*" | Restart-NetAdapter
```

## 🔍 Finding and Installing Models

### How to Find Models

**1. Browse Hugging Face Hub**
- Visit [huggingface.co/models](https://huggingface.co/models)
- Filter by "Text Generation" task
- Sort by "Most Downloads" or "Trending"
- Check the model card for requirements and license

**2. Check vLLM Compatibility**
- Visit [vLLM Supported Models](https://docs.vllm.ai/en/latest/models/supported_models.html)
- Supported architectures include:
  - LLaMA, LLaMA-2, LLaMA-3
  - Mistral, Mixtral
  - GPT-2, GPT-J, GPT-NeoX
  - OPT, BLOOM, Falcon
  - Qwen, Phi, Gemma
  - And many more!

**3. Verify Model Requirements**
- Check model size vs your GPU memory
- Review license terms (some require agreement)
- Look for quantized versions if memory is limited

### Downloading Models

**Basic syntax:**
```
./pull_model.sh <huggingface_model_name>
```

**Examples:**
```
# Small test model
./pull_model.sh facebook/opt-125m

# Production-ready model
./pull_model.sh mistralai/Mistral-7B-Instruct-v0.2

# Large model
./pull_model.sh meta-llama/Llama-2-7b-chat-hf
```

### What Happens During Download

The script automatically:
1. ✅ Downloads the model from Hugging Face
2. ✅ Stores it in your models directory
3. ✅ Creates a default `vllm_config.json` file
4. ✅ **Adds the model to your `.env` configuration**
5. ✅ Provides next steps

**No manual configuration needed!**

### Installing Your First Model

**Step-by-step example:**

```
# 1. Navigate to installation directory
cd /path/to/vllm_app

# 2. View available model options
./pull_model.sh

# 3. Download a beginner-friendly model
./pull_model.sh facebook/opt-125m

# 4. The model is automatically configured - just run!
./run.sh
```

### Multiple Models

Download multiple models - they're all added automatically:

```
./pull_model.sh facebook/opt-125m
./pull_model.sh facebook/opt-1.3b
./pull_model.sh microsoft/phi-2

# Check your configuration
cat .env
# MODEL_LIST='opt-125m:vllm_config.json,opt-1.3b:vllm_config.json,phi-2:vllm_config.json'
```

### Protected Models (Gated Models)

Some models require Hugging Face authentication:

```
# Login to Hugging Face
huggingface-cli login

# Enter your token when prompted

# Now download gated models
./pull_model.sh meta-llama/Llama-2-7b-chat-hf
```

Get your token from: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### Quantized Models

For limited GPU memory, use quantized models:

```
# Search for GPTQ or AWQ models on Hugging Face
./pull_model.sh TheBloke/Llama-2-7B-Chat-GPTQ
```

Benefits:
- 4-bit precision (~75% memory reduction)
- Faster inference
- Minimal quality loss

## ⚙️ Configuration

### The .env File

Located in your installation directory, this file controls all settings:

```
# Model storage location
MODEL_DIR=/path/to/models

# Models to serve (automatically updated by pull_model.sh)
MODEL_LIST='opt-125m:vllm_config.json,mistral-7b:vllm_config.json'

# Default server port
VLLM_PORT=8000

# Installation mode (stable or dev)
DEV_MODE=false
```

### Per-Model Configuration

Each model has a `vllm_config.json` file in its directory:

```
{
  "max_model_len": 2048,
  "gpu_memory_utilization": 0.9,
  "tensor_parallel_size": 1,
  "dtype": "auto",
  "quantization": null
}
```

**Key parameters:**
- `max_model_len`: Maximum sequence length
- `gpu_memory_utilization`: GPU memory fraction (0.0-1.0)
- `tensor_parallel_size`: Number of GPUs for tensor parallelism
- `dtype`: Data type (`auto`, `float16`, `bfloat16`, `float32`)
- `quantization`: Quantization method (`awq`, `gptq`, `squeezellm`, `null`)

### Advanced Configuration Examples

**Multi-GPU setup (tensor parallelism):**
```
{
  "tensor_parallel_size": 4,
  "gpu_memory_utilization": 0.95,
  "max_model_len": 4096
}
```

**Memory-constrained setup:**
```
{
  "gpu_memory_utilization": 0.7,
  "max_model_len": 1024,
  "dtype": "float16"
}
```

**Quantized model:**
```
{
  "quantization": "gptq",
  "dtype": "float16",
  "gpu_memory_utilization": 0.9
}
```

## 🎮 Usage

### Simple Server (run.sh)

Start vLLM with all configured models:

```
cd /path/to/install_dir
./run.sh
```

The script will:
- Load configuration from `.env`
- Validate all models exist
- Start vLLM server(s)
- Display access information

**Stop the server:** Press `Ctrl+C`

### Testing Your Server

**List models:**
```
curl http://localhost:8000/v1/models
```

**Send a completion request:**
```
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "opt-125m",
    "messages": [
      {"role": "user", "content": "Hello! Tell me a joke."}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

**Streaming response:**
```
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "opt-125m",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'
```

## 🎛️ Management Interface

The FastAPI-based management interface provides dynamic control over multiple vLLM instances.

### Starting the Manager

```
cd /path/to/install_dir
./start_manager.sh
```

Access:
- API Server: `http://localhost:9000`
- Interactive Docs: `http://localhost:9000/docs`
- ReDoc: `http://localhost:9000/redoc`

### Key Features

- ✅ Start/stop models dynamically
- ✅ Monitor resource usage (memory, CPU, uptime)
- ✅ Health checking
- ✅ Dynamic port allocation
- ✅ GPU assignment per model
- ✅ Request proxying to correct model
- ✅ Persistent state across restarts

### API Endpoints

#### List Available Models
```
curl http://localhost:9000/models
```

#### Start a Model
```
curl -X POST http://localhost:9000/models/opt-125m/start
```

**With custom configuration:**
```
curl -X POST http://localhost:9000/models/mistral-7b/start \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mistral-7b",
    "port": 8001,
    "gpu_ids": "0,1",
    "gpu_memory_utilization": 0.95,
    "tensor_parallel_size": 2
  }'
```

#### Check Model Status
```
curl http://localhost:9000/models/status
```

**Response example:**
```
{
  "models": [
    {
      "name": "opt-125m",
      "status": "running",
      "port": 8000,
      "pid": 12345,
      "gpu_ids": "0",
      "uptime": "2h 15m",
      "memory_usage": 512.5
    }
  ]
}
```

#### Stop a Model
```
curl -X POST http://localhost:9000/models/opt-125m/stop
```

#### Stop All Models
```
curl -X DELETE http://localhost:9000/models/stop-all
```

#### Proxy Chat Completion
```
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "opt-125m",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Management Workflows

**Multi-model deployment:**
```
# Start manager
./start_manager.sh

# In another terminal, start multiple models
curl -X POST http://localhost:9000/models/opt-125m/start
curl -X POST http://localhost:9000/models/phi-2/start
curl -X POST http://localhost:9000/models/mistral-7b/start

# Check what's running
curl http://localhost:9000/models/status

# Use different models via proxy
curl -X POST http://localhost:9000/v1/chat/completions \
  -d '{"model": "opt-125m", "messages": [{"role": "user", "content": "Hi"}]}'

curl -X POST http://localhost:9000/v1/chat/completions \
  -d '{"model": "mistral-7b", "messages": [{"role": "user", "content": "Hi"}]}'
```

**Dynamic scaling:**
```
# Start small model for testing
curl -X POST http://localhost:9000/models/opt-125m/start

# Switch to larger model for production
curl -X POST http://localhost:9000/models/opt-125m/stop
curl -X POST http://localhost:9000/models/mistral-7b/start
```

## 🔀 Multi-Model Serving

### How It Works

**Important:** vLLM does not support multiple models in a single server instance. Instead, each model runs as a separate process on its own port.

### Architecture

```
┌─────────────────────────────────────────┐
│         Load Balancer / Proxy           │
│          (Optional - Nginx)             │
└───────────┬─────────────────────────────┘
            │
     ┌──────┴──────┬──────────────┐
     │             │              │
┌────▼────┐   ┌────▼────┐   ┌────▼────┐
│ Model A │   │ Model B │   │ Model C │
│ Port    │   │ Port    │   │ Port    │
│ 8000    │   │ 8001    │   │ 8002    │
│ GPU 0   │   │ GPU 1   │   │ GPU 2   │
└─────────┘   └─────────┘   └─────────┘
```

### GPU Assignment Strategies

**Strategy 1: One Model Per GPU**
```
# Model A on GPU 0
CUDA_VISIBLE_DEVICES=0 vllm serve model_a --port 8000

# Model B on GPU 1
CUDA_VISIBLE_DEVICES=1 vllm serve model_b --port 8001

# Model C on GPU 2
CUDA_VISIBLE_DEVICES=2 vllm serve model_c --port 8002
```

**Strategy 2: GPU Sharing (Small Models)**
```
# Both models share GPU 0
CUDA_VISIBLE_DEVICES=0 vllm serve small_model_a --port 8000 --gpu-memory-utilization 0.4
CUDA_VISIBLE_DEVICES=0 vllm serve small_model_b --port 8001 --gpu-memory-utilization 0.4
```

**Strategy 3: Tensor Parallelism (Large Model)**
```
# Single model using multiple GPUs
CUDA_VISIBLE_DEVICES=0,1,2,3 vllm serve large_model --port 8000 --tensor-parallel-size 4
```

### Using the Management Interface

The management interface handles all of this automatically:

```
# Start manager
./start_manager.sh

# Start models on different GPUs
curl -X POST http://localhost:9000/models/opt-125m/start \
  -d '{"gpu_ids": "0", "port": 8000}'

curl -X POST http://localhost:9000/models/mistral-7b/start \
  -d '{"gpu_ids": "1", "port": 8001}'

curl -X POST http://localhost:9000/models/llama-7b/start \
  -d '{"gpu_ids": "2,3", "tensor_parallel_size": 2, "port": 8002}'
```

### Load Balancing (Optional)

For a unified API endpoint, use Nginx:

```
upstream vllm_opt {
    server localhost:8000;
}

upstream vllm_mistral {
    server localhost:8001;
}

server {
    listen 80;
    
    location /opt/ {
        proxy_pass http://vllm_opt/;
    }
    
    location /mistral/ {
        proxy_pass http://vllm_mistral/;
    }
}
```

## 🔧 Service Management

### Installing as a Service

After testing manually, install as a systemd service for automatic startup:

```
./manage_service.sh install
```

This creates a `vllm` service that:
- Starts automatically on boot
- Restarts on failure
- Runs with your user permissions
- Logs to systemd journal

### Service Commands

```
# Check status
systemctl status vllm

# Start service
sudo systemctl start vllm

# Stop service
sudo systemctl stop vllm

# Restart service
sudo systemctl restart vllm

# Enable auto-start on boot
sudo systemctl enable vllm

# Disable auto-start
sudo systemctl disable vllm

# View logs (real-time)
journalctl -u vllm -f

# View recent logs
journalctl -u vllm -n 50
```

### Uninstalling Service

```
./manage_service.sh uninstall
```

This removes the service but keeps vLLM and your models.

### Installing Manager as a Service

```
./manage_service.sh install-manager
```

Creates a separate `vllm-manager` service on port 9000.

## ⬆️ Upgrading

### Upgrade Script

```
cd /path/to/install_dir
./upgrade_vllm.sh
```

The script:
- Detects installation mode (stable vs dev)
- Stops running services
- Upgrades vLLM
- Restarts services
- Verifies installation

### Manual Upgrade (Stable)

```
source venv/bin/activate
pip install --upgrade vllm
```

### Manual Upgrade (Dev)

```
cd vllm-source
git pull
pip install -e . --upgrade
```

## 🔧 Troubleshooting

### Common Issues

#### No Models Configured

**Symptom:** `run.sh` says MODEL_LIST is empty

**Solution:**
```
# Download a model
./pull_model.sh facebook/opt-125m

# Model is automatically added to .env
./run.sh
```

#### Model Not Found

**Symptom:** Error about missing model directory

**Solution:**
```
# Check what models you have
ls models/

# Check .env configuration
cat .env

# Download the missing model
./pull_model.sh <model_name>
```

#### vLLM Not Found

**Symptom:** `vllm: command not found`

**Solution:**
```
# Activate virtual environment
source venv/bin/activate

# Verify installation
vllm --version

# If not installed, reinstall
pip install vllm
```

#### Out of Memory (OOM)

**Symptom:** CUDA out of memory errors

**Solutions:**
```
# 1. Use a smaller model
./pull_model.sh facebook/opt-125m

# 2. Reduce GPU memory utilization
# Edit models/your-model/vllm_config.json
{
  "gpu_memory_utilization": 0.7,  # Lower this
  "max_model_len": 1024           # Or reduce this
}

# 3. Use quantized model
./pull_model.sh TheBloke/Llama-2-7B-Chat-GPTQ
```

#### Service Won't Start

**Check logs:**
```
journalctl -u vllm -n 50
```

**Common causes:**
- Model not downloaded
- Incorrect permissions
- Port already in use
- GPU not available

#### Port Already in Use

**Find what's using the port:**
```
sudo lsof -i :8000
```

**Kill the process:**
```
kill <PID>
```

**Or change port in .env:**
```
VLLM_PORT=8001
```

#### WSL-Specific Issues

**GPU not detected:**
```
# Check Windows driver
# From PowerShell:
nvidia-smi

# Update WSL
wsl --update
```

**Slow performance:**
```
# Verify files are in Linux filesystem
pwd  # Should show /home/... not /mnt/c/...

# Check WSL version
wsl -l -v  # Should show VERSION 2
```

### Getting Help

1. Check `QUICKSTART.txt` in your installation directory
2. Review this README
3. Check vLLM documentation: https://docs.vllm.ai
4. Open an issue: https://github.com/ParisNeo/vllm_deployer/issues

## 📁 Project Structure

```
vllm_deployer/
├── install_vllm.sh         # Main installation script
├── upgrade_vllm.sh         # Upgrade script
├── manage_service.sh       # Service management
├── run.sh                  # Simple server launcher
├── pull_model.sh           # Model download utility
├── vllm_manager.py         # FastAPI management interface
├── start_manager.sh        # Manager launcher
├── .gitignore             # Git ignore rules
├── CHANGELOG.md           # Version history
├── LICENSE                # MIT License
└── README.md              # This file

# After installation:
install_dir/
├── venv/                  # Python virtual environment
├── models/                # Downloaded models
├── vllm-source/          # Source code (dev mode only)
├── .env                   # Configuration file
├── .install_info         # Installation metadata
├── QUICKSTART.txt        # Quick reference guide
├── run.sh                # Copied scripts
├── pull_model.sh
├── manage_service.sh
├── upgrade_vllm.sh
├── vllm_manager.py
└── start_manager.sh
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style
- Add tests for new features
- Update documentation
- Update CHANGELOG.md

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Project Repository**: https://github.com/ParisNeo/vllm_deployer
- **vLLM Documentation**: https://docs.vllm.ai
- **vLLM GitHub**: https://github.com/vllm-project/vllm
- **Hugging Face Models**: https://huggingface.co/models
- **WSL Documentation**: https://docs.microsoft.com/windows/wsl/

## 🙏 Acknowledgments

- **vLLM Team** for the excellent inference engine
- **Hugging Face** for model hosting and tools
- **Community Contributors** for feedback and improvements

## 📊 Stats

- ⭐ Star this repo if you find it useful!
- 🐛 Report bugs via GitHub Issues
- 💡 Request features via GitHub Discussions
- 📧 Contact: [Your contact info or link]

---

**Made with ❤️ by ParisNeo**

*Happy Serving! 🚀*
