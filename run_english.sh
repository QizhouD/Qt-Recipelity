#!/bin/bash
echo "Starting Recipelity - Intelligent Recipe Management System (English Version)"
echo "=================================================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
REQUIRED_VERSION="3.9"

if [ $(echo -e "$PYTHON_VERSION\n$REQUIRED_VERSION" | sort -V | head -n1) != "$REQUIRED_VERSION" ]; then
    echo "Warning: Python version $PYTHON_VERSION is installed. Python 3.9 or higher is recommended."
    echo ""
fi

# Check if required packages are installed
REQUIRED_PACKAGES=("PyQt6" "sqlalchemy" "requests" "beautifulsoup4" "matplotlib" "opencv-python")

MISSING_PACKAGES=()
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo "Missing required packages: ${ echo "${MISSING_PACKAGES[@]}"
    echo ""
    echo "Installing missing packages..."
    pip3 install "${MISSING_PACKAGES[@]}"
    echo ""
fi

# Create data directory if it doesn't exist
mkdir -p data

# Run the application
echo "Starting Recipelity..."
echo ""
python3 main_en.py

# Check if the application started successfully
if [ $? -ne 0 ]; then
    echo ""
    echo "Error: Failed to start Recipelity. Please check the error messages above."
    echo "If you're using Python 3.13, try installing the fixed requirements:"
    echo "pip3 install -r requirements_fixed.txt"
    exit 1
fi
