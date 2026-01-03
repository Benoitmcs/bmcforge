#!/bin/bash
# BMCForge installer
# Creates venv, installs package, and sets up global 'bmc' command

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
BIN_NAME="bmc"

echo "Installing BMCForge..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Install package
echo "Installing package..."
"$VENV_DIR/bin/pip" install -q -e "$SCRIPT_DIR"

# Determine install location for wrapper
if [ -w /usr/local/bin ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -d "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
else
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
    echo "Note: Add $INSTALL_DIR to your PATH"
fi

# Create wrapper script
WRAPPER="$INSTALL_DIR/$BIN_NAME"
echo "Creating wrapper at $WRAPPER..."

cat > "$WRAPPER" << EOF
#!/bin/bash
exec "$VENV_DIR/bin/bmc" "\$@"
EOF

chmod +x "$WRAPPER"

echo ""
echo "BMCForge installed successfully!"
echo "Run 'bmc --help' to get started."

# Check if wrapper is in PATH
if ! command -v bmc &> /dev/null; then
    echo ""
    echo "Note: Add this to your shell config:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi
