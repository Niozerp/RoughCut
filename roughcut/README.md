# RoughCut

An AI-powered DaVinci Resolve plugin that transforms dormant media asset libraries into an intelligent creative partner.

## Installation

### Method 1: Drag-and-Drop Installation (Recommended)

1. Download the RoughCut release package
2. Drag `lua/roughcut.lua` into DaVinci Resolve's Scripts folder:
   - **macOS**: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Workflow Integration Scripts/`
   - **Windows**: `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Scripts\`
3. Restart Resolve or refresh the Scripts menu
4. Access RoughCut from the Scripts menu in DaVinci Resolve

### Method 2: Developer Installation

```bash
# Clone the repository
git clone <repository-url>
cd roughcut

# Install dependencies
poetry install

# Copy Lua script to Resolve Scripts folder
cp lua/roughcut.lua /path/to/resolve/scripts/
```

## Verification

After installation:
1. Open DaVinci Resolve
2. Go to **Workspace > Scripts** menu
3. Select **RoughCut**
4. A confirmation dialog should appear showing successful installation

## Project Structure

```
roughcut/
├── pyproject.toml              # Poetry configuration
├── poetry.lock                 # Dependency lock file
├── README.md                   # This file
├── src/
│   └── roughcut/              # Python package
│       ├── __init__.py        # Package initialization
│       ├── __main__.py        # Python entry point
│       ├── backend/           # Business logic (future stories)
│       ├── config/             # Configuration module
│       └── protocols/          # Lua ↔ Python communication
├── lua/
│   └── roughcut.lua           # Main Resolve script
├── templates/                 # Format templates
│   └── formats/
└── tests/                     # Test suite
```

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
