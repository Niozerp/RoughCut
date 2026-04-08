# RoughCut

An AI-powered DaVinci Resolve plugin that transforms dormant media asset libraries into an intelligent creative partner.

## Installation

### Method 1: Simple Installation (Recommended)

**Important**: Put only `RoughCut.lua` at the Utility scripts root. Keep the rest of RoughCut inside a sibling `roughcut/` folder.

1. **Copy `RoughCut.lua`** into DaVinci Resolve's Utility Scripts folder:
   - **macOS**: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility/`
   - **Windows**: `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\`

2. **Copy the entire `roughcut/` folder** to the same location so it sits next to `RoughCut.lua`.
   - Final structure should look like:
      ```
      Utility/
      ├── RoughCut.lua          ← The launcher (ONLY menu item)
      ├── roughcut/             ← RoughCut package root
      │   ├── lua/
      │   │   ├── roughcut_main.lua
      │   │   ├── ui/
      │   │   └── utils/
      │   ├── scripts/
      │   ├── src/
      │   ├── templates/
      │   ├── pyproject.toml
      │   └── poetry.lock
      └── (other utility scripts)
      ```

3. Restart Resolve or refresh the Scripts menu.

4. Access RoughCut from **Workspace > Scripts > Utility > RoughCut**

### What Gets Installed Where

| Location | What Goes There | What Resolve Shows |
|----------|-----------------|-------------------|
| Scripts Folder | `RoughCut.lua` + `roughcut/` folder | Single "RoughCut" menu item |
| `roughcut/lua/` | All Lua modules | Nothing (not scanned) |
| `roughcut/src/` | Python backend | Nothing (not scanned) |

**Common Mistake**: If you see multiple menu items like "main_window", "navigation", "media_browser" - you've copied the Lua files incorrectly. Only `RoughCut.lua` should be in the Scripts folder root.

### Method 2: Developer Installation

From the `roughcut/` directory in this repo, use the deploy helper:

```bash
python scripts/deploy.py --project-path . --force
```

The deploy helper installs:
- `RoughCut.lua` into Resolve's `Support/Fusion/Scripts/Utility/` folder
- the full `roughcut/` package tree alongside it so the launcher, Lua modules, backend installer, and Python package stay in sync

## Verification

After installation:
1. Open DaVinci Resolve
2. Go to **Workspace > Scripts** menu
3. Open **Utility** and select **RoughCut**
4. On first launch, RoughCut will:
   - Check for Python backend
   - Install dependencies if needed (shows progress dialog)
   - Transition directly into the main RoughCut window after installation finishes

## Getting Started

### First Launch

When you first run RoughCut:
1. **Launcher Handoff**: `RoughCut.lua` finds `roughcut/lua/roughcut_main.lua`, connects to Resolve, and hands control to the packaged app
2. **Backend Check**: RoughCut checks local config state and whether the `roughcut` Python package is already importable globally
3. **Install Branch**:
   - If the backend is already available, RoughCut skips the install dialog and goes straight to the home screen
   - If the backend is missing, RoughCut shows the install dialog, installs the backend, and then opens the same home screen
4. **Home Screen**: The first reachable UI is the main RoughCut window with three options:
   - `Manage Media`
   - `Manage Formats`
   - `Create Rough Cut`

### Using RoughCut

The current Resolve-facing UI is stabilized around dispatcher-safe route shells:
1. **Manage Media**
   - Opens a stable window on the shared dispatcher runtime
   - Folder selection, save, and re-index actions now report explicit gated status instead of failing silently

2. **Manage Formats**
   - Opens a stable template-browser shell on the shared dispatcher runtime
   - Template browsing works inside the shell; deeper backend preview/application work is still being migrated

3. **Create Rough Cut**
   - Opens a stable workflow shell on the shared dispatcher runtime
   - Media-browser and generation actions report explicit gated status while the remaining legacy windows are being migrated

### Troubleshooting

**Nothing happens when I click RoughCut in the menu**
- Check Resolve console: Workspace > Console
- Verify `roughcut/` folder is next to `RoughCut.lua`
- Check INSTALL.txt for correct folder structure
- Expected startup milestones in the console:
  - `RoughCut: Startup - launcher handoff received`
  - `RoughCut: Startup - Fusion UI manager acquired`
  - `RoughCut: Startup - backend ready, skipping install UI`
    or `RoughCut: Startup - backend missing, starting install flow`
  - `RoughCut: Startup - home screen bound`
  - `RoughCut: Startup - entering main window RunLoop`

**The window opens but seems stuck**
- The expected first screen is the home hub with `Manage Media`, `Manage Formats`, and `Create Rough Cut`
- If you do not see those buttons, the deployed Lua files are out of sync with the repo
- Re-run the deploy helper and relaunch RoughCut

**The route opens, but actions only update status text**
- That is expected in the dispatcher-stabilization build
- The startup path and first-hop windows are now dispatcher-safe
- Any deeper action that still depends on a legacy non-dispatcher window is intentionally gated instead of failing silently

**I see too many menu items (main_window, navigation, etc.)**
- You've copied individual .lua files to the Scripts folder
- Delete all RoughCut-related files from Scripts folder
- Re-install following the instructions above (only copy RoughCut.lua and the roughcut/ folder)

**Installation seems stuck**
- First-time Python backend installation can take 3-7 minutes
- Check the progress dialog for status
- You can cancel and retry if needed
- If the backend is already installed globally, RoughCut should skip the install dialog entirely

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
│   ├── roughcut_main.lua     # Main Lua module
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
