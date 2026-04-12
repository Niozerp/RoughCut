# RoughCut Installation Guide

> **Prerequisites**: DaVinci Resolve 18.5+ (Studio or Free), Python 3.10+, Node.js 20+, Windows/macOS/Linux

## Quick Start (2 Minutes) — One-Click Install ⭐

### Step 1: Download RoughCut

1. Download the latest `RoughCut.zip` from the [releases page](releases)
2. **Extract the ZIP file** to a folder (e.g., `Downloads/RoughCut/`)
3. You should see:
   - `install.bat` — **Double-click this on Windows** ⭐
   - `install.sh` — **Run this on macOS/Linux** ⭐
   - `roughcut/` — The deployable package (`RoughCut.lua`, `lua/`, `src/`, `scripts/`, `templates/`)

> 💡 **Tip**: The installer handles everything automatically. Manual steps are only needed if the auto-installer fails.

### Step 2: Run the Installer

**Windows:**
```
Double-click install.bat
```
The installer will automatically:
- Find your DaVinci Resolve installation
- Copy the script to the right folder
- Install Python dependencies
- Build the Electron app
- Install SpacetimeDB
- Verify the Rust toolchain and `wasm32-unknown-unknown` target needed for the bundled database module

**macOS/Linux:**
```bash
# Open Terminal in the RoughCut folder
cd ~/Downloads/RoughCut  # or wherever you extracted it

# Make it executable (first time only)
chmod +x install.sh

# Run the installer
./install.sh
```

### Step 3: Launch RoughCut

1. **Restart DaVinci Resolve** (required after first install)
2. Navigate to: **Workspace > Scripts > Utility > RoughCut**
3. On first launch, RoughCut runs a blocking preflight bootstrap before any GUI appears.
4. Once bootstrap finishes, the RoughCut main window should appear.

---

## Manual Installation (If One-Click Fails)

If the automatic installer can't find Resolve or you prefer manual control:

### Copy Lua Script Manually

**Windows:**
```
1. Copy roughcut/RoughCut.lua
2. Navigate to: %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
   (Paste into File Explorer address bar)
3. Paste the file
4. Copy the entire roughcut/ folder into the same Utility folder so Resolve can load roughcut/lua/roughcut_main.lua
```

**macOS:**
```bash
# Copy roughcut/RoughCut.lua to:
~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility/

cp roughcut/RoughCut.lua ~/Library/Application\ Support/Blackmagic\ Design/DaVinci\ Resolve/Support/Fusion/Scripts/Utility/

# Copy the roughcut/ folder next to it:
cp -r roughcut ~/Library/Application\ Support/Blackmagic\ Design/DaVinci\ Resolve/Support/Fusion/Scripts/Utility/
```

**Linux:**
```bash
# Copy roughcut/RoughCut.lua to:
~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/
# or
/opt/resolve/Fusion/Scripts/Utility/ (system-wide)

cp roughcut/RoughCut.lua ~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/

# Copy the roughcut/ folder next to it as well:
cp -r roughcut ~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/
```

### Install Python Backend

**Option A: Automatic (Recommended)**

The Lua script will auto-install dependencies on first run. Just:
1. Open DaVinci Resolve
2. Go to **Workspace > Scripts > Utility > RoughCut**
3. Click **Yes** when prompted to install Python dependencies

**Option B: Manual with Poetry**

If you prefer manual control:

```bash
# Navigate to the backend folder
cd roughcut

# Install Poetry if you don't have it
pip install poetry

# Install dependencies
poetry install
```

### Install Standalone Runtime Dependencies

The standalone app also needs:

- **Node.js 20+** for the Electron shell and frontend build
- **SpacetimeDB CLI** for the embedded local database runtime
- **Rust + rustup + `wasm32-unknown-unknown`** because RoughCut ships a Rust SpacetimeDB module that is compiled to WebAssembly on first publish

After bootstrap succeeds, RoughCut launches Electron from the direct packaged binary inside `node_modules/electron/dist`, so Node.js is only needed when bootstrap must install or rebuild the app.

If the one-click installer did not complete these steps, install them manually:

```bash
# Install the Rust toolchain and wasm target
rustup target add wasm32-unknown-unknown
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

### "install.bat won't run" or "Windows protected your PC"

**Windows SmartScreen may block the installer** (common with downloaded scripts):
1. Right-click on `install.bat`
2. Select **Properties**
3. Check **Unblock** at the bottom of the General tab
4. Click **OK**
5. Try running again

Or click **"More info"** then **"Run anyway"** when the SmartScreen warning appears.

### "install.sh: Permission denied"

**Make it executable first:**
```bash
chmod +x install.sh
./install.sh
```

### "Could not find DaVinci Resolve" or path entry issues

**The installer couldn't auto-detect Resolve.** This can happen if:
- Resolve is installed but the Scripts folder doesn't exist yet (first-time Resolve user)
- Resolve is in a non-standard or portable location
- Resolve is not installed at all

**The installer will now:**
1. Ask you interactive questions to understand your situation
2. Offer to create the missing Scripts/Utility folders automatically
3. Open File Explorer/Finder to help you locate the right folder
4. Guide you step-by-step through finding the correct path

**IMPORTANT - How to enter the path correctly:**

When the installer asks for the path, enter it like this:
```
C:\Users\YourName\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility
```

**NOT like this:**
```
"C:\Users\YourName\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\"  <- Wrong! (quotes and trailing backslash)
```

**Key points:**
- ✅ **NO quotes** at the beginning or end
- ✅ **NO trailing backslash** (\) at the end
- ✅ Just the plain folder path

**What happens in the new installer:**
- If Resolve isn't installed → Offers to open download page
- If Scripts folder exists but Utility doesn't → Creates Utility folder for you
- If custom/portable install → Guides you to enter the correct path
- Step-by-step walkthrough using Resolve's menu (Workspace > Scripts > Edit...)

### "DaVinci Resolve appears to be running!"

**The installer detected Resolve is currently running.** This can cause file copy to fail because Resolve may lock the Scripts folder.

**Solution:**
1. Close DaVinci Resolve completely
2. Re-run the installer
3. The installer will warn you again but let you continue if you choose

### "Script not appearing in menu"

**Check the path**: The file must be in the `Utility` subfolder, not directly in `Scripts`.

**Restart Resolve**: Script scanning only happens at startup.

### "Python backend not found"

Verify the backend folder is accessible:
- Windows: Check `roughcut/` folder is present where you ran the installer
- The installer should set this up automatically
- The Lua script will also try to auto-install on first run

### "wasm32-unknown-unknown target is not installed"

RoughCut starts a local SpacetimeDB instance and publishes a bundled Rust module into it. That publish step needs the Rust WebAssembly target.

On current builds, RoughCut checks and installs this target during the blocking prelaunch bootstrap before the GUI opens. If bootstrap still stops here, the console output should include the exact failing install step.

Try this first:

1. Re-run `install.bat` on Windows or `./install.sh` on macOS/Linux.
2. If the error persists, install Rust manually from [rustup.rs](https://rustup.rs/).
3. Run `rustup target add wasm32-unknown-unknown`.

If `cargo` or `rustup` still are not found after installation, restart your terminal so the Rust bin directory is on `PATH`.

### "Permission denied during install"

**Windows**: 
- Right-click `install.bat` → **"Run as administrator"** (one time only)
- Or manually copy the files as shown in "Manual Installation"

**macOS/Linux**: 
```bash
# Fix folder permissions
chmod +w ~/Library/Application\ Support/Blackmagic\ Design/DaVinci\ Resolve/Support/Fusion/Scripts/Utility/
# Then re-run the installer
```

### "Poetry installation failed"

**No problem!** The RoughCut Lua script will automatically:
1. Detect Poetry is missing
2. Offer to install it when you first run RoughCut
3. Just click **"Yes"** in the dialog that appears

Or install manually:
```bash
# Windows (PowerShell as Admin):
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# macOS/Linux:
curl -sSL https://install.python-poetry.org | python3 -
```

### "Failed to copy RoughCut.lua" with error codes

**The new installer shows debug output to help diagnose copy failures.**

Common error codes and solutions:

**Error code: 0**
- ✅ **Success!** File copied successfully.
- The installer will continue normally.

**Error code: 1**
- Usually means "success with warnings" in some Windows versions
- The installer will verify the file actually exists at the destination
- If the file is there, installation continues successfully

**Error code: 5**
- Permission denied
- Run install.bat as Administrator (right-click → Run as administrator)
- Check that DaVinci Resolve is closed

**Error code: 2 or 3**
- File not found or path not found
- Check that the source file exists in `roughcut\RoughCut.lua`
- Verify the target path is correct

**Source file NOT found**
- The installer can't find `roughcut\RoughCut.lua`
- Make sure you extracted the entire ZIP file
- Run install.bat from inside the RoughCut folder (not from elsewhere)

**Target folder NOT found**
- The path you entered doesn't exist
- Double-check the spelling and folder names
- Try navigating to the folder in File Explorer first to verify

**Solution steps:**
1. Close DaVinci Resolve completely
2. Verify the source files exist:
   - `roughcut\RoughCut.lua`
   - `roughcut\lua\roughcut_main.lua`
3. Run as Administrator if permission issues persist
4. Check the debug output - it shows exactly what path was used

### "Notion connection fails"

- Verify your integration has access to the specific page
- Check that the page URL is the full URL (not just the page ID)
- Ensure the integration is added as a collaborator to the page

---

## Uninstallation

To remove RoughCut:

1. **Delete from Resolve**:
   - Delete `RoughCut.lua` from the Scripts/Utility folder
   - Delete the deployed `roughcut/` folder from the Scripts/Utility folder
   - (Path shown during installation, or see "Manual Installation" section above)

2. **Delete backend**:
   - Delete the `roughcut/` folder where you extracted it

3. **Clean up Python environment** (optional):
   ```bash
   # Only if you want to remove all traces
   poetry env remove --all  # in the roughcut folder
   ```

4. **Restart DaVinci Resolve**

5. **(Optional)** Remove Notion integration from your Notion account

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
| Node.js | 20.0+ | Latest LTS |
| Rust toolchain | rustup + stable | rustup + stable |
| RAM | 16 GB | 32 GB |
| Storage | 500 MB | 2 GB (for media cache) |
| Internet | Required for AI features | Stable connection |

---

*Last updated: 2026-04-05*
*Install scripts version: 2.2 (Fixed trailing backslash bug, improved error handling)*
