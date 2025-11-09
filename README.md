# vLLM Deployer

[![GitHub](https://img.shields.io/badge/GitHub-ParisNeo%2Fvllm__deployer-blue?logo=github)](https://github.com/ParisNeo/vllm_deployer)

This project provides scripts to install, run, upgrade, and manage an efficient vLLM serving environment with optional systemd service integration.

## Features

- 🚀 Easy installation with virtual environment management
- 🔧 Support for both stable and development versions
- 📦 Automated model downloading from Hugging Face
- ⚙️ Optional systemd service for production deployment
- 🔄 Simple upgrade process
- 🎯 Multi-GPU support ready
- 💻 Windows support via WSL2

## Files

- `install_vllm.sh`: Sets up a Python virtual environment, installs vLLM (stable or dev), copies scripts
- `upgrade_vllm.sh`: Upgrades vLLM to the latest version (respects dev/stable mode)
- `manage_service.sh`: Install or uninstall the vLLM systemd service
- `run.sh`: Runs vLLM server loading specified models from `.env` configuration
- `pull_model.sh`: Downloads and configures Hugging Face models for use with vLLM
- `.gitignore`: Ignores `venv`, `models`, `vllm-source`, and `.env` files
- `CHANGELOG.md`: Project changelog

## Requirements

- **Linux**: Ubuntu 20.04+, Debian, or other modern Linux distributions
- **Windows**: Windows 10/11 with WSL2 (see Windows section below)
- Python 3.9+
- Git (for dev installation)
- `huggingface-cli` for pulling models (optional: `pip install huggingface-hub`)
- NVIDIA GPU with CUDA support (recommended)
- For service management: systemd (Linux/WSL)

## Platform Support

### Linux
Full native support with all features.

### Windows (via WSL2)
vLLM does not run natively on Windows, but works excellently through WSL2 (Windows Subsystem for Linux). See the [Windows/WSL Setup](#windowswsl-setup) section below for detailed instructions.

## Quick Start

### Installation

1. Clone this repository:

```
git clone https://github.com/ParisNeo/vllm_deployer.git
cd vllm_deployer
```

2. Install stable version:

```
bash install_vllm.sh [install_directory] [optional_model_directory]
```

3. Or install development version from source:

```
bash install_vllm.sh --dev [install_directory] [optional_model_directory]
```

If no install directory is provided, it uses the current directory. If no model directory is provided, it defaults to `models` subfolder inside the install directory.

### Testing Without Service

After installation, you can test vLLM manually:

```
cd /path/to/install_dir
./run.sh
```

This allows you to verify everything works before installing as a system service.

### Installing as a System Service

Once you've tested and confirmed vLLM works correctly:

```
bash manage_service.sh install [install_directory]
```

This creates and enables a systemd service that starts vLLM automatically on boot.

### Uninstalling the Service

To remove the systemd service (doesn't remove vLLM itself):

```
bash manage_service.sh uninstall [install_directory]
```

### Pulling Models

Pull a model from Hugging Face:

```
./pull_model.sh facebook/opt-1.3b [optional_model_dir]
```

The script will:
- Download the model to your models directory
- Create a default `vllm_config.json` configuration file
- Provide instructions for updating your `.env` file

### Configuration

Update the `.env` file in your install directory to configure models and settings:

```
MODEL_DIR=/path/to/models
MODEL_LIST='opt-1.3b:vllm_config.json,llama-7b:vllm_config.json'
VLLM_PORT=8000
DEV_MODE=false
```

### Upgrading

To upgrade vLLM to the latest version:

```
bash upgrade_vllm.sh [install_directory]
```

The script automatically:
- Detects whether you're using stable or dev mode
- Stops the service if running
- Upgrades vLLM
- Restarts the service if it was running

### Service Management

If you've installed the systemd service, use these commands:

```
# Check status
systemctl status vllm

# Stop service
sudo systemctl stop vllm

# Start service
sudo systemctl start vllm

# Restart service
sudo systemctl restart vllm

# View logs
journalctl -u vllm -f

# Enable autostart on boot
sudo systemctl enable vllm

# Disable autostart
sudo systemctl disable vllm
```

## Windows/WSL Setup

### Prerequisites

1. **Windows 10 version 2004+ or Windows 11**
2. **NVIDIA GPU** (optional but highly recommended)

### Step 1: Install WSL2

Open PowerShell as Administrator and run:

```
# Enable WSL
wsl --install

# Or if WSL is already installed, ensure you're using WSL2
wsl --set-default-version 2
```

Restart your computer if prompted.

### Step 2: Install Ubuntu

```
# Install Ubuntu 22.04 (recommended)
wsl --install -d Ubuntu-22.04
```

Launch Ubuntu from the Start menu and complete the initial setup (create username/password).

### Step 3: Enable GPU Support in WSL (For NVIDIA GPUs)

1. **Install NVIDIA GPU drivers on Windows** (not in WSL):
   - Download and install the latest NVIDIA drivers from [nvidia.com](https://www.nvidia.com/Download/index.aspx)
   - Make sure to install drivers version 470.76 or later

2. **Verify GPU access in WSL**:

```
# Inside WSL Ubuntu
nvidia-smi
```

If this shows your GPU, you're ready to proceed.

### Step 4: Install CUDA Toolkit in WSL

```
# Update package lists
sudo apt update
sudo apt upgrade -y

# Install essential build tools
sudo apt install -y build-essential python3-dev python3-pip python3-venv git

# Install CUDA toolkit (choose appropriate version)
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-4
```

### Step 5: Set up vLLM Deployer

```
# Navigate to your preferred location
cd ~

# Clone the repository
git clone https://github.com/ParisNeo/vllm_deployer.git
cd vllm_deployer

# Run installation
bash install_vllm.sh ~/vllm_app
```

### Step 6: Access from Windows

WSL uses a virtual network adapter. To access vLLM from Windows:

1. **Find your WSL IP address**:

```
# Inside WSL
hostname -I
```

2. **Access from Windows browser**:
   - Use `http://<WSL_IP>:8000` in your browser
   - Or use `http://localhost:8000` (Windows 11 automatically forwards localhost)

### WSL-Specific Notes

#### File System Performance
- Store your models and vLLM installation in the Linux filesystem (`/home/username/`) for best performance
- Avoid using Windows filesystem paths (`/mnt/c/...`) as they are significantly slower
- Access WSL files from Windows Explorer via `\\wsl$\Ubuntu-22.04\home\username\`

#### Memory Management
WSL2 uses dynamic memory allocation. If you have large models, you may want to configure WSL memory limits:

Create or edit `C:\Users\<YourUsername>\.wslconfig`:

```
[wsl2]
memory=32GB
processors=8
swap=8GB
```

Restart WSL: `wsl --shutdown` (in PowerShell)

#### Starting WSL Service on Windows Boot

The systemd service will work within WSL, but WSL itself doesn't auto-start. To auto-start vLLM on Windows boot:

1. Create a scheduled task in Windows
2. Or use Windows Terminal with startup settings
3. Or manually start WSL and the service when needed

#### GPU Memory
Windows reserves some GPU memory for the desktop. If you encounter OOM errors, close unnecessary applications or adjust your model's GPU memory utilization.

### Troubleshooting WSL

**GPU not detected in WSL:**
```
# Verify NVIDIA driver in Windows
# From PowerShell
nvidia-smi

# Update WSL kernel
wsl --update
```

**Network connectivity issues:**
```
# Reset WSL network
# From PowerShell (as Administrator)
wsl --shutdown
Get-NetAdapter | Where-Object Name -like "*WSL*" | Restart-NetAdapter
```

**Slow performance:**
- Ensure files are in Linux filesystem, not `/mnt/c/`
- Check that WSL2 is being used: `wsl -l -v`
- Allocate more resources in `.wslconfig`

## Dev vs Stable

- **Stable**: Installs the latest released version from PyPI. Recommended for production use.
- **Dev**: Installs from the GitHub main branch. Useful for testing latest features or contributing to vLLM.

## Project Structure

```
vllm_deployer/
├── install_vllm.sh      # Main installation script
├── upgrade_vllm.sh      # Upgrade script
├── manage_service.sh    # Service management script
├── run.sh               # vLLM runner script
├── pull_model.sh        # Model download script
├── .gitignore
├── CHANGELOG.md
└── README.md
```

## Workflow Example

### Linux

```
# 1. Install vLLM
bash install_vllm.sh /opt/vllm

# 2. Pull a model
cd /opt/vllm
./pull_model.sh meta-llama/Llama-2-7b-hf

# 3. Update .env with your model configuration
nano .env
# Add: MODEL_LIST='Llama-2-7b-hf:vllm_config.json'

# 4. Test manually first
./run.sh

# 5. If everything works, install as service
./manage_service.sh install

# 6. Check service status
systemctl status vllm
```

### Windows (WSL)

```
# From PowerShell (Windows side)
wsl --install -d Ubuntu-22.04

# Inside WSL Ubuntu
cd ~
git clone https://github.com/ParisNeo/vllm_deployer.git
cd vllm_deployer
bash install_vllm.sh ~/vllm_app

# Pull and configure model
cd ~/vllm_app
./pull_model.sh facebook/opt-1.3b

# Edit .env
nano .env
# Add: MODEL_LIST='opt-1.3b:vllm_config.json'

# Test
./run.sh

# Access from Windows browser at http://localhost:8000
```

## Troubleshooting

### Service won't start
Check logs: `journalctl -u vllm -n 50`

### Model not loading
Verify model path in `.env` and ensure the model files exist in `MODEL_DIR`

### Permission issues
Ensure the service runs as the correct user with access to model files

### GPU not detected
Verify CUDA installation and GPU drivers are properly installed

### Out of memory errors
- Reduce batch size in model config
- Use smaller models or quantized versions
- Close other GPU-intensive applications
- For WSL: allocate more memory in `.wslconfig`

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/ParisNeo/vllm_deployer).

## License

This project is open source and available under the MIT License.

## Links

- Project Repository: https://github.com/ParisNeo/vllm_deployer
- vLLM Documentation: https://docs.vllm.ai
- Hugging Face Models: https://huggingface.co/models
- WSL Documentation: https://docs.microsoft.com/en-us/windows/wsl/

---

For questions or issues, please open an issue on GitHub.
