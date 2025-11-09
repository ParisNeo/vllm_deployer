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

## Files

- `install_vllm.sh`: Sets up a Python virtual environment, installs vLLM (stable or dev), copies scripts
- `upgrade_vllm.sh`: Upgrades vLLM to the latest version (respects dev/stable mode)
- `manage_service.sh`: Install or uninstall the vLLM systemd service
- `run.sh`: Runs vLLM server loading specified models from `.env` configuration
- `pull_model.sh`: Downloads and configures Hugging Face models for use with vLLM
- `.gitignore`: Ignores `venv`, `models`, `vllm-source`, and `.env` files
- `CHANGELOG.md`: Project changelog

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

## Requirements

- Python 3.9+
- Git (for dev installation)
- `huggingface-cli` for pulling models (optional: `pip install huggingface-hub`)
- Linux with systemd (for service management)
- NVIDIA GPU with CUDA support (recommended)

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

## Troubleshooting

### Service won't start
Check logs: `journalctl -u vllm -n 50`

### Model not loading
Verify model path in `.env` and ensure the model files exist in `MODEL_DIR`

### Permission issues
Ensure the service runs as the correct user with access to model files

### GPU not detected
Verify CUDA installation and GPU drivers are properly installed

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/ParisNeo/vllm_deployer).

## License

This project is open source and available under the MIT License.

## Links

- Project Repository: https://github.com/ParisNeo/vllm_deployer
- vLLM Documentation: https://docs.vllm.ai
- Hugging Face Models: https://huggingface.co/models

---

For questions or issues, please open an issue on GitHub.
