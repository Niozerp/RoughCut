#!/bin/bash
#
# RoughCut Installer for macOS/Linux
# One-click installation script
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_ROOT="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="RoughCut.lua"
MODULE_DIR_NAME="roughcut"
SOURCE_MODULE_ROOT="$INSTALL_ROOT/roughcut"
SOURCE_LAUNCHER="$INSTALL_ROOT/roughcut/$SCRIPT_NAME"
BACKEND_DIR="$SOURCE_MODULE_ROOT"

# Print with colors
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if source files exist first
if [[ ! -f "$SOURCE_LAUNCHER" ]]; then
    print_error "Cannot find RoughCut launcher"
    print_error "Looked in: $SOURCE_LAUNCHER"
    echo ""
    echo "Make sure you're running this script from the extracted RoughCut folder."
    echo "This folder should contain: roughcut/, install.sh, and install.bat"
    echo ""
    exit 1
fi

if [[ ! -d "$SOURCE_MODULE_ROOT" ]]; then
    print_error "Cannot find RoughCut module tree"
    print_error "Looked in: $SOURCE_MODULE_ROOT"
    echo ""
    echo "Make sure you're running this script from the extracted RoughCut folder."
    echo "This folder should contain: roughcut/, install.sh, and install.bat"
    echo ""
    exit 1
fi

if [[ ! -f "$SOURCE_MODULE_ROOT/lua/roughcut_main.lua" ]] || [[ ! -f "$SOURCE_MODULE_ROOT/scripts/install.py" ]] || [[ ! -f "$SOURCE_MODULE_ROOT/pyproject.toml" ]]; then
    print_error "The RoughCut module tree is incomplete."
    print_error "Expected roughcut/lua/roughcut_main.lua, roughcut/scripts/install.py, and roughcut/pyproject.toml"
    echo ""
    exit 1
fi

# Header
clear
echo "============================================"
echo "     RoughCut Installer for macOS/Linux"
echo "============================================"
echo ""

# Determine OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=Linux;;
    Darwin*)    PLATFORM=Mac;;
    *)          PLATFORM="UNKNOWN"
esac

print_info "Detected platform: $PLATFORM"
echo ""

# Find DaVinci Resolve installation first
print_info "Looking for DaVinci Resolve installation..."

RESOLVE_FOUND=0
RESOLVE_APP=""

if [[ "$PLATFORM" == "Mac" ]]; then
    # Check for Resolve app on Mac
    if [[ -d "/Applications/DaVinci Resolve.app" ]]; then
        RESOLVE_APP="/Applications/DaVinci Resolve.app"
        RESOLVE_FOUND=1
        print_ok "Found DaVinci Resolve: $RESOLVE_APP"
    elif [[ -d "/Applications/DaVinci Resolve Studio.app" ]]; then
        RESOLVE_APP="/Applications/DaVinci Resolve Studio.app"
        RESOLVE_FOUND=1
        print_ok "Found DaVinci Resolve Studio: $RESOLVE_APP"
    fi
elif [[ "$PLATFORM" == "Linux" ]]; then
    # Check for Resolve on Linux
    if command -v resolve &> /dev/null; then
        RESOLVE_FOUND=1
        print_ok "Found DaVinci Resolve in PATH"
    elif [[ -x "/opt/resolve/bin/resolve" ]]; then
        RESOLVE_FOUND=1
        print_ok "Found DaVinci Resolve: /opt/resolve/bin/resolve"
    elif [[ -x "/home/resolve/bin/resolve" ]]; then
        RESOLVE_FOUND=1
        print_ok "Found DaVinci Resolve: /home/resolve/bin/resolve"
    fi
fi

if [[ $RESOLVE_FOUND -eq 0 ]]; then
    print_warn "DaVinci Resolve executable not found!"
    echo ""
    echo "Possible reasons:"
    echo "  - Resolve is not installed"
    echo "  - Resolve is installed in a non-standard location"
    echo "  - This is a portable/folder-based installation"
    echo ""
    print_info "We'll try to find the Scripts folder anyway..."
    echo ""
fi

# Now look for Scripts folder
print_info "Searching for Resolve Scripts folder..."
echo ""

RESOLVE_SCRIPTS=""

# Platform-specific paths
if [[ "$PLATFORM" == "Mac" ]]; then
    # macOS paths
    CHECK_PATHS=(
        "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility"
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility"
    )
    CHECK_PARENT_PATHS=(
        "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts"
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts"
    )
    CHECK_SUPPORT_PATHS=(
        "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support"
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support"
    )
elif [[ "$PLATFORM" == "Linux" ]]; then
    # Linux paths
    CHECK_PATHS=(
        "$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility"
        "/opt/resolve/Fusion/Scripts/Utility"
        "/home/resolve/Fusion/Scripts/Utility"
        "$HOME/.config/DaVinciResolve/Fusion/Scripts/Utility"
    )
    CHECK_PARENT_PATHS=(
        "$HOME/.local/share/DaVinciResolve/Fusion/Scripts"
        "/opt/resolve/Fusion/Scripts"
        "/home/resolve/Fusion/Scripts"
        "$HOME/.config/DaVinciResolve/Fusion/Scripts"
    )
    CHECK_SUPPORT_PATHS=(
        "$HOME/.local/share/DaVinciResolve"
        "/opt/resolve"
        "/home/resolve"
    )
else
    print_error "Unsupported platform: $PLATFORM"
    exit 1
fi

# Try to find Utility folder directly
for path in "${CHECK_PATHS[@]}"; do
    if [[ -d "$path" ]]; then
        RESOLVE_SCRIPTS="$path"
        print_ok "Found Scripts folder: $path"
        break
    fi
done

# If Utility folder doesn't exist, check if Scripts folder exists
if [[ -z "$RESOLVE_SCRIPTS" ]]; then
    for path in "${CHECK_PARENT_PATHS[@]}"; do
        if [[ -d "$path" ]]; then
            print_info "Found Scripts folder, creating Utility subfolder..."
            mkdir -p "$path/Utility" 2>/dev/null
            if [[ -d "$path/Utility" ]]; then
                RESOLVE_SCRIPTS="$path/Utility"
                print_ok "Created Utility folder: $RESOLVE_SCRIPTS"
                break
            fi
        fi
    done
fi

# If Scripts folder doesn't exist, check if Support folder exists
if [[ -z "$RESOLVE_SCRIPTS" ]]; then
    for path in "${CHECK_SUPPORT_PATHS[@]}"; do
        if [[ -d "$path" ]]; then
            print_info "Found Resolve Support folder, creating Scripts/Utility..."
            mkdir -p "$path/Fusion/Scripts/Utility" 2>/dev/null
            if [[ -d "$path/Fusion/Scripts/Utility" ]]; then
                RESOLVE_SCRIPTS="$path/Fusion/Scripts/Utility"
                print_ok "Created Scripts/Utility folder: $RESOLVE_SCRIPTS"
                break
            fi
        fi
    done
fi

# Interactive mode - ask user
if [[ -z "$RESOLVE_SCRIPTS" ]]; then
    clear
    echo "============================================"
    echo "     Finding DaVinci Resolve"
    echo "============================================"
    echo ""
    print_error "Could not automatically find or create DaVinci Resolve Scripts folder."
    echo ""
    echo "Let's figure this out together."
    echo ""
    
    # First, ask if Resolve is installed
    echo "Is DaVinci Resolve installed on this computer?"
    echo ""
    echo "  1. Yes, it's installed (standard location)"
    echo "  2. Yes, but it's in a custom/portable location"
    echo "  3. No, Resolve is not installed yet"
    echo "  4. I'm not sure / Cancel installation"
    echo ""
    
    read -rp "Select option (1-4): " response
    
    case $response in
        1)
            echo ""
            print_info "Let's help you find the Scripts folder:"
            echo ""
            echo "Step 1: Open DaVinci Resolve"
            echo "Step 2: Go to: Workspace > Scripts > Edit..."
            echo "Step 3: Note the folder path that opens"
            echo ""
            echo "This is your Scripts folder. The file goes in the 'Utility' subfolder."
            echo ""
            
            if [[ "$PLATFORM" == "Mac" ]]; then
                echo "Common macOS locations:"
                echo "  ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility/"
                echo "  /Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility/"
            else
                echo "Common Linux locations:"
                echo "  ~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/"
                echo "  /opt/resolve/Fusion/Scripts/Utility/"
            fi
            echo ""
            
            # Try to open file manager
            if [[ "$PLATFORM" == "Mac" ]]; then
                if [[ -d "$HOME/Library/Application Support/Blackmagic Design" ]]; then
                    open "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve" 2>/dev/null || true
                fi
            elif [[ "$PLATFORM" == "Linux" ]]; then
                if command -v xdg-open &> /dev/null; then
                    xdg-open "$HOME/.local/share/" 2>/dev/null || true
                fi
            fi
            ;;
        2)
            echo ""
            print_info "You have DaVinci Resolve in a custom or portable location."
            echo ""
            echo "Please navigate to where Resolve is installed and find:"
            if [[ "$PLATFORM" == "Mac" ]]; then
                echo "  DaVinci Resolve.app/Contents/Resources/Support/Fusion/Scripts/Utility/"
            else
                echo "  resolve/Support/Fusion/Scripts/Utility/"
            fi
            echo ""
            echo "Or if the Utility folder doesn't exist yet:"
            echo "  .../Scripts/ (we'll create Utility for you)"
            echo ""
            ;;
        3)
            echo ""
            print_info "You need to install DaVinci Resolve first."
            echo ""
            echo "Download from: https://www.blackmagicdesign.com/products/davinciresolve/"
            echo ""
            echo "After installing Resolve, run this installer again."
            echo ""
            read -rp "Open download page now? [Y/n]: " open_page
            if [[ "$open_page" =~ ^[Yy]$ ]] || [[ -z "$open_page" ]]; then
                if [[ "$PLATFORM" == "Mac" ]]; then
                    open "https://www.blackmagicdesign.com/products/davinciresolve/"
                else
                    xdg-open "https://www.blackmagicdesign.com/products/davinciresolve/" 2>/dev/null || echo "Please visit: https://www.blackmagicdesign.com/products/davinciresolve/"
                fi
            fi
            exit 0
            ;;
        4|*)
            echo ""
            print_error "Installation cancelled by user."
            exit 1
            ;;
    esac
    
    echo ""
    read -rp "Paste the full path to the 'Utility' folder (or the parent 'Scripts' folder): " RESOLVE_SCRIPTS
    
    if [[ -z "$RESOLVE_SCRIPTS" ]]; then
        echo ""
        print_error "Installation cancelled by user."
        exit 1
    fi
    
    # Expand ~ to home directory
    RESOLVE_SCRIPTS="${RESOLVE_SCRIPTS/#\~/$HOME}"
    
    # Check if user gave us the Scripts folder or the Utility folder
    if [[ -f "$RESOLVE_SCRIPTS/$SCRIPT_NAME" ]]; then
        print_info "It looks like you already have $SCRIPT_NAME here."
        print_info "Using this location: $RESOLVE_SCRIPTS"
    fi
    
    # If they gave us the Scripts folder (not Utility), check and create Utility
    if [[ "$(basename "$RESOLVE_SCRIPTS")" != "Utility" && ! -d "$RESOLVE_SCRIPTS/Utility" ]]; then
        if [[ -d "$RESOLVE_SCRIPTS" ]]; then
            print_info "Creating Utility subfolder..."
            mkdir -p "$RESOLVE_SCRIPTS/Utility"
            if [[ -d "$RESOLVE_SCRIPTS/Utility" ]]; then
                RESOLVE_SCRIPTS="$RESOLVE_SCRIPTS/Utility"
                print_ok "Created Utility folder"
            fi
        fi
    fi
    
    # Verify path exists
    if [[ ! -d "$RESOLVE_SCRIPTS" ]]; then
        print_error "The specified path does not exist: $RESOLVE_SCRIPTS"
        exit 1
    fi
fi

echo ""
print_ok "Resolve Scripts folder: $RESOLVE_SCRIPTS"
echo ""

# Copy launcher and module tree
echo ""
print_info "[2/5] Installing RoughCut launcher and module tree..."

# Check if Resolve is running (it might lock the file)
RESOLVE_RUNNING=0
if [[ "$PLATFORM" == "Mac" ]]; then
    if pgrep -x "DaVinci Resolve" > /dev/null; then
        RESOLVE_RUNNING=1
    fi
elif [[ "$PLATFORM" == "Linux" ]]; then
    if pgrep -x "resolve" > /dev/null; then
        RESOLVE_RUNNING=1
    fi
fi

if [[ $RESOLVE_RUNNING -eq 1 ]]; then
    print_warn "DaVinci Resolve appears to be running!"
    print_warn "Please close Resolve before continuing."
    echo ""
    read -rp "Continue anyway (might fail)? [y/N]: " continue_anyway
    if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
        echo ""
        print_info "Please close DaVinci Resolve and run this installer again."
        exit 0
    fi
    echo ""
fi

TARGET_LAUNCHER="$RESOLVE_SCRIPTS/$SCRIPT_NAME"
TARGET_MODULE_ROOT="$RESOLVE_SCRIPTS/$MODULE_DIR_NAME"
INSTALL_TIMESTAMP="$(date +%s)"

if [[ -e "$TARGET_MODULE_ROOT" ]]; then
    MODULE_BACKUP="$RESOLVE_SCRIPTS/${MODULE_DIR_NAME}_backup_$INSTALL_TIMESTAMP"
    if mv "$TARGET_MODULE_ROOT" "$MODULE_BACKUP"; then
        print_info "Backed up existing module tree to $MODULE_BACKUP"
    else
        print_error "Failed to back up existing module tree at $TARGET_MODULE_ROOT"
        exit 1
    fi
fi

if [[ -f "$TARGET_LAUNCHER" ]]; then
    LAUNCHER_BACKUP="$RESOLVE_SCRIPTS/${SCRIPT_NAME%.lua}_backup_$INSTALL_TIMESTAMP.lua"
    if cp "$TARGET_LAUNCHER" "$LAUNCHER_BACKUP"; then
        print_info "Backed up existing launcher to $LAUNCHER_BACKUP"
    else
        print_warn "Could not back up existing launcher. It will be overwritten."
    fi
fi

if cp "$SOURCE_LAUNCHER" "$TARGET_LAUNCHER"; then
    print_ok "$SCRIPT_NAME copied to Scripts/Utility"
else
    print_error "Failed to copy $SCRIPT_NAME"
    echo ""
    echo "Possible causes:"
    echo "  - DaVinci Resolve is running (close it and try again)"
    echo "  - Permission denied (try: sudo ./install.sh)"
    echo "  - Path is incorrect"
    echo ""
    exit 1
fi

if cp -R "$SOURCE_MODULE_ROOT" "$RESOLVE_SCRIPTS/"; then
    print_ok "roughcut/ package copied to Scripts/Utility/$MODULE_DIR_NAME"
else
    print_error "Failed to copy RoughCut module tree"
    echo ""
    echo "Possible causes:"
    echo "  - DaVinci Resolve is running (close it and try again)"
    echo "  - Permission denied (try: sudo ./install.sh)"
    echo "  - Path is incorrect"
    echo ""
    exit 1
fi

# Copy roughcut-electron folder if it exists
ELECTRON_SOURCE="$INSTALL_ROOT/roughcut-electron"
ELECTRON_TARGET="$RESOLVE_SCRIPTS/roughcut-electron"

if [[ -f "$ELECTRON_SOURCE/package.json" ]]; then
    print_info "Copying roughcut-electron folder..."
    
    if [[ -d "$ELECTRON_TARGET" ]]; then
        print_info "Existing roughcut-electron folder found, updating..."
        rm -rf "$ELECTRON_TARGET"
    fi
    
    if cp -R "$ELECTRON_SOURCE" "$RESOLVE_SCRIPTS/"; then
        print_ok "roughcut-electron/ copied to Scripts/Utility/"
    else
        print_warn "Failed to copy roughcut-electron folder"
        print_info "The Electron UI will not be available"
        print_info "You can still use the native Resolve UI"
    fi
else
    print_info "roughcut-electron folder not found, skipping"
fi

print_info "Verifying installed files..."

REQUIRED_INSTALL_PATHS=(
    "$TARGET_LAUNCHER"
    "$TARGET_MODULE_ROOT/lua/roughcut_main.lua"
    "$TARGET_MODULE_ROOT/lua/ui/main_window.lua"
    "$TARGET_MODULE_ROOT/lua/ui/electron_bridge.lua"
    "$TARGET_MODULE_ROOT/lua/ui/electron_main_window.lua"
    "$TARGET_MODULE_ROOT/scripts/install.py"
    "$TARGET_MODULE_ROOT/pyproject.toml"
)

for required_path in "${REQUIRED_INSTALL_PATHS[@]}"; do
    if [[ -e "$required_path" ]]; then
        print_ok "Verified: $required_path"
    else
        print_error "Missing required installed file: $required_path"
        exit 1
    fi
done

# Check Python
echo ""
print_info "[3/5] Checking Python installation..."

PYTHON_CMD=""

# Try to find Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

if [[ -z "$PYTHON_CMD" ]]; then
    print_warn "Python not found!"
    echo ""
    echo "RoughCut requires Python 3.10+ for AI features."
    echo ""
    
    read -rp "Continue without Python? (Lua features only) [Y/n]: " response
    if [[ ! "$response" =~ ^[Yy]$ ]] && [[ -n "$response" ]]; then
        if [[ "$PLATFORM" == "Mac" ]]; then
            echo ""
            echo "Install Python via Homebrew:"
            echo "  brew install python@3.11"
            echo ""
            echo "Or download from: https://www.python.org/downloads/"
        else
            echo ""
            echo "Install Python via your package manager:"
            echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
            echo "  Fedora: sudo dnf install python3 python3-pip"
            echo "  Arch: sudo pacman -S python python-pip"
        fi
        exit 0
    fi
    
    echo ""
    print_info "Continuing without Python. AI features will not be available."
    print_info "You can install Python later and the backend will auto-install."
    SKIP_PYTHON=1
else
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    print_ok "Found Python $PYTHON_VERSION"
fi

# Check Poetry and install backend (if we have Python)
if [[ -z "$SKIP_PYTHON" ]]; then
    echo ""
    print_info "[4/5] Installing Python backend..."
    
    if ! command -v poetry &> /dev/null; then
        print_info "Poetry not found. Installing automatically..."
        echo ""
        
        # Install Poetry
        if curl -sSL https://install.python-poetry.org | $PYTHON_CMD -; then
            print_ok "Poetry installed successfully"
            
            # Add to PATH for this session
            export PATH="$HOME/.local/bin:$PATH"
        else
            print_warn "Automatic Poetry installation failed."
            echo ""
            echo "The RoughCut Lua script will attempt to install dependencies"
            echo "on first run. Just click \"Yes\" when prompted."
            echo ""
            SKIP_POETRY=1
        fi
    else
        POETRY_VERSION=$(poetry --version | awk '{print $3}')
        print_ok "Poetry $POETRY_VERSION found"
    fi
    
    # Install Python dependencies
    if [[ -z "$SKIP_POETRY" ]]; then
        echo ""
        print_info "Installing RoughCut Python backend..."
        echo "(This may take a few minutes on first run)"
        echo ""
        
        cd "$BACKEND_DIR"
        
        if poetry install --no-interaction; then
            print_ok "Python backend installed successfully"
        else
            print_warn "Backend installation had issues."
            print_info "The Lua script will retry on first run."
        fi
    fi
fi

# Install Electron UI
echo ""
print_info "[5/5] Checking Electron UI dependencies..."

# Check if Node.js/npm is available
NPM_CMD=""
if command -v npm &> /dev/null; then
    NPM_CMD="npm"
elif command -v npm.cmd &> /dev/null; then
    NPM_CMD="npm.cmd"
fi

if [[ -z "$NPM_CMD" ]]; then
    print_warn "Node.js/npm not found!"
    echo ""
    echo "The modern Electron UI requires Node.js."
    echo ""
    read -rp "Continue with native Resolve UI (no Electron)? [Y/n]: " response
    if [[ ! "$response" =~ ^[Yy]$ ]] && [[ -n "$response" ]]; then
        if [[ "$PLATFORM" == "Mac" ]]; then
            echo ""
            echo "Install Node.js via Homebrew:"
            echo "  brew install node"
            echo ""
            echo "Or download from: https://nodejs.org/"
        else
            echo ""
            echo "Install Node.js via your package manager:"
            echo "  Ubuntu/Debian: sudo apt install nodejs npm"
            echo "  Fedora: sudo dnf install nodejs npm"
            echo "  Arch: sudo pacman -S nodejs npm"
        fi
        exit 0
    fi
    
    echo ""
    print_info "Continuing without Electron UI."
    print_info "The native Resolve UI will be used instead."
    SKIP_ELECTRON=1
else
    NPM_VERSION=$($NPM_CMD --version 2>&1)
    print_ok "npm $NPM_VERSION found"
fi

# Install Electron dependencies if npm is available
if [[ -z "$SKIP_ELECTRON" ]]; then
    # Check if roughcut-electron exists
    if [[ ! -f "$INSTALL_ROOT/roughcut-electron/package.json" ]]; then
        print_info "roughcut-electron folder not found, skipping Electron UI install"
    else
        # Check if dependencies already installed
        if [[ -d "$INSTALL_ROOT/roughcut-electron/node_modules" ]]; then
            print_ok "Electron dependencies already installed"
        else
            print_info "Installing Electron UI dependencies..."
            print_info "This may take 2-3 minutes..."
            echo ""
            
            cd "$INSTALL_ROOT/roughcut-electron"
            
            if $NPM_CMD install; then
                print_ok "Electron UI dependencies installed successfully"
            else
                print_warn "Electron dependency installation had issues."
                print_info "The script will try to install on first run from Resolve."
            fi
        fi
    fi
fi

# Success!
echo ""
echo "============================================"
echo "     RoughCut Installation Complete!"
echo "============================================"
echo ""
print_ok "$SCRIPT_NAME installed to Resolve Scripts"
print_ok "roughcut/ module tree installed alongside the launcher"

if [[ -f "$RESOLVE_SCRIPTS/roughcut-electron/package.json" ]]; then
    print_ok "Electron UI installed"
elif [[ -z "$SKIP_ELECTRON" ]]; then
    print_info "Electron UI not installed (requires Node.js)"
fi

if [[ -z "$SKIP_PYTHON" ]]; then
    print_ok "Python backend ready"
else
    print_ok "Python backend will auto-install on first run"
fi

echo ""
echo "NEXT STEPS:"
echo "-----------"
echo "1. RESTART DaVinci Resolve (if it's open)"
echo "2. Go to: Workspace > Scripts > Utility > RoughCut"
echo "3. The RoughCut window should appear!"
echo ""
echo "TROUBLESHOOTING:"
echo "----------------"
echo "- If script doesn't appear: Restart Resolve completely"
echo "- If backend fails: It will auto-install when you run RoughCut"
echo "- For help: See roughcut/README.md or roughcut/INSTALL.txt"
echo ""
echo "Installation location: $RESOLVE_SCRIPTS"
echo ""

# Try to launch Resolve
if [[ "$PLATFORM" == "Mac" ]]; then
    if [[ -d "/Applications/DaVinci Resolve.app" ]] || [[ -d "/Applications/DaVinci Resolve Studio.app" ]]; then
        read -rp "Launch DaVinci Resolve now? [Y/n]: " response
        if [[ "$response" =~ ^[Yy]$ ]] || [[ -z "$response" ]]; then
            if [[ -d "/Applications/DaVinci Resolve.app" ]]; then
                open -a "DaVinci Resolve"
            else
                open -a "DaVinci Resolve Studio"
            fi
        fi
    fi
elif [[ "$PLATFORM" == "Linux" ]]; then
    if command -v resolve &> /dev/null; then
        read -rp "Launch DaVinci Resolve now? [Y/n]: " response
        if [[ "$response" =~ ^[Yy]$ ]] || [[ -z "$response" ]]; then
            resolve &
        fi
    elif [[ -x "/opt/resolve/bin/resolve" ]]; then
        read -rp "Launch DaVinci Resolve now? [Y/n]: " response
        if [[ "$response" =~ ^[Yy]$ ]] || [[ -z "$response" ]]; then
            /opt/resolve/bin/resolve &
        fi
    fi
fi

echo ""
echo "Installation complete! Enjoy using RoughCut! 🎬"
echo ""

read -rp "Press Enter to exit..."
