<div align="center">

# vLLM Deployer 🚀

### The Ultimate Management UI for vLLM

[![GitHub Stars](https://img.shields.io/github/stars/ParisNeo/vllm_deployer?style=social)](https://github.com/ParisNeo/vllm_deployer/stargazers)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![vLLM](https://img.shields.io/badge/vLLM-latest-orange.svg)](https://docs.vllm.ai)

Go from a bare server to a production-ready, multi-model LLM serving platform in minutes. vLLM Deployer provides a powerful web UI to install, manage, and monitor your vLLM instances with zero configuration headaches.

![vLLM Deployer Dashboard Screenshot](https://raw.githubusercontent.com/ParisNeo/vllm_deployer/main/vllm_deployer.png)

</div>

---

## Why vLLM Deployer?

[vLLM](https://github.com/vllm-project/vllm) is the fastest LLM inference engine, but managing its setup, configuration, and multiple running models can be a complex task involving manual CLI commands, `screen` sessions, and scattered YAML files. **vLLM Deployer solves this.**

It wraps the power of vLLM in a sophisticated and intuitive web interface, transforming the tedious process of LLM deployment into a seamless, click-and-go experience.

| Before vLLM Deployer 😩 | After vLLM Deployer ✨ |
| :--- | :--- |
| Manual `pip install` & dependency hell | ✅ **One-Command Installation** |
| Juggling SSH and `tmux`/`screen` sessions | ✅ **Centralized Web Dashboard** |
| Editing complex YAML files by hand | ✅ **Easy UI-Based Model Configuration** |
| No visibility into GPU usage | ✅ **Live GPU Monitoring & Assignment** |
| Manually pulling models with `huggingface-cli` | ✅ **One-Click Model Pulling from UI** |
| Error-prone, manual process management | ✅ **Robust, Production-Ready Service** |

## Key Benefits

- 🚀 **Deploy in Minutes, Not Days:** Go from a bare server to a fully managed vLLM instance with a single installation script. What used to take hours of manual setup is now automated.
- 🖥️ **Effortless Web UI Management:** Pull models from Hugging Face, configure GPU memory, set quantization, and manage model parameters through an intuitive interface. No more command-line guesswork.
- 📈 **Maximize GPU ROI:** With live GPU monitoring, you can see exactly how your expensive hardware is being utilized. Assign models to specific GPUs and optimize your resource allocation with ease.
- 📚 **Centralized Model Hub:** Manage your entire library of local Hugging Face models from a single dashboard. View download status, size, and configuration at a glance, whether models are running or not.
- 🔒 **Production-Ready & Secure:** Built with a database backend, a secure authentication layer, and optional `systemd` integration, vLLM Deployer is designed for robust, 24/7 operation.
- ⚙️ **One-Click Upgrades:** Keep vLLM at the cutting edge. Upgrade to the latest version directly from the web UI with real-time log streaming.

## 🚀 3-Step Quick Start

1.  **Install**
    ```bash
    git clone https://github.com/ParisNeo/vllm_deployer.git
    cd vllm_deployer
    bash install_vllm.sh
    ```

2.  **Run the Manager**
    ```bash
    ./run.sh
    ```

3.  **Manage Everything from Your Browser**
    - Open `http://localhost:9000`.
    - Login with `admin` / `admin123`.
    - Pull your first model (e.g., `mistralai/Mistral-7B-Instruct-v0.2`) and click "Start"!

## Who is this for?

-   **ML Engineers & MLOps:** Streamline your deployment workflows and provide a stable, manageable serving platform for your teams.
-   **Researchers & Data Scientists:** Quickly spin up, test, and tear down different models without waiting for DevOps resources.
-   **Startups & Small Teams:** Get a powerful, enterprise-grade LLM serving solution without the high cost and complexity of larger platforms.
-   **AI Hobbyists & Enthusiasts:** Easily run and manage multiple LLMs on your own hardware without the command-line hassle.

---

## 📋 Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Security](#security)
- [Usage](#usage)
- [Windows/WSL Setup](#windowswsl-setup)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 📦 Requirements

-   **OS**: Linux (Ubuntu 20.04+, Debian 11+) or Windows 10/11 with WSL2
-   **Python**: 3.9+
-   **GPU**: NVIDIA GPU with CUDA 12.1+ (Compute Capability 7.0+)
-   **Disk Space**: Varies by model (10GB+ recommended)
-   **RAM**: 16GB+ recommended

## 📥 Installation

Our one-command installer handles everything from setting up a virtual environment to installing dependencies and configuring the service.

```bash
# Clone the repository
git clone https://github.com/ParisNeo/vllm_deployer.git
cd vllm_deployer

# Install to the current directory
bash install_vllm.sh

# Or, specify a custom installation directory
bash install_vllm.sh /opt/vllm_deployer
```

For the latest features, you can install the development version of vLLM:
```bash
bash install_vllm.sh --dev
```
The script will guide you through the process and create a `QUICKSTART.txt` file with next steps.

## 🔒 Security

The default login for the Web UI is `admin` / `admin123`. You can and should change this immediately.

#### Change Password from the UI (Recommended)
1.  Log in to the web interface.
2.  Click the "Admin" button in the header.
3.  Follow the prompts to set a new password.

#### Change Password via Environment Variable (for advanced/dockerized setups)
1.  Generate a SHA256 hash for your password:
    ```bash
    echo -n 'your_secure_password' | sha256sum
    ```
2.  Set the environment variable before running the manager:
    ```bash
    export VLLM_ADMIN_PASSWORD_HASH='your_hash_here'
    ./run.sh
    ```

## 🎮 Usage

The entire workflow is managed through the web UI.

1.  **Start the Manager:**
    ```bash
    ./run.sh
    ```
2.  **Open the UI:** Navigate to `http://localhost:9000`.
3.  **Pull a Model:** Use the "Pull New Model" form to download a model from Hugging Face. You'll see real-time download logs.
4.  **Configure & Start:** Once downloaded, click "Edit" to adjust parameters like GPU memory utilization, or just click "Start" to launch it with defaults.
5.  **Monitor:** Watch the live GPU and system stats on the dashboard. View real-time logs for any running model.
6.  **Test Your Model:** Once a model is running on its assigned port (e.g., 8000), you can use it via its OpenAI-compatible API:
    ```bash
    curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
        "model": "your-model-name",
        "messages": [{"role": "user", "content": "Hello! Tell me a joke."}]
    }'
    ```

## 💻 Windows/WSL Setup

vLLM Deployer works perfectly on Windows via WSL2 with full GPU acceleration. See our detailed [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md) for a full walkthrough.

## 🔧 Troubleshooting

-   **Model Fails to Start:** Check the logs! Click the "Logs" button next to the model in the UI to see the output from the vLLM server. Common causes are CUDA OOM (Out of Memory) or configuration errors.
-   **`vllm` command not found:** Ensure you are running scripts from your installation directory, which allows them to activate the correct virtual environment.
-   **CUDA Out of Memory:** Edit the model configuration in the UI and lower the "GPU Memory Utilization" (e.g., to `0.8`). You can also try using a quantized model version (e.g., AWQ, GPTQ).

## 📁 Project Structure

```vllm_deployer/
├── frontend/                # Web UI files (HTML, JS)
├── install_vllm.sh          # Main installation script
├── manage_service.sh        # systemd service management
├── run.sh                   # Manager launcher
├── vllm_manager.py          # FastAPI backend
├── ...
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
