# Changelog

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
