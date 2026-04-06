# RoughCut Installation Guide

> **Prerequisites**: DaVinci Resolve 18.5+ (Studio or Free), Python 3.10+, Windows/macOS/Linux

## Quick Start (2 Minutes)

### Step 1: Download RoughCut

1. Download the latest `RoughCut.zip` from the [releases page](releases)
2. Extract the ZIP file to a temporary location
3. You should see:
   - `roughcut.lua` — The Resolve script entry point
   - `roughcut_backend/` — Python backend folder
   - `install.bat` (Windows) / `install.sh` (macOS/Linux) — Optional helper scripts

---

### Step 2: Install the Lua Script

**Windows:**
```
1. Copy roughcut.lua
2. Navigate to: %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
   (Paste into File Explorer address bar)
3. Paste the file
```

**macOS:**
```bash
# Copy roughcut.lua to:
~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility/
```

**Linux:**
```bash
# Copy roughcut.lua to:
~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/
# or
/opt/resolve/Fusion/Scripts/Utility/ (system-wide)
```

---

### Step 3: Install Python Backend

**Option A: Automatic (Recommended)**

The Lua script will auto-install dependencies on first run. Just:
1. Open DaVinci Resolve
2. Go to **Workspace > Scripts > Utility > RoughCut**
3. Click **Yes** when prompted to install Python dependencies

**Option B: Manual with Poetry**

If you prefer manual control:

```bash
# Navigate to the backend folder
cd roughcut_backend

# Install Poetry if you don't have it
pip install poetry

# Install dependencies
poetry install

# The install script will set up the path in Resolve settings
```

---

### Step 4: Launch RoughCut

1. **Restart DaVinci Resolve** (required after first install)
2. Navigate to: **Workspace > Scripts > Utility > RoughCut**
3. The RoughCut main window should appear

---

## Post-Installation Setup

### Optional: Configure Media Folders

Before your first rough cut:

1. In RoughCut, click **Settings** (gear icon)
2. Under **Media Folders**, set your asset directories:
   - **Music**: Path to your music/soundtrack library
   - **SFX**: Path to sound effects folder
   - **VFX**: Path to video templates/overlays
3. Click **Save & Index** to scan your media

### Optional: Enable Notion Integration

For cloud backup of your media database:

1. Get a Notion Integration Token:
   - Go to [notion.so/my-integrations](https://notion.so/my-integrations)
   - Create new integration → copy the token
2. In RoughCut, click **Settings**
3. Paste your **Notion API Token**
4. Enter your **Notion Page URL** (where RoughCut will sync data)
5. Click **Validate Connection**

---

## Verification

Run through this checklist to confirm everything works:

- [ ] RoughCut appears in **Scripts > Utility** menu
- [ ] Main window opens without errors
- [ ] Settings panel loads
- [ ] (If configured) Notion connection validates successfully
- [ ] Media indexing starts and completes (test with a small folder first)

---

## Troubleshooting

### "Script not appearing in menu"

**Check the path**: The file must be in the `Utility` subfolder, not directly in `Scripts`.

**Restart Resolve**: Script scanning only happens at startup.

### "Python backend not found"

Verify the backend folder is accessible:
- Windows: Check `roughcut_backend/` is in the same folder as `roughcut.lua` or in your PATH
- Check Resolve's Python path in **Preferences > System > General > Python Script Executable**

### "Permission denied during install"

**Windows**: Run Resolve as Administrator once for the auto-install to complete.

**macOS/Linux**: Ensure the scripts folder has write permissions:
```bash
chmod +w ~/Library/Application\ Support/Blackmagic\ Design/DaVinci\ Resolve/Support/Fusion/Scripts/Utility/
```

### "Notion connection fails"

- Verify your integration has access to the specific page
- Check that the page URL is the full URL (not just the page ID)
- Ensure the integration is added as a collaborator to the page

---

## Uninstallation

To remove RoughCut:

1. Delete `roughcut.lua` from the Scripts/Utility folder
2. Delete the `roughcut_backend/` folder
3. (Optional) Remove Notion integration from your Notion account
4. Restart DaVinci Resolve

---

## Next Steps

Once installed:

1. **Read the [User Guide](user-guide.md)** — Learn the rough cut workflow
2. **Explore Format Templates** — See `templates/` folder for examples
3. **Try the Demo** — Use sample footage to test the AI rough cut generation

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| DaVinci Resolve | 18.5+ | 19.0+ |
| Python | 3.10 | 3.11+ |
| RAM | 16 GB | 32 GB |
| Storage | 500 MB | 2 GB (for media cache) |
| Internet | Required for AI features | Stable connection |

---

*Last updated: 2026-04-05*
