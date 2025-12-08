#!/bin/bash
# create_env.sh - Create a Python virtual environment and install required packages.
# Usage: ./create_env.sh [env_name]
# If no env_name is provided, defaults to myEnv.
# Installs: pip (upgrade), google, protobuf==3.17.3, PyQt5

set -e  # Exit on error

# Function to display help
show_help() {
    echo "Usage: ./create_env.sh [env_name]"
    echo "  env_name  Optional name of the virtual environment folder (default: myEnv)"
    echo "Example: ./create_env.sh .venv"
    exit 0
}

# Parse arguments
ENV_NAME="${1:-myEnv}"

if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_help
fi

echo "Creating / using environment: $ENV_NAME"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found in PATH. Install Python3 and retry."
    echo "On RedHat/CentOS/RHEL, run: sudo yum install python3"
    exit 1
fi

# Create venv if it does not exist
if [ ! -f "$ENV_NAME/bin/python" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv "$ENV_NAME"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        exit 1
    fi
else
    echo "[INFO] Virtual environment already exists."
fi

# Activate environment
source "$ENV_NAME/bin/activate"
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to activate virtual environment."
    exit 1
fi

echo "[INFO] Upgrading pip..."
python -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to upgrade pip."
    exit 1
fi

echo "[INFO] Installing required packages: google protobuf==3.17.3 PyQt5"
pip install google protobuf==3.17.3 PyQt5
if [ $? -ne 0 ]; then
    echo "[ERROR] Package installation failed."
    exit 1
fi

echo "[SUCCESS] Environment '$ENV_NAME' ready."
echo "To activate later: source $ENV_NAME/bin/activate"
echo "To deactivate: deactivate"
