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
- [Security](#security)
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

```bash
# 1. Install vLLM Deployer
git clone https://github.com/ParisNeo/vllm_deployer.git
cd vllm_deployer
bash install_vllm.sh

# 2. (Recommended) Change the default password
./reset_password.sh

# 3. Start the manager
./run.sh
```

Now open `http://localhost:9000` in your browser, log in, and pull your first model from the UI.

## 🔒 Security

### Default Credentials

The default login for the Web UI is:
- **Username**: `admin`
- **Password**: `admin123`

**It is strongly recommended to change the default password immediately after installation.**

### Changing the Password

You can change the password in two ways:

#### 1. Using the Reset Script (Recommended)

The easiest way to reset your password is to use the provided script.

```bash
# Navigate to your installation directory
cd /path/to/vllm_app

# Run the script and follow the prompts
./reset_password.sh
```

This will securely prompt you for a new password and automatically update your configuration. Remember to restart the manager for the new password to take effect.

#### 2. Using Environment Variables

For production or containerized environments, you can set the password hash directly using an environment variable.

1.  **Generate the hash for your new password:**
    ```bash
    echo -n 'your_secure_password' | sha256sum
    ```
    This will output a hash string, e.g., `5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8`.

2.  **Set the environment variable:**
    ```bash
    export VLLM_ADMIN_PASSWORD_HASH='your_hash_here'
    ```
    To make this permanent, add the `export` command to your shell profile (e.g., `~/.bashrc` or `~/.zshrc`).

**Note:** The `VLLM_ADMIN_PASSWORD_HASH` environment variable will always override the setting in the `.env` file if both are present.

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

All model management is now handled through the Web UI.

1.  **Start the manager:** `./run.sh`
2.  **Open the UI:** `http://localhost:9000`
3.  **Pull a model:** Use the "Pull New Model" form, entering the Hugging Face model ID (e.g., `mistralai/Mistral-7B-Instruct-v0.2`).
4.  **Monitor progress:** A log window will appear, showing the download progress in real-time.
5.  **Start the model:** Once downloaded, the model will appear in your "Managed Models" list. Click "Start" to launch it.

### Protected Models (Gated Models)

If you need to download a model that requires authentication (like Llama 3), you must first log in via the command line on the server where the manager is running:

```bash
# Activate the virtual environment
source venv/bin/activate

# Login to Hugging Face
huggingface-cli login

# Enter your token when prompted
```

Once you have logged in, you can pull the gated model through the Web UI as usual.

## ⚙️ Configuration

### The .env File

Located in your installation directory, this file controls core settings:

```
# Model storage location
MODEL_DIR=/path/to/models

# Default server port (not used by manager)
VLLM_PORT=8000

# Installation mode (stable or dev)
DEV_MODE=false

# Admin password hash (set by reset_password.sh)
VLLM_ADMIN_PASSWORD_HASH='...'
```

### Per-Model Configuration

Model-specific configuration is now managed directly in the Web UI. After a model is downloaded, you can edit its settings before starting it.

## 🎮 Usage

### Starting the Manager

The primary way to use the system is through the vLLM Manager.

```bash
cd /path/to/install_dir
./run.sh
```

This starts the web server. Access the UI at `http://localhost:9000`.

From the UI, you can:
- Pull, configure, start, stop, and delete models.
- Monitor system resources and GPU usage.
- Upgrade the vLLM installation.

### Testing a Running Model

Once you start a model from the UI, it will be assigned a port (e.g., 8000). You can then test it using `curl`.

**List models (verifies the server is running):**
```bash
curl http://localhost:8000/v1/models
```

**Send a completion request:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "user", "content": "Hello! Tell me a joke."}
    ]
  }'
```

## 🎛️ Management Interface

The FastAPI-based management interface provides dynamic control over vLLM instances via a modern web UI and a REST API.

### Starting the Manager

```bash
./run.sh
```

- **Web UI**: `http://localhost:9000`
- **API Docs**: `http://localhost:9000/docs`

### Key Features

- ✅ **Database Backend**: All model configurations are stored in a persistent SQLite database.
- ✅ **UI-Driven Workflow**: Pull, configure, run, and delete models entirely from the browser.
- ✅ **Live Logging**: Real-time log streaming for model downloads and vLLM upgrades.
- ✅ **System Management**: View vLLM version and perform one-click upgrades.
- ✅ **Dynamic Port Allocation**: Automatically assigns available ports to running models.

## 🔧 Service Management

### Installing as a Service

After testing manually, install as a systemd service for automatic startup:

```bash
sudo ./manage_service.sh install
```

This creates a `vllm` service that:
- Starts automatically on boot
- Restarts on failure
- Runs the `run.sh` script to launch the manager.

### Service Commands

```bash
# Check status
systemctl status vllm

# Start service
sudo systemctl start vllm

# Stop service
sudo systemctl stop vllm

# View logs (real-time)
journalctl -u vllm -f
```

### Uninstalling Service

```bash
sudo ./manage_service.sh uninstall
```

## ⬆️ Upgrading

vLLM can be upgraded directly from the Web UI.

1.  Navigate to the "System Information" panel in the dashboard.
2.  Click the "Upgrade vLLM" button.
3.  A log window will appear, showing the real-time output of the upgrade process.
4.  Once the upgrade is complete, **restart the manager** (`sudo systemctl restart vllm` if running as a service, or `Ctrl+C` and `./run.sh` otherwise) to apply the changes.

## 🔧 Troubleshooting

### Common Issues

#### Model Fails to Download

- **Gated Model**: Ensure you have run `huggingface-cli login` on the server.
- **Disk Space**: Check if you have enough disk space in the `models` directory.
- **Network Issues**: Verify the server has a stable internet connection.

#### vLLM Not Found

**Symptom:** `vllm: command not found` when running scripts manually.
**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate
```

#### Out of Memory (OOM)

**Symptom:** CUDA out of memory errors when starting a model.
**Solution:**
- Use a smaller model.
- In the UI, edit the model's configuration to lower the "GPU Memory Utilization" (e.g., to `0.7`).
- Use a quantized model (e.g., GPTQ, AWQ).

## 📁 Project Structure

```
vllm_deployer/
├── frontend/                # Web UI files
│   ├── index.html
│   └── script.js
├── install_vllm.sh          # Main installation script
├── manage_service.sh        # Service management
├── run.sh                   # Manager launcher
├── reset_password.sh        # Password reset utility
├── vllm_manager.py          # FastAPI backend
├── .gitignore
├── CHANGELOG.md
└── README.md

# After installation:
install_dir/
├── frontend/
├── venv/
├── models/
├── .env
├── vllm_manager.db          # SQLite database
├── ... (copied scripts)
```

## 🤝 Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and open a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.