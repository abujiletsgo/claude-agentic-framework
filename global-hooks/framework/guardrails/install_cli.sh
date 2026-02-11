#!/bin/bash
# Installation script for claude-hooks CLI tool

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Installing claude-hooks CLI tool..."
echo

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLI_SCRIPT="$SCRIPT_DIR/claude_hooks_cli.py"

# Check if CLI script exists
if [ ! -f "$CLI_SCRIPT" ]; then
    echo -e "${RED}Error: CLI script not found at $CLI_SCRIPT${NC}"
    exit 1
fi

# Make CLI script executable
echo -e "${YELLOW}Making CLI script executable...${NC}"
chmod +x "$CLI_SCRIPT"

# Create ~/.local/bin if it doesn't exist
if [ ! -d "$HOME/.local/bin" ]; then
    echo -e "${YELLOW}Creating ~/.local/bin directory...${NC}"
    mkdir -p "$HOME/.local/bin"
fi

# Create symlink
echo -e "${YELLOW}Creating symlink to ~/.local/bin/claude-hooks...${NC}"
ln -sf "$CLI_SCRIPT" "$HOME/.local/bin/claude-hooks"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo
    echo -e "${YELLOW}Warning: ~/.local/bin is not in your PATH${NC}"
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
    echo "Then reload your shell:"
    echo "    source ~/.bashrc  # or source ~/.zshrc"
    echo
fi

# Verify installation
echo
echo -e "${YELLOW}Verifying installation...${NC}"
if [ -x "$HOME/.local/bin/claude-hooks" ]; then
    echo -e "${GREEN}✓ Symlink created successfully${NC}"

    # Test the CLI
    if "$HOME/.local/bin/claude-hooks" --help > /dev/null 2>&1; then
        echo -e "${GREEN}✓ CLI is working correctly${NC}"
        echo
        echo -e "${GREEN}Installation complete!${NC}"
        echo
        echo "Usage:"
        echo "  claude-hooks health         # Show hook health status"
        echo "  claude-hooks list           # List all tracked hooks"
        echo "  claude-hooks --help         # Show all commands"
        echo
        echo "For detailed usage, see CLI_USAGE.md"
    else
        echo -e "${RED}✗ CLI test failed${NC}"
        echo "Try running: $HOME/.local/bin/claude-hooks --help"
        exit 1
    fi
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi
