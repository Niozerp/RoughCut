"""Unit tests for ResolveApi discovery and standalone attach behavior."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from roughcut.backend.timeline.resolve_api import ResolveApi


@pytest.fixture(autouse=True)
def clear_resolve_module_cache(monkeypatch):
    """Ensure DaVinciResolveScript imports are isolated per test."""
    monkeypatch.delenv("RESOLVE_SCRIPT_API", raising=False)
    monkeypatch.delenv("RESOLVE_SCRIPT_LIB", raising=False)
    sys.modules.pop("DaVinciResolveScript", None)
    yield
    sys.modules.pop("DaVinciResolveScript", None)


def write_fake_resolve_module(module_dir: Path) -> None:
    """Create a fake DaVinciResolveScript module for discovery tests."""
    module_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / "DaVinciResolveScript.py").write_text(
        """
class _Project:
    def GetName(self):
        return "Demo Project"


class _ProjectManager:
    def GetCurrentProject(self):
        return _Project()


class _Resolve:
    def Fusion(self):
        return "fusion"

    def GetProjectManager(self):
        return _ProjectManager()

    def GetVersion(self):
        return "19.0"


def scriptapp(name):
    if name == "Resolve":
        return _Resolve()
    return None
""".strip(),
        encoding="utf-8",
    )


class TestResolveApiDiscovery:
    """Test standalone Resolve discovery helpers."""

    def test_connect_uses_env_module_path(self, tmp_path, monkeypatch):
        """ResolveApi should discover DaVinciResolveScript from RESOLVE_SCRIPT_API."""
        module_dir = tmp_path / "Modules"
        write_fake_resolve_module(module_dir)
        monkeypatch.setenv("RESOLVE_SCRIPT_API", str(module_dir))

        api = ResolveApi()

        assert api.connect() is True
        status = api.get_connection_status()
        assert status["connected"] is True
        assert status["project_name"] == "Demo Project"
        assert any(str(module_dir) == path for path in status["search_paths"])

    def test_status_reports_missing_module_when_unavailable(self, monkeypatch):
        """ResolveApi should report discovery failure outside Resolve."""
        monkeypatch.setenv("RESOLVE_SCRIPT_API", str(Path("/nonexistent/path")))
        monkeypatch.setattr(
            "roughcut.backend.timeline.resolve_api.import_module",
            lambda _name: (_ for _ in ()).throw(ImportError("module not found")),
        )

        api = ResolveApi()
        status = api.get_connection_status()

        assert status["connected"] is False
        assert status["available"] is False
        assert status["module_error"] is not None

    def test_disconnect_clears_cached_handles(self, tmp_path, monkeypatch):
        """Disconnect should clear cached connection state for future rediscovery."""
        module_dir = tmp_path / "Modules"
        write_fake_resolve_module(module_dir)
        monkeypatch.setenv("RESOLVE_SCRIPT_API", str(module_dir))
        monkeypatch.syspath_prepend(str(module_dir))

        api = ResolveApi()
        assert api.connect() is True

        api.disconnect()

        assert api._resolve is None
        assert api._project is None
        assert api._fusion is None
