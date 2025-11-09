# Changelog

All notable changes to the vLLM Deployer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-11-09

### 🚀 Major Release: vLLM Manager Pro

This is a major version upgrade introducing a complete web-based management interface with enterprise features.

### Added

**Management Interface (`vllm_manager_pro.py`)**:
- **Web UI Dashboard**: Beautiful, responsive web interface with real-time updates
- **Authentication System**: 
  - Secure login with password hashing (SHA256)
  - Session-based authentication with configurable timeout
  - Cookie-based session management
  - Default admin credentials (admin/admin123) with security warnings
  - Environment variable support for custom password hash
- **Model Management**:
  - Full CRUD operations (Create, Read, Update, Delete) via web interface
  - Start, stop, and restart models with single click
  - Support for both text-generation and embedding models
  - Automatic model type detection
  - Model size display and metadata
  - Real-time status monitoring
- **GPU Management**:
  - Live GPU monitoring with GPUtil integration
  - Memory usage tracking (total, used, free)
  - GPU utilization percentage display
  - Temperature monitoring
  - Visual progress bars for memory usage
  - Assign models to specific GPU(s)
  - View which models are running on each GPU
  - Dynamic GPU reassignment with automatic restart
- **Real-time Dashboard**:
  - System statistics (CPU, RAM, GPU usage)
  - Model count (total, running, stopped)
  - GPU summary (count, memory usage)
  - Manager uptime display
  - Auto-refresh every 5 seconds
  - Resource usage per running model
  - Process monitoring (PID, memory, CPU per model)
- **Advanced Features**:
  - Multi-model concurrent management
  - Automatic port allocation to prevent conflicts
  - Health check system for running models
  - Process isolation and tracking
  - Persistent state across manager restarts
  - Session persistence
  - Request proxying to model endpoints
  - Interactive API documentation at /docs
  - RESTful API for programmatic access

**New Endpoints**:
- `POST /api/login` - User authentication
- `POST /api/logout` - Session termination
- `GET /api/check-auth` - Authentication verification
- `GET /api/models/available` - List all available models
- `GET /api/models/running` - List running models with detailed status
- `POST /api/models/{name}/start` - Start a model instance
- `POST /api/models/{name}/stop` - Stop a running model
- `POST /api/models/{name}/restart` - Restart a model
- `DELETE /api/models/stop-all` - Stop all running models
- `GET /api/gpus` - Get GPU information and assignments
- `POST /api/models/{name}/assign-gpu` - Reassign model to different GPU(s)
- `GET /api/dashboard/stats` - Get comprehensive dashboard statistics
- `GET /` - Web UI interface (embedded HTML)

**New Scripts**:
- `start_manager_pro.sh`: Launch script for the enhanced manager
  - Automatic dependency installation
  - Security warnings for default passwords
  - Clear usage instructions

### Changed

- Manager now runs on dedicated port 9000 (configurable)
- Enhanced state management with session tracking
- Improved error handling with detailed HTTP responses
- Better process management with graceful shutdown
- Enhanced logging and monitoring capabilities

### Security

- Password-based authentication (SHA256 hashing)
- Session token management with expiration
- HTTP-only cookies for session security
- CORS middleware for API security
- Configurable session timeout (default: 1 hour)
- Environment variable support for production passwords

### Dependencies

New dependencies added:
- `GPUtil` - GPU monitoring and management
- Enhanced `pydantic` models for data validation
- Additional `psutil` features for process monitoring

### UI Features

- Color-coded status indicators (running/stopped)
- Responsive design for mobile and desktop
- Real-time updates without page refresh
- Visual progress bars for GPU memory
- Interactive model cards with action buttons
- System statistics dashboard
- Professional gradient theme
- Modal confirmations for destructive actions

### Performance

- Auto-refresh dashboard every 5 seconds
- Efficient GPU polling
- Optimized state persistence
- Minimal resource overhead
- Async operations for better responsiveness

### Breaking Changes

- Original `vllm_manager.py` superseded by `vllm_manager_pro.py`
- Different port (9000 instead of previous default)
- New authentication requirement for all endpoints
- Enhanced API response formats
- Additional dependencies required

### Migration Guide

To upgrade from previous version:

1. Install new dependencies:
   ```
   pip install gputil pydantic
   ```

2. Set admin password (recommended):
   ```
   export VLLM_ADMIN_PASSWORD_HASH=$(echo -n 'your_password' | sha256sum | cut -d' ' -f1)
   ```

3. Launch new manager:
   ```
   ./start_manager_pro.sh
   ```

4. Access web UI at http://localhost:9000
5. Login with credentials (default: admin/admin123)

### Documentation

- Added comprehensive security documentation
- Added GPU management guide
- Added embedding model support documentation
- Updated API documentation with new endpoints

## [1.3.3] - 2025-11-09

### Fixed
- **Critical**: Fixed "Config file must be of a yaml/yml type" error
- Changed configuration format from JSON to YAML (vLLM requirement)
- Fixed config file parsing to properly handle YAML format

### Changed
- **Complete rewrite of `pull_model.sh`**:
  - Now creates YAML configuration files instead of JSON
  - Enhanced help system with comprehensive model recommendations
  - Improved error handling with detailed solutions
  - Better visual feedback with color-coded output
  - Automatic .env backup before modifications
  - Platform compatibility (Linux and macOS sed differences)
  - Model size display after download
  - Comprehensive next steps guidance

- **Complete rewrite of `run.sh`**:
  - Implemented proper YAML config parser (`read_yaml_value` function)
  - Enhanced error handling with step-by-step guidance
  - Automatic default YAML config creation when missing
  - Multi-model support with automatic port assignment
  - Detailed configuration display for each model
  - Improved logging with model name and port prefixes
  - Better process management and graceful shutdown
  - Comprehensive test command examples
  - Version detection and display

### Added
- YAML configuration support with inline documentation
- Automatic port offset calculation for multiple models
- Configuration validation and auto-creation
- Enhanced visual feedback throughout both scripts
- Support for all vLLM YAML config parameters

## [1.3.2] - 2025-11-09

### Added
- Complete rewrite of `install_vllm.sh` with enhanced user experience
- Auto-generated `QUICKSTART.txt` guide
- Installation metadata saved to `.install_info` file
- Detailed .env file with inline documentation

## [1.3.1] - 2025-11-09

### Added
- Automatic .env configuration in `pull_model.sh`
- Models automatically added to MODEL_LIST after download

## [1.3.0] - 2025-11-09

### Added
- FastAPI-based management interface (`vllm_manager.py`)
- Basic REST API for model management

## [1.2.4] - 2025-11-09

### Added
- Comprehensive error handling in `run.sh`
- Step-by-step user guidance

## [1.2.3] - 2025-11-09

### Added
- Comprehensive help system in `pull_model.sh`
- Model recommendations by size

## [1.2.2] - 2025-11-09

### Added
- Complete Windows/WSL setup guide

## [1.2.1] - 2025-11-09

### Added
- Verbose output and error handling

## [1.2.0] - 2025-11-09

### Changed
- Made systemd service optional

## [1.1.0] - 2025-11-09

### Added
- Development installation mode
- Upgrade script

## [1.0.0] - 2025-11-09

### Added
- Initial release

---

## Version History Summary

- **2.0.0** - vLLM Manager Pro with Web UI, authentication, and advanced features
- **1.3.3** - YAML config support (critical bug fix)
- **1.3.2** - Enhanced installer with detailed feedback
- **1.3.1** - Automatic .env configuration
- **1.3.0** - FastAPI management interface
- **1.2.x** - Error handling, WSL support, model guides
- **1.1.0** - Dev mode and upgrade script
- **1.0.0** - Initial release

---

## Security Notes

### Version 2.0.0 Security

**Default Credentials**: The default password is `admin123`. This MUST be changed in production environments.

**Setting Custom Password**:
```
# Generate password hash
echo -n 'your_secure_password' | sha256sum

# Set environment variable
export VLLM_ADMIN_PASSWORD_HASH='your_hash_here'

# Or add to .bashrc/.zshrc
echo 'export VLLM_ADMIN_PASSWORD_HASH="your_hash_here"' >> ~/.bashrc
```

**Session Security**:
- Sessions expire after 1 hour of inactivity
- Session tokens stored in HTTP-only cookies
- Session state persisted to disk for manager restarts

**Production Recommendations**:
1. Always set a custom admin password
2. Use HTTPS in production (reverse proxy recommended)
3. Restrict manager port access with firewall rules
4. Regular security updates
5. Monitor authentication logs

## Contributing

Please update this changelog when making significant changes to the project.
Follow the [Keep a Changelog](https://keepachangelog.com/) format.
