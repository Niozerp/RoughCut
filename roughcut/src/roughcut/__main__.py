"""RoughCut entry point.

Supports running as a module: python -m roughcut
"""

from roughcut import __version__


def main():
    """Main entry point for RoughCut backend."""
    print(f"RoughCut Backend v{__version__}")
    print("Status: Installation successful (Story 1.1)")
    print("Note: Full backend features coming in Story 1.3")


if __name__ == "__main__":
    main()
