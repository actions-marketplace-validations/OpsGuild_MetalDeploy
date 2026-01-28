#!/bin/bash

# MetalDeploy One-Liner Installer
# Usage: curl -sSL https://raw.githubusercontent.com/OpsGuild/MetalDeploy/main/scripts/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting MetalDeploy installation...${NC}"

# Check for requirements
for cmd in python3 git; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed. Please install $cmd and try again.${NC}"
        exit 1
    fi
done

# Define installation directory
INSTALL_DIR="$HOME/.metal-deploy"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/OpsGuild/MetalDeploy.git"

# Create installation directory
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${BLUE}Found existing installation at $INSTALL_DIR. Updating...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo -e "${BLUE}Cloning MetalDeploy to $INSTALL_DIR...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Set up virtual environment
echo -e "${BLUE}Setting up virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install --upgrade pip
pip install fabric invoke pyyaml

# Create the wrapper script
echo -e "${BLUE}Creating executable wrapper...${NC}"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/metaldeploy" << EOF
#!/bin/bash
source "$INSTALL_DIR/venv/bin/activate"
python3 "$INSTALL_DIR/main.py" "\$@"
EOF

chmod +x "$BIN_DIR/metaldeploy"

echo -e "${GREEN}✅ MetalDeploy installed successfully!${NC}"
echo -e ""
echo -e "You can now run it using: ${BLUE}metaldeploy --help${NC}"
echo -e ""

# Check if BIN_DIR is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${RED}Warning: $BIN_DIR is not in your PATH.${NC}"
    echo -e "Add this to your .bashrc or .zshrc:"
    echo -e "  ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
fi
