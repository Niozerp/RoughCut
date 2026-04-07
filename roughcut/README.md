# RoughCut

An AI-powered DaVinci Resolve plugin that transforms dormant media asset libraries into an intelligent creative partner.

## Installation

### Method 1: Simple Installation (Recommended)

**Important**: Only copy the launcher script to Resolve's Scripts folder. Do NOT copy the entire lua folder.

1. **Copy just ONE file** - `RoughCut.lua` - into DaVinci Resolve's Scripts folder:
   - **macOS**: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Workflow Integration Scripts/`
   - **Windows**: `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Scripts\`

2. **Copy the RoughCut modules folder** to the SAME location:
   - Copy the entire `roughcut/` folder (containing `lua/`, `src/`, etc.) so it sits next to `RoughCut.lua`
   - Final structure should look like:
      ```
      Workflow Integration Scripts/
      ├── RoughCut.lua          ← The launcher (ONLY menu item)
      ├── roughcut/             ← All the actual code
      │   ├── lua/
      │   │   ├── roughcut_main.lua  ← Main module (loaded by launcher)
      │   │   ├── ui/
      │   │   └── utils/
      │   └── src/
      └── (other scripts)
      ```

3. Restart Resolve or refresh the Scripts menu (Workspace > Scripts > Update)

4. Access RoughCut from **Workspace > Scripts > RoughCut**

### What Gets Installed Where

| Location | What Goes There | What Resolve Shows |
|----------|-----------------|-------------------|
| Scripts Folder | `RoughCut.lua` + `roughcut/` folder | Single "RoughCut" menu item |
| `roughcut/lua/` | All Lua modules | Nothing (not scanned) |
| `roughcut/src/` | Python backend | Nothing (not scanned) |

**Common Mistake**: If you see multiple menu items like "main_window", "navigation", "media_browser" - you've copied the Lua files incorrectly. Only `RoughCut.lua` should be in the Scripts folder root.

### Method 2: Developer Installation

```bash
# Clone the repository
git clone <repository-url>
cd roughcut

# Install dependencies
poetry install

# Copy launcher and modules to Resolve Scripts folder
# Windows:
copy RoughCut.lua "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Scripts\"
xcopy /E /I roughcut "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Scripts\roughcut\"

# macOS:
cp RoughCut.lua "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Workflow Integration Scripts/"
cp -r roughcut "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Workflow Integration Scripts/"
```

## Verification

After installation:
1. Open DaVinci Resolve
2. Go to **Workspace > Scripts** menu
3. You should see ONE menu item: **RoughCut**
4. Select **RoughCut**
5. On first launch, RoughCut will:
   - Check for Python backend
   - Install dependencies if needed (shows progress dialog)
   - Open the main RoughCut window

## Getting Started

### First Launch

When you first run RoughCut:
1. **Installation Check**: RoughCut checks if Python backend is installed
2. **Auto-Install**: If needed, it automatically installs Python dependencies (takes 2-5 minutes)
3. **Main Window**: Opens with 3 main options:
   - **Manage Media** - Set up your Music, SFX, and VFX folders
   - **Manage Formats** - Define rough cut templates
   - **Create Rough Cut** - Start the AI-powered workflow

### Using RoughCut

1. **Configure Media Folders** (one-time setup):
   - Click "Manage Media"
   - Add folders containing your Music, SFX, and VFX assets
   - RoughCut will index them automatically

2. **Create a Rough Cut**:
   - Click "Create Rough Cut"
   - Select source video from media pool
   - Choose a format template
   - Let AI suggest music, SFX, and cuts
   - Review and apply to timeline

### Troubleshooting

**Nothing happens when I click RoughCut in the menu**
- Check Resolve console: Workspace > Console
- Verify `roughcut/` folder is next to `RoughCut.lua`
- Check INSTALL.txt for correct folder structure

**I see too many menu items (main_window, navigation, etc.)**
- You've copied individual .lua files to the Scripts folder
- Delete all RoughCut-related files from Scripts folder
- Re-install following the instructions above (only copy RoughCut.lua and the roughcut/ folder)

**Installation seems stuck**
- First-time Python backend installation can take 3-7 minutes
- Check the progress dialog for status
- You can cancel and retry if needed

## Project Structure

```
roughcut/
├── RoughCut.lua                ← Launcher script (ONLY file that goes in Scripts folder root)
├── INSTALL.txt                 ← Installation instructions
├── pyproject.toml              # Poetry configuration
├── poetry.lock                 # Dependency lock file
├── README.md                   # This file
├── src/
│   └── roughcut/              # Python package
│       ├── __init__.py        # Package initialization
│       ├── __main__.py        # Python entry point
│       ├── backend/           # Business logic
│       ├── config/            # Configuration module
│       └── protocols/         # Lua ↔ Python communication
├── lua/
│   ├── roughcut.lua          # Main Lua module
│   ├── ui/                   # UI components
│   │   ├── main_window.lua
│   │   ├── navigation.lua
│   │   └── ...
│   ├── utils/                # Utilities
│   └── ...
├── templates/                # Format templates
│   └── formats/
└── tests/                    # Test suite
```

**Key Point**: Only `RoughCut.lua` goes in the Scripts folder root. Everything else stays inside the `roughcut/` folder.

## Usage

Currently (Story 1.1), RoughCut provides:
- ✅ Drag-and-drop installation via Lua script
- ✅ Scripts menu integration with DaVinci Resolve
- ✅ Installation verification dialog

Future stories will add:
- Media asset indexing and management
- AI-powered rough cut generation
- Format template system
- Timeline creation and media placement

## Requirements

- DaVinci Resolve 17+ (Studio or Free version)
- Python 3.10+ (for backend features)
- Poetry 2.0+ (for development)

## Development

```bash
# Setup environment
poetry install

# Run backend
poetry run python -m roughcut

# Testing
poetry run pytest
```

## License

[License to be determined]

## Support

For issues or questions, please refer to the project documentation or contact the development team.
