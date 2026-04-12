"""Unit tests for the prelaunch RoughCut bootstrap helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from bootstrap_launch import (
    BootstrapState,
    described_table_names,
    determine_bootstrap_actions,
    resolve_direct_electron_binary,
)


class TestDetermineBootstrapActions(unittest.TestCase):
    """Validate the bootstrap repair planner."""

    def test_flags_missing_python_before_any_other_action(self) -> None:
        state = BootstrapState(
            python_ready=False,
            poetry_ready=False,
            backend_ready=False,
            node_ready=False,
            npm_ready=False,
            electron_runtime_ready=False,
            electron_bundle_ready=False,
            spacetime_ready=False,
            rustup_ready=False,
            cargo_ready=False,
            wasm_target_ready=False,
        )

        self.assertEqual(determine_bootstrap_actions(state), ["abort_python"])

    def test_skips_node_install_when_electron_runtime_is_already_ready(self) -> None:
        state = BootstrapState(
            python_ready=True,
            poetry_ready=True,
            backend_ready=True,
            node_ready=False,
            npm_ready=False,
            electron_runtime_ready=True,
            electron_bundle_ready=True,
            spacetime_ready=True,
            rustup_ready=True,
            cargo_ready=True,
            wasm_target_ready=True,
        )

        self.assertEqual(determine_bootstrap_actions(state), [])

    def test_requires_node_install_and_build_when_electron_assets_are_missing(self) -> None:
        state = BootstrapState(
            python_ready=True,
            poetry_ready=True,
            backend_ready=True,
            node_ready=False,
            npm_ready=False,
            electron_runtime_ready=False,
            electron_bundle_ready=False,
            spacetime_ready=True,
            rustup_ready=True,
            cargo_ready=True,
            wasm_target_ready=True,
        )

        self.assertEqual(
            determine_bootstrap_actions(state),
            ["install_node", "npm_install", "npm_build"],
        )

    def test_detects_spacetime_and_rust_repairs(self) -> None:
        state = BootstrapState(
            python_ready=True,
            poetry_ready=True,
            backend_ready=True,
            node_ready=True,
            npm_ready=True,
            electron_runtime_ready=True,
            electron_bundle_ready=True,
            spacetime_ready=False,
            rustup_ready=False,
            cargo_ready=False,
            wasm_target_ready=False,
        )

        self.assertEqual(determine_bootstrap_actions(state), ["install_spacetimedb", "install_rust"])

    def test_detects_missing_wasm_target(self) -> None:
        state = BootstrapState(
            python_ready=True,
            poetry_ready=True,
            backend_ready=True,
            node_ready=True,
            npm_ready=True,
            electron_runtime_ready=True,
            electron_bundle_ready=True,
            spacetime_ready=True,
            rustup_ready=True,
            cargo_ready=True,
            wasm_target_ready=False,
        )

        self.assertEqual(determine_bootstrap_actions(state), ["install_wasm_target"])


class TestResolveDirectElectronBinary(unittest.TestCase):
    """Validate direct Electron binary path resolution."""

    def test_resolves_platform_specific_binary_paths(self) -> None:
        electron_dir = Path("/tmp/roughcut/electron")

        self.assertEqual(
            resolve_direct_electron_binary(electron_dir, "win32"),
            electron_dir / "node_modules" / "electron" / "dist" / "electron.exe",
        )
        self.assertEqual(
            resolve_direct_electron_binary(electron_dir, "darwin"),
            electron_dir
            / "node_modules"
            / "electron"
            / "dist"
            / "Electron.app"
            / "Contents"
            / "MacOS"
            / "Electron",
        )
        self.assertEqual(
            resolve_direct_electron_binary(electron_dir, "linux"),
            electron_dir / "node_modules" / "electron" / "dist" / "electron",
        )


class TestDescribeTableNames(unittest.TestCase):
    """Validate parsing of `spacetime describe --json` output."""

    def test_ignores_trailing_cli_warning_after_json(self) -> None:
        output = """
        {
          "tables": [
            {"name": "asset_tags"},
            {"name": "media_assets"},
            {"name": "user_settings"}
          ]
        }
        WARNING: This command is UNSTABLE and subject to breaking changes.
        """

        self.assertEqual(
            described_table_names(output),
            {"asset_tags", "media_assets", "user_settings"},
        )


if __name__ == "__main__":
    unittest.main()
