#!/bin/bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT/roughcut"
ELECTRON_DIR="$BACKEND_DIR/electron"
ROOT_LAUNCHER="$ROOT/launch_roughcut.sh"

print_step() {
  printf '\n[%s] %s\n' "$1" "$2"
}

print_info() {
  printf '[INFO] %s\n' "$1"
}

print_ok() {
  printf '[OK] %s\n' "$1"
}

print_warn() {
  printf '[WARN] %s\n' "$1"
}

prepend_runtime_path() {
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
}

if [[ ! -f "$BACKEND_DIR/pyproject.toml" ]]; then
  echo "[ERROR] roughcut/pyproject.toml was not found."
  exit 1
fi

if [[ ! -f "$ELECTRON_DIR/package.json" ]]; then
  echo "[ERROR] roughcut/electron/package.json was not found."
  exit 1
fi

echo "============================================"
echo "       RoughCut Standalone Installer"
echo "============================================"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "[ERROR] Python 3.10+ is required."
  exit 1
fi

print_step "1/5" "Installing Python dependencies"
"$PYTHON_CMD" -m pip install --user poetry
(cd "$BACKEND_DIR" && "$PYTHON_CMD" -m poetry install --no-interaction)
print_ok "Python backend ready."

print_step "2/5" "Installing Electron dependencies"
if ! command -v npm >/dev/null 2>&1; then
  echo "[ERROR] npm was not found in PATH. Install Node.js 20+ and rerun install.sh."
  exit 1
fi

(cd "$ELECTRON_DIR" && npm install && npm run build)
print_ok "Electron app built."

print_step "3/5" "Verifying SpacetimeDB CLI"
if ! command -v spacetime >/dev/null 2>&1; then
  print_info "Installing SpacetimeDB CLI..."
  curl -sSf https://install.spacetimedb.com | sh -s -- -y
fi

prepend_runtime_path
if command -v spacetime >/dev/null 2>&1; then
  print_ok "SpacetimeDB CLI ready: $(command -v spacetime)"
else
  print_warn "SpacetimeDB CLI was installed but is not yet visible in this shell."
  print_warn "RoughCut will try to locate it again at launch time."
fi

print_step "4/5" "Verifying Rust toolchain and WebAssembly target"
if ! command -v rustup >/dev/null 2>&1; then
  print_info "Installing Rust toolchain..."
  curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal
fi

prepend_runtime_path
if ! command -v cargo >/dev/null 2>&1; then
  print_info "Initializing the stable Rust toolchain..."
  rustup default stable >/dev/null
fi

if ! rustup target list --installed | grep -qx 'wasm32-unknown-unknown'; then
  print_info "Installing Rust target wasm32-unknown-unknown..."
  rustup target add wasm32-unknown-unknown
fi

print_ok "Rust toolchain ready: $(command -v cargo)"
print_ok "WebAssembly target ready: wasm32-unknown-unknown"

print_step "5/5" "Validating standalone launcher"
if [[ ! -f "$ROOT_LAUNCHER" ]]; then
  echo "[ERROR] $ROOT_LAUNCHER was not found."
  exit 1
fi

if [[ ! -f "$BACKEND_DIR/scripts/bootstrap_launch.py" ]]; then
  echo "[ERROR] roughcut/scripts/bootstrap_launch.py was not found."
  exit 1
fi

chmod +x "$ROOT_LAUNCHER"
print_ok "Standalone launcher ready."

print_info "Checking for DaVinci Resolve scripts folder..."
RESOLVE_SCRIPTS=""
for candidate in \
  "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility" \
  "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility" \
  "$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility" \
  "/opt/resolve/Fusion/Scripts/Utility"; do
  if [[ -d "$candidate" ]]; then
    RESOLVE_SCRIPTS="$candidate"
    break
  fi
done

if [[ -n "$RESOLVE_SCRIPTS" ]]; then
  print_info "Installing Resolve menu support to $RESOLVE_SCRIPTS"
  cp "$BACKEND_DIR/RoughCut.lua" "$RESOLVE_SCRIPTS/"
  rm -rf "$RESOLVE_SCRIPTS/roughcut"
  cp -R "$BACKEND_DIR" "$RESOLVE_SCRIPTS/roughcut"
  print_ok "Resolve menu support installed."
else
  print_info "Resolve scripts folder not found. Skipping Resolve menu installation."
fi

print_ok "RoughCut bootstrap complete."
print_ok "Launcher ready: $ROOT_LAUNCHER"

print_info "Launching RoughCut standalone..."
"$ROOT_LAUNCHER" &
