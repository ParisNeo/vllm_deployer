# Changelog

## 1.2.3 - 2025-11-09
- Enhanced `pull_model.sh` with comprehensive help text and examples
- Added popular model recommendations by size
- Added GPU memory requirement estimates
- Added "Finding and Installing Models" section to README with:
  - Model size categories and recommendations
  - Step-by-step first model installation
  - Quantized model information
  - Authentication instructions for protected models
  - Troubleshooting guide
- Improved error messages in pull_model.sh

## 1.2.2 - 2025-11-09
- Added comprehensive Windows/WSL setup instructions to README
- Included WSL2 installation steps
- Added GPU support configuration for WSL
- Added WSL-specific troubleshooting section
- Documented filesystem performance considerations for WSL
- Added workflow examples for both Linux and Windows users

## 1.2.1 - 2025-11-09
- Enhanced `run.sh` with verbose output and error handling
- Added configuration validation (checks for empty MODEL_LIST, missing directories)
- Added colored output for better visibility
- Added proper error messages when models or configs are missing
- Added graceful shutdown with Ctrl+C handling

## 1.2.0 - 2025-11-09
- Made systemd service creation optional in `install_vllm.sh`.
- Added `manage_service.sh` script for installing and uninstalling the systemd service separately.
- Updated `upgrade_vllm.sh` to handle service restart only if service exists.
- Users can now test the application without creating a system service.

## 1.1.0 - 2025-11-09
- Added `--dev` flag to `install_vllm.sh` for installing vLLM from source (development version).
- Created `upgrade_vllm.sh` script for upgrading vLLM installations (both stable and dev).
- Updated `.gitignore` to exclude `vllm-source/` and `.env` files.
- Enhanced `.env` to track installation mode (dev/stable).

## 1.0.0 - 2025-11-09
- Initial release with:
  - `install_vllm.sh` for environment setup, script copying, systemd service creation.
  - `run.sh` for starting vLLM with models/configs from `.env`.
  - `pull_model.sh` for downloading and configuring models from Hugging Face.
  - `.gitignore` to exclude virtual environment and models directory.