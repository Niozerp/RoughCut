# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""Bootstrap RoughCut prerequisites before launching the Electron app."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

WASM_TARGET = "wasm32-unknown-unknown"
EXPECTED_SPACETIMEDB_TABLES = {"asset_tags", "media_assets", "user_settings"}
VERIFY_SPACETIMEDB_HOST = "127.0.0.1"


class BootstrapError(RuntimeError):
    """Raised when prelaunch bootstrap cannot complete successfully."""


@dataclass(frozen=True)
class BootstrapState:
    """Snapshot of the environment used to plan bootstrap repairs."""

    python_ready: bool
    poetry_ready: bool
    backend_ready: bool
    node_ready: bool
    npm_ready: bool
    electron_runtime_ready: bool
    electron_bundle_ready: bool
    spacetime_ready: bool
    rustup_ready: bool
    cargo_ready: bool
    wasm_target_ready: bool


def log(message: str) -> None:
    """Print a bootstrap progress line."""

    print(f"[RoughCut Bootstrap] {message}", flush=True)


def prepend_path_entries(existing_path: str | None, entries: Iterable[Path | str]) -> str:
    """Prepend unique path entries while preserving order."""

    normalized_entries = [str(entry).strip() for entry in entries if str(entry).strip()]
    existing_segments = [
        segment.strip()
        for segment in (existing_path or "").split(os.pathsep)
        if segment.strip()
    ]

    seen: set[str] = set()
    ordered: list[str] = []
    for segment in [*normalized_entries, *existing_segments]:
        key = segment.lower() if os.name == "nt" else segment
        if key in seen:
            continue
        seen.add(key)
        ordered.append(segment)
    return os.pathsep.join(ordered)


def package_root_from_script() -> Path:
    """Return the shipped RoughCut package root."""

    return Path(__file__).resolve().parents[1]


def poetry_command(python_executable: str) -> list[str]:
    """Return the Poetry command bound to the active Python."""

    return [python_executable, "-m", "poetry"]


def windows_node_paths() -> list[Path]:
    """Return common Windows Node.js install directories."""

    if os.name != "nt":
        return []

    entries: list[Path] = []
    for value in (
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ):
        if not value:
            continue
        if value == os.environ.get("LOCALAPPDATA"):
            entries.append(Path(value) / "Programs" / "nodejs")
        else:
            entries.append(Path(value) / "nodejs")
    return entries


def runtime_path_entries() -> list[Path]:
    """Return PATH entries that commonly contain runtime prerequisites."""

    home = Path.home()
    entries = [home / ".cargo" / "bin", home / ".local" / "bin"]

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        entries.extend(
            [
                Path(local_app_data) / "SpacetimeDB",
                Path(local_app_data) / "SpacetimeDB" / "bin",
            ]
        )

    app_data = os.environ.get("APPDATA")
    if app_data:
        entries.extend(
            [
                Path(app_data) / "SpacetimeDB",
                Path(app_data) / "SpacetimeDB" / "bin",
            ]
        )

    entries.extend(windows_node_paths())
    return entries


def build_runtime_env() -> dict[str, str]:
    """Return an environment that can see newly installed runtimes."""

    env = os.environ.copy()
    env["PATH"] = prepend_path_entries(env.get("PATH"), runtime_path_entries())
    return env


def candidate_exists(candidate: Path | str, env: dict[str, str]) -> str | None:
    """Resolve a filesystem path or PATH command candidate."""

    if isinstance(candidate, Path):
        return str(candidate.resolve()) if candidate.exists() else None

    resolved = shutil.which(candidate, path=env.get("PATH"))
    return resolved or None


def can_run(command: Sequence[str], env: dict[str, str], cwd: Path | None = None, timeout: int = 10) -> bool:
    """Return True when a command exits successfully."""

    try:
        result = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return False

    return result.returncode == 0


def run_command(
    command: Sequence[str],
    description: str,
    env: dict[str, str],
    cwd: Path | None = None,
    timeout: int = 900,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command and raise a bootstrap error on failure."""

    log(description)
    try:
        result = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise BootstrapError(f"{description} failed because {command[0]!r} was not found.") from exc
    except subprocess.TimeoutExpired as exc:
        raise BootstrapError(f"{description} timed out after {timeout} seconds.") from exc
    except OSError as exc:
        raise BootstrapError(f"{description} failed: {exc}") from exc

    if check and result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        if output:
            raise BootstrapError(f"{description} failed: {output.splitlines()[-1]}")
        raise BootstrapError(f"{description} failed with exit code {result.returncode}.")

    return result


def with_spacetime_root_dir(root_dir: Path | None, args: Sequence[str]) -> list[str]:
    """Prepend a SpacetimeDB root directory argument when one is configured."""

    if root_dir is None:
        return list(args)
    return [f"--root-dir={root_dir}", *args]


def resolve_spacetime_server_url(host: str, port: int) -> str:
    """Return the HTTP URL for a SpacetimeDB server."""

    connect_host = "127.0.0.1" if host == "localhost" else host
    return f"http://{connect_host}:{port}"


def reserve_local_tcp_port(host: str = VERIFY_SPACETIMEDB_HOST) -> int:
    """Reserve and return an ephemeral local TCP port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def extract_json_prefix(raw_output: str) -> object:
    """Decode the first JSON value from CLI output with trailing warnings."""

    stripped = raw_output.strip()
    json_start_candidates = [index for index in (stripped.find("{"), stripped.find("[")) if index >= 0]
    if not json_start_candidates:
        raise BootstrapError("SpacetimeDB describe output did not contain JSON.")

    decoder = json.JSONDecoder()
    json_text = stripped[min(json_start_candidates):]
    try:
        payload, _ = decoder.raw_decode(json_text)
    except json.JSONDecodeError as exc:
        raise BootstrapError(f"SpacetimeDB describe output was not valid JSON: {exc}") from exc

    return payload


def described_table_names(raw_output: str) -> set[str]:
    """Return the set of table names reported by `spacetime describe --json`."""

    payload = extract_json_prefix(raw_output)
    if not isinstance(payload, dict):
        raise BootstrapError("SpacetimeDB describe output was not a JSON object.")

    tables = payload.get("tables")
    if not isinstance(tables, list):
        raise BootstrapError("SpacetimeDB describe output did not include a tables list.")

    names = {
        str(table.get("name"))
        for table in tables
        if isinstance(table, dict) and isinstance(table.get("name"), str)
    }
    if not names:
        raise BootstrapError("SpacetimeDB describe output did not report any table names.")

    return names


def collect_process_output(process: subprocess.Popen[str], timeout: int = 5) -> str:
    """Collect buffered stdout/stderr from a child process."""

    try:
        stdout_text, stderr_text = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            stdout_text, stderr_text = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            return ""

    return "\n".join(part.strip() for part in (stdout_text, stderr_text) if part and part.strip())


def terminate_process(process: subprocess.Popen[str]) -> None:
    """Terminate a child process and wait for it to exit."""

    if process.poll() is not None:
        collect_process_output(process)
        return

    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        process.kill()
        try:
            process.wait(timeout=5)
        except Exception:
            pass

    collect_process_output(process, timeout=1)


def is_local_tcp_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Return True when a local TCP listener is accepting connections."""

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_spacetimedb_server(
    host: str,
    port: int,
    process: subprocess.Popen[str],
    timeout: int = 15,
) -> None:
    """Wait until a temporary SpacetimeDB server responds to health checks."""
    deadline = time.time() + timeout

    while time.time() < deadline:
        if process.poll() is not None:
            output = collect_process_output(process)
            details = output or f"exit code {process.returncode}"
            raise BootstrapError(f"Temporary SpacetimeDB server exited before becoming ready: {details}")

        if is_local_tcp_port_open(host, port):
            return

        time.sleep(0.4)

    raise BootstrapError("Timed out waiting for the temporary SpacetimeDB server to become ready.")


def ensure_python_version() -> None:
    """Abort if the current interpreter is too old."""

    if sys.version_info < (3, 10):
        current = ".".join(str(part) for part in sys.version_info[:3])
        raise BootstrapError(
            f"RoughCut requires Python 3.10 or newer before launch. Current interpreter: {current}."
        )


def ensure_poetry_available(python_executable: str, env: dict[str, str]) -> list[str]:
    """Install Poetry into the active Python if it is missing."""

    command = poetry_command(python_executable)
    if can_run([*command, "--version"], env):
        return command

    run_command(
        [python_executable, "-m", "pip", "install", "--user", "poetry"],
        "Installing Poetry",
        env,
        timeout=900,
    )

    if not can_run([*command, "--version"], env):
        raise BootstrapError(
            "Poetry could not be activated after installation. Try running "
            f"{python_executable} -m pip install --user poetry manually."
        )
    return command


def backend_ready(command: Sequence[str], package_root: Path, env: dict[str, str]) -> bool:
    """Return True when the backend can be imported via Poetry."""

    return can_run(
        [*command, "run", "python", "-c", "import roughcut"],
        env,
        cwd=package_root,
        timeout=60,
    )


def ensure_backend_dependencies(command: Sequence[str], package_root: Path, env: dict[str, str]) -> None:
    """Install backend dependencies only when the Poetry environment is not ready."""

    if backend_ready(command, package_root, env):
        return

    install_result = run_command(
        [*command, "install", "--no-interaction"],
        "Installing RoughCut backend dependencies",
        env,
        cwd=package_root,
        timeout=1800,
        check=False,
    )

    combined_output = f"{install_result.stdout}\n{install_result.stderr}"
    if install_result.returncode != 0 and (
        "pyproject.toml changed significantly since poetry.lock was last generated" not in combined_output
    ):
        output = (install_result.stderr or install_result.stdout or "").strip()
        raise BootstrapError(
            f"Installing RoughCut backend dependencies failed: {output.splitlines()[-1] if output else 'unknown error'}"
        )

    if "pyproject.toml changed significantly since poetry.lock was last generated" in combined_output:
        run_command(
            [*command, "lock", "--no-interaction"],
            "Refreshing poetry.lock for RoughCut",
            env,
            cwd=package_root,
            timeout=900,
        )
        run_command(
            [*command, "install", "--no-interaction"],
            "Re-installing RoughCut backend dependencies",
            env,
            cwd=package_root,
            timeout=1800,
        )

    if not backend_ready(command, package_root, env):
        raise BootstrapError("RoughCut backend dependencies are still unavailable after Poetry install.")


def electron_source_paths(electron_dir: Path) -> list[Path]:
    """Return files and directories that should trigger an Electron rebuild."""

    return [
        electron_dir / "electron",
        electron_dir / "src",
        electron_dir / "package.json",
        electron_dir / "vite.config.ts",
        electron_dir / "tsconfig.electron.json",
        electron_dir / "tsconfig.preload.json",
        electron_dir / "index.html",
    ]


def latest_mtime(path: Path) -> float:
    """Return the most recent modification time for a file or directory tree."""

    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_mtime

    latest = path.stat().st_mtime
    for child in path.rglob("*"):
        if child.is_file():
            latest = max(latest, child.stat().st_mtime)
    return latest


def resolve_direct_electron_binary(electron_dir: Path, platform_name: str | None = None) -> Path:
    """Return the direct Electron runtime binary path for a platform."""

    resolved_platform = platform_name or sys.platform
    dist_dir = electron_dir / "node_modules" / "electron" / "dist"
    if resolved_platform == "win32":
        return dist_dir / "electron.exe"
    if resolved_platform == "darwin":
        return dist_dir / "Electron.app" / "Contents" / "MacOS" / "Electron"
    return dist_dir / "electron"


def is_electron_build_current(electron_dir: Path) -> bool:
    """Return True when the Electron bundle exists and is newer than the sources."""

    bundle_main = electron_dir / "dist" / "electron" / "main.js"
    if not bundle_main.exists():
        return False

    source_mtime = max(latest_mtime(path) for path in electron_source_paths(electron_dir))
    return bundle_main.stat().st_mtime >= source_mtime


def rust_module_dir(package_root: Path) -> Path:
    """Return the bundled SpacetimeDB Rust module directory."""

    return package_root / "src" / "roughcut" / "backend" / "database" / "rust_modules"


def rust_module_output_path(module_dir: Path) -> Path:
    """Return the expected wasm output path for the Rust module."""

    crate_name = "roughcut_spacetimedb"
    cargo_toml = module_dir / "Cargo.toml"
    if cargo_toml.exists():
        match = re.search(r'^name\s*=\s*"([^"]+)"', cargo_toml.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            crate_name = match.group(1).replace("-", "_")

    return module_dir / "target" / "wasm32-unknown-unknown" / "release" / f"{crate_name}.wasm"


def rust_module_source_mtime(module_dir: Path) -> float:
    """Return the latest modification time among Rust module source inputs."""

    candidates = [module_dir / "Cargo.toml", module_dir / "rust-toolchain.toml", module_dir / "src"]
    return max(latest_mtime(path) for path in candidates)


def is_rust_module_build_current(module_dir: Path) -> bool:
    """Return True when the wasm artifact exists and is newer than the sources."""

    wasm_path = rust_module_output_path(module_dir)
    if not wasm_path.exists():
        return False

    return wasm_path.stat().st_mtime >= rust_module_source_mtime(module_dir)


def node_command_candidates() -> list[Path | str]:
    """Return candidate node executables."""

    candidates: list[Path | str] = []
    if os.name == "nt":
        candidates.extend(path / "node.exe" for path in windows_node_paths())
        candidates.append("node.exe")
    candidates.append("node")
    return candidates


def npm_command_candidates(node_binary: str | None) -> list[Path | str]:
    """Return candidate npm executables."""

    candidates: list[Path | str] = []
    if node_binary:
        node_path = Path(node_binary)
        if node_path.is_file():
            if os.name == "nt":
                candidates.append(node_path.with_name("npm.cmd"))
                candidates.append(node_path.with_name("npm.exe"))
            else:
                candidates.append(node_path.with_name("npm"))

    if os.name == "nt":
        candidates.extend(["npm.cmd", "npm.exe"])
    candidates.append("npm")
    return candidates


def find_working_command(
    candidates: Sequence[Path | str],
    env: dict[str, str],
    version_args: Sequence[str],
) -> str | None:
    """Return the first candidate that can be executed successfully."""

    for candidate in candidates:
        resolved = candidate_exists(candidate, env)
        if not resolved:
            continue
        if can_run([resolved, *version_args], env):
            return resolved
    return None


def find_node_binary(env: dict[str, str]) -> str | None:
    """Locate a usable Node binary."""

    return find_working_command(node_command_candidates(), env, ["--version"])


def find_npm_command(env: dict[str, str], node_binary: str | None) -> str | None:
    """Locate a usable npm command."""

    return find_working_command(npm_command_candidates(node_binary), env, ["--version"])


def install_node(env: dict[str, str]) -> None:
    """Install Node.js using the best available platform-native installer."""

    if os.name == "nt":
        winget = find_working_command(["winget"], env, ["--version"])
        if not winget:
            raise BootstrapError(
                "Node.js is required to build RoughCut on first launch, but winget is unavailable. "
                "Install Node.js LTS from https://nodejs.org/ and relaunch RoughCut."
            )
        run_command(
            [
                winget,
                "install",
                "--id",
                "OpenJS.NodeJS.LTS",
                "-e",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            "Installing Node.js LTS with winget",
            env,
            timeout=1800,
        )
        return

    if sys.platform == "darwin":
        brew = find_working_command(["brew"], env, ["--version"])
        if not brew:
            raise BootstrapError(
                "Node.js is required to build RoughCut on first launch, but Homebrew is not available. "
                "Install Node.js LTS from https://nodejs.org/ and relaunch RoughCut."
            )
        run_command([brew, "install", "node"], "Installing Node.js with Homebrew", env, timeout=1800)
        return

    installer_prefix = ["sudo"] if os.geteuid() != 0 and shutil.which("sudo") else []
    if find_working_command(["apt-get"], env, ["--version"]):
        run_command([*installer_prefix, "apt-get", "update"], "Updating apt package lists for Node.js", env, timeout=1800)
        run_command([*installer_prefix, "apt-get", "install", "-y", "nodejs", "npm"], "Installing Node.js with apt-get", env, timeout=1800)
        return
    if find_working_command(["dnf"], env, ["--version"]):
        run_command([*installer_prefix, "dnf", "install", "-y", "nodejs", "npm"], "Installing Node.js with dnf", env, timeout=1800)
        return
    if find_working_command(["yum"], env, ["--version"]):
        run_command([*installer_prefix, "yum", "install", "-y", "nodejs", "npm"], "Installing Node.js with yum", env, timeout=1800)
        return
    if find_working_command(["pacman"], env, ["--version"]):
        run_command([*installer_prefix, "pacman", "-Sy", "--noconfirm", "nodejs", "npm"], "Installing Node.js with pacman", env, timeout=1800)
        return

    raise BootstrapError(
        "Node.js is required to build RoughCut on first launch, but no supported package manager was found. "
        "Install Node.js LTS from https://nodejs.org/ and relaunch RoughCut."
    )


def ensure_electron_ready(package_root: Path, env: dict[str, str]) -> Path:
    """Install Electron dependencies and rebuild only when necessary."""

    electron_dir = package_root / "electron"
    if not electron_dir.exists():
        raise BootstrapError(f"Electron directory was not found at {electron_dir}.")

    binary_path = resolve_direct_electron_binary(electron_dir)
    runtime_ready = binary_path.exists()
    build_ready = is_electron_build_current(electron_dir)
    if runtime_ready and build_ready:
        return binary_path

    node_binary = find_node_binary(env)
    npm_command = find_npm_command(env, node_binary)
    if not node_binary or not npm_command:
        install_node(env)
        env.clear()
        env.update(build_runtime_env())
        node_binary = find_node_binary(env)
        npm_command = find_npm_command(env, node_binary)

    if not node_binary or not npm_command:
        raise BootstrapError("Node.js was installed, but node/npm are still unavailable in the launch environment.")

    if not runtime_ready:
        run_command([npm_command, "install"], "Installing Electron dependencies", env, cwd=electron_dir, timeout=1800)

    if not is_electron_build_current(electron_dir):
        run_command([npm_command, "run", "build"], "Building RoughCut Electron app", env, cwd=electron_dir, timeout=1800)

    binary_path = resolve_direct_electron_binary(electron_dir)
    if not binary_path.exists():
        raise BootstrapError("Electron runtime is still missing after npm install.")
    if not is_electron_build_current(electron_dir):
        raise BootstrapError("Electron build output is stale after npm run build.")

    return binary_path


def spacetime_candidates() -> list[Path | str]:
    """Return candidate spacetime CLI locations."""

    home = Path.home()
    candidates: list[Path | str] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.extend(
            [
                Path(local_app_data) / "SpacetimeDB" / "spacetime.exe",
                Path(local_app_data) / "SpacetimeDB" / "bin" / "spacetime.exe",
            ]
        )

    app_data = os.environ.get("APPDATA")
    if app_data:
        candidates.extend(
            [
                Path(app_data) / "SpacetimeDB" / "spacetime.exe",
                Path(app_data) / "SpacetimeDB" / "bin" / "spacetime.exe",
            ]
        )

    candidates.extend(
        [
            home / ".local" / "bin" / "spacetime.exe",
            home / ".local" / "bin" / "spacetime",
            "spacetime",
        ]
    )
    return candidates


def find_spacetime_binary(env: dict[str, str]) -> str | None:
    """Locate the SpacetimeDB CLI."""

    return find_working_command(spacetime_candidates(), env, ["--version"])


def install_spacetimedb(env: dict[str, str]) -> None:
    """Install the SpacetimeDB CLI."""

    if os.name == "nt":
        run_command(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "iwr https://windows.spacetimedb.com -UseBasicParsing | iex",
            ],
            "Installing SpacetimeDB CLI",
            env,
            timeout=1800,
        )
        return

    run_command(
        ["bash", "-lc", "curl -sSf https://install.spacetimedb.com | sh -s -- -y"],
        "Installing SpacetimeDB CLI",
        env,
        timeout=1800,
    )


def ensure_spacetimedb(env: dict[str, str]) -> str:
    """Ensure the SpacetimeDB CLI is available."""

    binary = find_spacetime_binary(env)
    if binary:
        return binary

    install_spacetimedb(env)
    env.clear()
    env.update(build_runtime_env())
    binary = find_spacetime_binary(env)
    if not binary:
        raise BootstrapError("SpacetimeDB CLI is still unavailable after installation.")
    return binary


def rustup_candidates() -> list[Path | str]:
    """Return candidate rustup locations."""

    home = Path.home()
    return [
        home / ".cargo" / "bin" / ("rustup.exe" if os.name == "nt" else "rustup"),
        "rustup.exe" if os.name == "nt" else "rustup",
        "rustup",
    ]


def cargo_candidates() -> list[Path | str]:
    """Return candidate cargo locations."""

    home = Path.home()
    return [
        home / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo"),
        "cargo.exe" if os.name == "nt" else "cargo",
        "cargo",
    ]


def find_rustup_binary(env: dict[str, str]) -> str | None:
    """Locate rustup."""

    return find_working_command(rustup_candidates(), env, ["--version"])


def find_cargo_binary(env: dict[str, str]) -> str | None:
    """Locate cargo."""

    return find_working_command(cargo_candidates(), env, ["--version"])


def install_rust(env: dict[str, str]) -> None:
    """Install the Rust toolchain."""

    if os.name == "nt":
        winget = find_working_command(["winget"], env, ["--version"])
        if not winget:
            raise BootstrapError(
                "Rust is required to publish RoughCut's bundled SpacetimeDB module, but winget is unavailable. "
                "Install rustup from https://rustup.rs/ and relaunch RoughCut."
            )
        run_command(
            [
                winget,
                "install",
                "--id",
                "Rustlang.Rustup",
                "-e",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            "Installing rustup with winget",
            env,
            timeout=1800,
        )
        return

    run_command(
        ["bash", "-lc", "curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal"],
        "Installing rustup",
        env,
        timeout=1800,
    )


def wasm_target_installed(rustup_binary: str, env: dict[str, str]) -> bool:
    """Return True when the Rust wasm target is installed."""

    try:
        result = subprocess.run(
            [rustup_binary, "target", "list", "--installed"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return False

    if result.returncode != 0:
        return False

    installed_targets = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return WASM_TARGET in installed_targets


def ensure_rust_toolchain(env: dict[str, str]) -> None:
    """Ensure rustup, cargo, and the wasm target are ready."""

    rustup_binary = find_rustup_binary(env)
    cargo_binary = find_cargo_binary(env)
    if not rustup_binary or not cargo_binary:
        install_rust(env)
        env.clear()
        env.update(build_runtime_env())
        rustup_binary = find_rustup_binary(env)
        cargo_binary = find_cargo_binary(env)

    if not rustup_binary:
        raise BootstrapError("rustup is still unavailable after installation.")

    if not cargo_binary:
        run_command([rustup_binary, "default", "stable"], "Initializing the stable Rust toolchain", env, timeout=900)
        env.clear()
        env.update(build_runtime_env())
        cargo_binary = find_cargo_binary(env)

    if not cargo_binary:
        raise BootstrapError("cargo is still unavailable after initializing the Rust toolchain.")

    if not wasm_target_installed(rustup_binary, env):
        run_command([rustup_binary, "target", "add", WASM_TARGET], f"Installing Rust target {WASM_TARGET}", env, timeout=1800)

    if not wasm_target_installed(rustup_binary, env):
        raise BootstrapError(f"Rust target {WASM_TARGET} is still unavailable after installation.")


def ensure_rust_module_buildable(package_root: Path, env: dict[str, str]) -> None:
    """Build the bundled Rust module before launching Electron when needed."""

    module_dir = rust_module_dir(package_root)
    if not module_dir.exists():
        raise BootstrapError(f"Bundled SpacetimeDB Rust module was not found at {module_dir}.")

    if is_rust_module_build_current(module_dir):
        return

    cargo_binary = find_cargo_binary(env)
    if not cargo_binary:
        raise BootstrapError("cargo is unavailable while building the bundled SpacetimeDB Rust module.")

    run_command(
        [cargo_binary, "build", "--target", WASM_TARGET, "--release"],
        "Building RoughCut's bundled SpacetimeDB Rust module",
        env,
        cwd=module_dir,
        timeout=1800,
    )

    if not is_rust_module_build_current(module_dir):
        raise BootstrapError("The bundled SpacetimeDB Rust module did not produce a wasm artifact.")


def verify_spacetimedb_module_setup(
    package_root: Path,
    spacetime_binary: str,
    env: dict[str, str],
) -> None:
    """Verify the bundled module publishes cleanly and exposes expected tables."""

    module_dir = rust_module_dir(package_root)
    if not module_dir.exists():
        raise BootstrapError(f"Bundled SpacetimeDB Rust module was not found at {module_dir}.")

    with tempfile.TemporaryDirectory(prefix="roughcut-spacetimedb-verify-") as temp_dir:
        temp_root = Path(temp_dir)
        data_dir = temp_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        port = reserve_local_tcp_port()
        server_url = resolve_spacetime_server_url(VERIFY_SPACETIMEDB_HOST, port)
        start_command = [
            spacetime_binary,
            *with_spacetime_root_dir(
                None,
                [
                    "start",
                    "--data-dir",
                    str(data_dir),
                    "--listen-addr",
                    f"{VERIFY_SPACETIMEDB_HOST}:{port}",
                ],
            ),
        ]

        log("Verifying RoughCut's bundled SpacetimeDB module and schema.")
        process = subprocess.Popen(
            start_command,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        try:
            wait_for_spacetimedb_server(VERIFY_SPACETIMEDB_HOST, port, process)
            run_command(
                [
                    spacetime_binary,
                    *with_spacetime_root_dir(
                        None,
                        [
                            "publish",
                            "--yes",
                            "--server",
                            server_url,
                            "--module-path",
                            str(module_dir),
                            "roughcut",
                        ],
                    ),
                ],
                "Publishing RoughCut's bundled SpacetimeDB module for verification",
                env,
                timeout=120,
            )
            describe_result = run_command(
                [
                    spacetime_binary,
                    *with_spacetime_root_dir(
                        None,
                        ["describe", "--json", "--server", server_url, "--yes", "roughcut"],
                    ),
                ],
                "Inspecting verified SpacetimeDB schema",
                env,
                timeout=30,
            )
            table_names = described_table_names(
                "\n".join(
                    part for part in (describe_result.stdout, describe_result.stderr) if part.strip()
                )
            )
            missing_tables = EXPECTED_SPACETIMEDB_TABLES - table_names
            if missing_tables:
                raise BootstrapError(
                    "Published RoughCut SpacetimeDB module is missing expected tables: "
                    f"{', '.join(sorted(missing_tables))}. "
                    f"Found: {', '.join(sorted(table_names))}."
                )
        finally:
            terminate_process(process)


def determine_bootstrap_actions(state: BootstrapState) -> list[str]:
    """Return the repair actions implied by a detected bootstrap state."""

    if not state.python_ready:
        return ["abort_python"]

    actions: list[str] = []
    if not state.poetry_ready:
        actions.append("install_poetry")
    if not state.backend_ready:
        actions.append("install_backend")
    if not state.electron_runtime_ready or not state.electron_bundle_ready:
        if not state.node_ready or not state.npm_ready:
            actions.append("install_node")
        if not state.electron_runtime_ready:
            actions.append("npm_install")
        if not state.electron_bundle_ready:
            actions.append("npm_build")
    if not state.spacetime_ready:
        actions.append("install_spacetimedb")
    if not state.rustup_ready or not state.cargo_ready:
        actions.append("install_rust")
    elif not state.wasm_target_ready:
        actions.append("install_wasm_target")
    return actions


def collect_bootstrap_state(package_root: Path, python_executable: str, env: dict[str, str]) -> BootstrapState:
    """Detect the current bootstrap status before applying repairs."""

    command = poetry_command(python_executable)
    poetry_ready = can_run([*command, "--version"], env)
    node_binary = find_node_binary(env)
    npm_command = find_npm_command(env, node_binary)
    electron_dir = package_root / "electron"
    rustup_binary = find_rustup_binary(env)

    return BootstrapState(
        python_ready=sys.version_info >= (3, 10),
        poetry_ready=poetry_ready,
        backend_ready=poetry_ready and backend_ready(command, package_root, env),
        node_ready=node_binary is not None,
        npm_ready=npm_command is not None,
        electron_runtime_ready=resolve_direct_electron_binary(electron_dir).exists(),
        electron_bundle_ready=is_electron_build_current(electron_dir),
        spacetime_ready=find_spacetime_binary(env) is not None,
        rustup_ready=rustup_binary is not None,
        cargo_ready=find_cargo_binary(env) is not None,
        wasm_target_ready=bool(rustup_binary and wasm_target_installed(rustup_binary, env)),
    )


def launch_electron_app(
    binary_path: Path,
    electron_dir: Path,
    mode: str,
    project_name: str | None,
    env: dict[str, str],
) -> None:
    """Launch the Electron app directly from its packaged binary."""

    launch_env = env.copy()
    launch_env["ROUGHCUT_LAUNCH_MODE"] = mode
    if project_name:
        launch_env["ROUGHCUT_PROJECT"] = project_name
    else:
        launch_env.pop("ROUGHCUT_PROJECT", None)

    log_dir = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".").resolve()
    stdout_path = log_dir / f"roughcut-electron-stdout-{os.getpid()}.log"
    stderr_path = log_dir / f"roughcut-electron-stderr-{os.getpid()}.log"
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")

    popen_kwargs: dict[str, object] = {
        "cwd": str(electron_dir),
        "env": launch_env,
        "stdout": stdout_handle,
        "stderr": stderr_handle,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        popen_kwargs["close_fds"] = True
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen([str(binary_path), "."], **popen_kwargs)

    deadline = time.time() + 8
    while time.time() < deadline:
        if proc.poll() is not None:
            stdout_handle.close()
            stderr_handle.close()
            stdout_text = stdout_path.read_text(encoding="utf-8", errors="ignore").strip() if stdout_path.exists() else ""
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="ignore").strip() if stderr_path.exists() else ""
            details = stderr_text or stdout_text or f"exit code {proc.returncode}"
            raise BootstrapError(f"Electron exited during startup: {details}")
        time.sleep(0.25)

    stdout_handle.close()
    stderr_handle.close()


def run_bootstrap(mode: str, project_name: str | None) -> None:
    """Run the end-to-end prelaunch bootstrap."""

    ensure_python_version()
    package_root = package_root_from_script()
    env = build_runtime_env()

    state = collect_bootstrap_state(package_root, sys.executable, env)
    planned_actions = determine_bootstrap_actions(state)
    if planned_actions:
        log(f"Bootstrap repairs required: {', '.join(planned_actions)}")
    else:
        log("Bootstrap check passed without repairs.")

    command = ensure_poetry_available(sys.executable, env)
    ensure_backend_dependencies(command, package_root, env)
    electron_binary = ensure_electron_ready(package_root, env)
    spacetime_binary = ensure_spacetimedb(env)
    ensure_rust_toolchain(env)
    ensure_rust_module_buildable(package_root, env)
    verify_spacetimedb_module_setup(package_root, spacetime_binary, env)

    log("Launching RoughCut Electron app.")
    launch_electron_app(electron_binary, package_root / "electron", mode, project_name, env)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for bootstrap launch."""

    parser = argparse.ArgumentParser(description="Bootstrap RoughCut before launching Electron.")
    parser.add_argument("--mode", choices=("standalone", "resolve"), required=True)
    parser.add_argument("--project-name", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    args = parse_args(argv)
    try:
        run_bootstrap(mode=args.mode, project_name=args.project_name)
    except BootstrapError as exc:
        log(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
