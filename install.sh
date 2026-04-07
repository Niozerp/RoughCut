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
SCRIPT_NAME="roughcut.lua"
SOURCE_LUA="$(cd "$(dirname "$0")" && pwd)/roughcut/lua/roughcut.lua"
BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)/roughcut"

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
if [[ ! -f "$SOURCE_LUA" ]]; then
    print_error "Cannot find roughcut.lua"
    print_error "Looked in: $SOURCE_LUA"
    echo ""
    echo "Make sure you're running this script from the extracted RoughCut folder."
    echo "This folder should contain: roughcut/, install.sh, install-guide.md"
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
    if [[ -f "$RESOLVE_SCRIPTS/roughcut.lua" ]]; then
        print_info "It looks like you already have roughcut.lua here."
        print_info "Using this location: $RESOLVE_SCRIPTS"
    fi
    
    # If they gave us the Scripts folder (not Utility), check and create Utility
    if [[ ! -d "$RESOLVE_SCRIPTS/Utility" ]]; then
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

# Copy Lua script
echo ""
print_info "Installing RoughCut Lua script..."

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

if cp "$SOURCE_LUA" "$RESOLVE_SCRIPTS/"; then
    print_ok "roughcut.lua copied to Scripts/Utility"
else
    print_error "Failed to copy roughcut.lua"
    echo ""
    echo "Possible causes:"
    echo "  - DaVinci Resolve is running (close it and try again)"
    echo "  - Permission denied (try: sudo ./install.sh)"
    echo "  - Path is incorrect"
    echo ""
    exit 1
fi

# Check Python
echo ""
print_info "Checking Python installation..."

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
    print_info "Checking Poetry package manager..."
    
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

# Success!
echo ""
echo "============================================"
echo "     RoughCut Installation Complete!"
echo "============================================"
echo ""
print_ok "roughcut.lua installed to Resolve Scripts"

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
echo "- For help: See install-guide.md in this folder"
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
