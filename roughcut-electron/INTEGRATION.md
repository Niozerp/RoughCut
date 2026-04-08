# RoughCut Electron UI Integration

This document explains how the Electron UI integrates with DaVinci Resolve.

## Architecture

```
DaVinci Resolve
    ↓ (Scripts menu)
RoughCut.lua (launcher)
    ↓ (finds & loads modules)
roughcut/lua/roughcut_main.lua
    ↓ (detects UI mode)
ui.electron_bridge.lua
    ↓ (spawns process)
Electron App
    ↓ (communicates via IPC/Python)
Python Backend
    ↓ (Resolve API)
DaVinci Resolve (timeline, media, etc.)
```

## How It Works

### 1. Launch Flow

When the user runs RoughCut from Resolve's Scripts menu:

1. `RoughCut.lua` finds and loads `roughcut_main.lua`
2. `roughcut_main.lua` detects whether Electron is available
3. If available, it uses `electron_bridge.lua` to spawn the Electron process
4. Electron launches as a separate GUI application
5. Electron communicates with the Python backend for Resolve operations

### 2. UI Mode Detection

The system automatically detects which UI to use:

- **Electron Mode**: Used when `roughcut-electron/package.json` exists
- **Native Mode**: Fallback to Resolve's built-in UIManager

### 3. Communication

Communication between components uses JSON-RPC:

- **Lua → Python**: stdout/stdin protocol (existing)
- **Electron ↔ Python**: HTTP/WebSocket (to be implemented)
- **Lua → Electron**: Process spawn with file-based status (MVP)

## File Structure

```
roughcut/
├── lua/
│   ├── ui/
│   │   ├── electron_bridge.lua       # Launch/manages Electron
│   │   ├── electron_main_window.lua  # Electron window abstraction
│   │   └── main_window.lua           # Native Resolve UI (fallback)
│   └── roughcut_main.lua             # Entry point with UI detection
└── RoughCut.lua                      # Resolve launcher

roughcut-electron/
├── electron/
│   ├── main.ts                       # Electron main process
│   └── preload.ts                    # IPC bridge
├── src/
│   ├── App.tsx                       # Main React app
│   └── ...                           # Components & features
└── package.json
```

## Running the Electron UI

### Prerequisites

- Node.js 18+ and npm installed
- DaVinci Resolve running
- RoughCut Python backend installed

### From Resolve

1. Copy/link `roughcut/RoughCut.lua` to Resolve's Scripts folder
2. Ensure `roughcut/` folder is in the same directory or parent
3. Run `npm install` in `roughcut-electron/`
4. Launch from Resolve: **Workspace → Scripts → RoughCut**

### Development Mode

```bash
cd roughcut-electron
npm install
npm run dev
```

The Electron window will open. In development, it will connect to the Vite dev server for hot reloading.

### Building for Production

```bash
cd roughcut-electron
npm run build
```

This creates a standalone Electron app in `dist/`.

## Troubleshooting

### Electron doesn't launch

1. Check Resolve console for error messages
2. Verify `roughcut-electron/package.json` exists
3. Ensure npm is installed: `npm --version`
4. Check that `npm install` was run in `roughcut-electron/`

### Native UI fallback

If Electron fails to launch, the system automatically falls back to the native Resolve UI. Check the logs to see why Electron failed.

### Communication issues

The MVP uses file-based communication. Future versions will use proper IPC/WebSocket for real-time communication.

## Future Improvements

- [ ] WebSocket communication between Electron and Python
- [ ] File watching for real-time updates from Resolve
- [ ] Proper window management (focus, bring to front)
- [ ] Auto-installation of npm dependencies
- [ ] Packaging as standalone executable
