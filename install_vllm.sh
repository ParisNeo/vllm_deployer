#!/bin/bash

#############################################
# vLLM Deployer Installation Script
# Version: 1.3.1
# Description: Sets up vLLM with management interface
#############################################

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Print header
print_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

print_step() {
    echo -e "${GREEN}[Step $1/$2]${NC} ${BLUE}$3${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Banner
echo ""
print_header "vLLM Deployer Installer v1.3.1"
echo ""
echo -e "${MAGENTA}Fast, scalable LLM serving with management interface${NC}"
echo ""

#############################################
# Parse Arguments
#############################################

DEV_MODE=false
TOTAL_STEPS=8

# Check for --dev flag
if [ "$1" == "--dev" ]; then
    DEV_MODE=true
    shift
    print_info "Development mode enabled"
    echo ""
fi

INSTALL_DIR="${1:-$(pwd)}"
MODEL_DIR="${2:-$INSTALL_DIR/models}"
VENV_DIR="$INSTALL_DIR/venv"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}Configuration:${NC}"
echo "  Install directory:  $INSTALL_DIR"
echo "  Model directory:    $MODEL_DIR"
echo "  Virtual environment: $VENV_DIR"
echo "  Installation mode:  $([ "$DEV_MODE" = true ] && echo 'Development (from source)' || echo 'Stable (from PyPI)')"
echo ""

# Confirm installation
read -p "$(echo -e ${YELLOW}Continue with installation? [Y/n]:${NC} )" -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ -n $REPLY ]]; then
    echo "Installation cancelled."
    exit 0
fi
echo ""

#############################################
# Step 1: Create Directories
#############################################

print_step 1 $TOTAL_STEPS "Creating directory structure"
echo ""

mkdir -p "$INSTALL_DIR"
if [ $? -eq 0 ]; then
    print_success "Created install directory: $INSTALL_DIR"
else
    print_error "Failed to create install directory"
    exit 1
fi

mkdir -p "$MODEL_DIR"
if [ $? -eq 0 ]; then
    print_success "Created models directory: $MODEL_DIR"
else
    print_error "Failed to create models directory"
    exit 1
fi

echo ""

#############################################
# Step 2: Check Python Version
#############################################

print_step 2 $TOTAL_STEPS "Checking Python installation"
echo ""

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.9 or higher and try again"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

print_success "Found Python $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    print_error "Python 3.9 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

print_success "Python version is compatible"
echo ""

#############################################
# Step 3: Create Virtual Environment
#############################################

print_step 3 $TOTAL_STEPS "Creating Python virtual environment"
echo ""

if [ -d "$VENV_DIR" ]; then
    print_warning "Virtual environment already exists at $VENV_DIR"
    read -p "$(echo -e ${YELLOW}Remove and recreate? [y/N]:${NC} )" -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        print_info "Removed existing virtual environment"
    else
        print_info "Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        print_success "Virtual environment created successfully"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
if [ $? -eq 0 ]; then
    print_success "Virtual environment activated"
else
    print_error "Failed to activate virtual environment"
    exit 1
fi

echo ""

#############################################
# Step 4: Upgrade pip and Install Core Dependencies
#############################################

print_step 4 $TOTAL_STEPS "Installing core dependencies"
echo ""

print_info "Upgrading pip..."
pip install --upgrade pip --quiet
if [ $? -eq 0 ]; then
    print_success "pip upgraded successfully"
else
    print_warning "pip upgrade had issues, continuing anyway..."
fi

echo ""

#############################################
# Step 5: Install vLLM
#############################################

print_step 5 $TOTAL_STEPS "Installing vLLM"
echo ""

if [ "$DEV_MODE" = true ]; then
    print_info "Installing vLLM from source (development version)"
    echo "This may take 10-15 minutes..."
    echo ""
    
    cd "$INSTALL_DIR"
    
    if [ -d "vllm-source" ]; then
        print_warning "vLLM source directory already exists"
        read -p "$(echo -e ${YELLOW}Pull latest changes? [Y/n]:${NC} )" -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            cd vllm-source
            git pull
            cd ..
        fi
    else
        git clone https://github.com/vllm-project/vllm.git vllm-source
        if [ $? -ne 0 ]; then
            print_error "Failed to clone vLLM repository"
            exit 1
        fi
        print_success "Cloned vLLM repository"
    fi
    
    cd vllm-source
    pip install -e .
    if [ $? -eq 0 ]; then
        print_success "vLLM installed from source"
    else
        print_error "Failed to install vLLM from source"
        exit 1
    fi
    cd "$INSTALL_DIR"
else
    print_info "Installing vLLM stable version from PyPI"
    echo "This may take 5-10 minutes..."
    echo ""
    
    pip install vllm
    if [ $? -eq 0 ]; then
        print_success "vLLM installed successfully"
    else
        print_error "Failed to install vLLM"
        exit 1
    fi
fi

# Verify installation
if command -v vllm &> /dev/null; then
    VLLM_VERSION=$(pip show vllm | grep Version | awk '{print $2}')
    print_success "vLLM version $VLLM_VERSION is ready"
else
    print_error "vLLM installation verification failed"
    exit 1
fi

echo ""

#############################################
# Step 6: Install Management Interface Dependencies
#############################################

print_step 6 $TOTAL_STEPS "Installing management interface dependencies"
echo ""

print_info "Installing FastAPI, Uvicorn, SQLAlchemy, and utilities..."
pip install fastapi uvicorn httpx psutil gputil pydantic sqlalchemy huggingface-hub --quiet
if [ $? -eq 0 ]; then
    print_success "Management dependencies installed"
else
    print_warning "Some dependencies may have issues, but continuing..."
fi

echo ""

#############################################
# Step 7: Copy Scripts and Setup Configuration
#############################################

print_step 7 $TOTAL_STEPS "Copying scripts and creating configuration"
echo ""

# List of scripts to copy
SCRIPTS_TO_COPY=(
    "run.sh"
    "manage_service.sh"
    "upgrade_vllm.sh"
    "vllm_manager.py"
)

print_info "Copying deployment scripts..."
COPIED_COUNT=0
for script in "${SCRIPTS_TO_COPY[@]}"; do
    if [ -f "$SCRIPT_DIR/$script" ]; then
        cp "$SCRIPT_DIR/$script" "$INSTALL_DIR/"
        chmod +x "$INSTALL_DIR/$script"
        print_success "  ✓ $script"
        COPIED_COUNT=$((COPIED_COUNT + 1))
    else
        print_warning "  ⚠ $script not found in source directory"
    fi
done

echo ""
print_success "Copied $COPIED_COUNT script(s) to $INSTALL_DIR"
echo ""

# Create .env configuration file
print_info "Creating .env configuration file..."
cat > "$INSTALL_DIR/.env" <<EOL
# vLLM Deployer Configuration
# Generated on $(date)

# Model storage directory
MODEL_DIR=$MODEL_DIR

# Models are now managed via the Web UI (http://localhost:9000)

# Default port for vLLM server (when using run.sh)
VLLM_PORT=8000

# Installation mode (do not modify manually)
DEV_MODE=$DEV_MODE

# Installation directory
INSTALL_DIR=$INSTALL_DIR
EOL

if [ $? -eq 0 ]; then
    print_success ".env configuration file created"
else
    print_error "Failed to create .env file"
    exit 1
fi

echo ""

#############################################
# Step 8: Create README and Quick Start Guide
#############################################

print_step 8 $TOTAL_STEPS "Creating quick start guide"
echo ""

cat > "$INSTALL_DIR/QUICKSTART.txt" <<'EOL'
╔════════════════════════════════════════════════════════════════╗
║           vLLM Deployer - Quick Start Guide                    ║
╚════════════════════════════════════════════════════════════════╝

GETTING STARTED
───────────────

1. Start the Manager
   ────────────────
   ./run.sh   

2. Open the Web UI
   ────────────────
   Open http://localhost:9000 in your browser.
   Login with default credentials:
     - Username: admin
     - Password: admin123

3. Download and Run a Model
   ────────────────
   - Use the UI to pull a model (e.g., facebook/opt-125m).
   - Once downloaded, click "Start" next to the model.

4. Test Your Model
   ───────────────
   Once a model is running (e.g., on port 8000), you can test it:
   
   curl http://localhost:8000/v1/models
   
   Or send a test message:
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "opt-125m", "messages": [{"role": "user", "content": "Hello!"}]}'

AVAILABLE COMMANDS
──────────────────
./run.sh                          - Start the vLLM Manager Web UI
./manage_service.sh install       - Install as systemd service
./manage_service.sh uninstall     - Remove systemd service
./upgrade_vllm.sh                 - Upgrade vLLM to latest version

MANAGEMENT UI
─────────────
Web Interface: http://localhost:9000
API docs:      http://localhost:9000/docs

From the UI, you can:
  • Pull new models from Hugging Face
  • Start, stop, and restart models
  • Monitor GPU usage
  • Configure model parameters
  • Delete models

RECOMMENDED MODELS FOR TESTING
───────────────────────────────

Small (fast, minimal GPU):
  • facebook/opt-125m
  • facebook/opt-1.3b
  
Medium (production ready):
  • mistralai/Mistral-7B-Instruct-v0.2
  • meta-llama/Llama-2-7b-chat-hf

TROUBLESHOOTING
───────────────
No models available:
  → Use the Web UI to pull a model.

vLLM not found:
  → Activate venv: source venv/bin/activate

Out of memory:
  → Try a smaller model or adjust gpu_memory_utilization in the UI config.

DOCUMENTATION
─────────────

Full README: cat README.md
GitHub: https://github.com/ParisNeo/vllm_deployer
vLLM Docs: https://docs.vllm.ai

╚════════════════════════════════════════════════════════════════╝
EOL

print_success "Quick start guide created: $INSTALL_DIR/QUICKSTART.txt"
echo ""

#############################################
# Installation Complete
#############################################

print_header "Installation Complete!"
echo ""

print_success "vLLM Deployer has been successfully installed!"
echo ""

echo -e "${CYAN}Installation Summary:${NC}"
echo "────────────────────────────────────────"
echo "  Installation directory: $INSTALL_DIR"
echo "  Models directory:       $MODEL_DIR"
echo "  Virtual environment:    $VENV_DIR"
echo "  vLLM version:          $VLLM_VERSION"
echo "  Installation mode:     $([ "$DEV_MODE" = true ] && echo 'Development' || echo 'Stable')"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "────────────────────────────────────────"
echo ""
echo -e "${GREEN}1.${NC} Navigate to installation directory:"
echo -e "   ${BLUE}cd $INSTALL_DIR${NC}"
echo ""
echo -e "${GREEN}2.${NC} Start the vLLM manager:"
echo -e "   ${BLUE}./run.sh${NC}"
echo ""
echo -e "${GREEN}3.${NC} Open the Web UI in your browser at ${BLUE}http://localhost:9000${NC}"
echo "   Login with 'admin' / 'admin123' and pull your first model."
echo ""
echo -e "${GREEN}4.${NC} (Optional) Install as a system service:"
echo -e "   ${BLUE}./manage_service.sh install${NC}"
echo ""

echo -e "${MAGENTA}Management Interface:${NC}"
echo "────────────────────────────────────────"
echo "  Start manager:     ./run.sh"
echo "  API docs:          http://localhost:9000/docs"
echo "  Interactive UI:    http://localhost:9000"
echo ""

echo -e "${GREEN}For detailed documentation, see README.md${NC}"
echo -e "${GREEN}For issues or questions: https://github.com/ParisNeo/vllm_deployer/issues${NC}"
echo ""

print_header "Happy Serving! 🚀"
echo ""

# Save installation info
cat > "$INSTALL_DIR/.install_info" <<EOL
INSTALL_DATE=$(date -Iseconds)
INSTALL_DIR=$INSTALL_DIR
MODEL_DIR=$MODEL_DIR
VENV_DIR=$VENV_DIR
DEV_MODE=$DEV_MODE
VLLM_VERSION=$VLLM_VERSION
PYTHON_VERSION=$PYTHON_VERSION
EOL
