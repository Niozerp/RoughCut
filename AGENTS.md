# BMad Framework - Agent Guidelines

This repository contains the BMad (Business Method for Agent Development) framework - a structured system of skills for agentic workflows.

## Project Structure

- `_bmad/{module}/` - Module configurations and skills
  - `core/` - Core utilities (init, distillator, etc.)
  - `bmm/` - Business Method Module (analysis, planning, solutioning, implementation)
  - `wds/` - Workflow Design System
- `.opencode/skills/` - Opencode-compatible skill definitions
- `design-artifacts/` - Product design outputs
- `_bmad-output/` - Generated outputs (planning, implementation artifacts)

## Build/Test/Lint Commands

### Running Tests

**Single test file:**
```bash
cd _bmad/core/bmad-init/scripts && python3 -m unittest tests.test_bmad_init
```

**Single test class:**
```bash
cd _bmad/core/bmad-init/scripts && python3 -m unittest tests.test_bmad_init.TestFindProjectRoot
```

**Single test method:**
```bash
cd _bmad/core/bmad-init/scripts && python3 -m unittest tests.test_bmad_init.TestFindProjectRoot.test_finds_bmad_folder
```

**All tests in a directory:**
```bash
cd _bmad/core/bmad-init/scripts && python3 -m unittest discover -s tests -v
```

**Run with pytest (if available):**
```bash
pytest _bmad/core/bmad-init/scripts/tests/test_bmad_init.py -v
```

### Opencode Extension (in .opencode/)

```bash
cd .opencode
bun install    # Install dependencies
bun run dev    # Development mode (if available)
```

## Code Style Guidelines

### Python Scripts

**File structure:**
```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "requests"]
# ///

#!/usr/bin/env python3
"""Module docstring explaining purpose."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Constants in UPPER_SNAKE_CASE
CHARS_PER_TOKEN = 4
SKIP_DIRS = {"node_modules", ".git"}

# Type hints on function signatures
def process_files(paths: list[str]) -> dict[str, any]:
    """Process file paths and return metadata."""
    pass

if __name__ == "__main__":
    main()
```

**Key conventions:**
- Use PEP 723 dependency declarations at the top of executable scripts
- Import from `__future__` for annotations
- Type hints on all function parameters and return values
- Docstrings for all modules and public functions
- Constants in UPPER_SNAKE_CASE
- Functions in snake_case, classes in PascalCase
- Use `pathlib.Path` for file operations, not raw strings
- Test files in `scripts/tests/` with `test_*.py` naming

### SKILL.md Files

**Frontmatter format:**
```yaml
---
name: bmad-{skill-name}
description: "Clear, actionable description. Use when the user says X."
argument-hint: "[--flag] [--option=value]"  # Optional
---
```

**Content guidelines:**
- Start with ## Overview section
- Use imperative voice for instructions
- Configuration references: `{project-root}`, `{user_name}`, `{output_folder}`
- Reference module configs: `_bmad/{module}/config.yaml`
- Use numbered steps for sequential processes
- Code blocks for JSON/YAML examples

### Configuration Files (config.yaml)

**Structure:**
```yaml
# Module Configuration
# Version: X.Y.Z

module_specific_var: "value"
# Core values (inherited from core module):
user_name: "Name"
communication_language: English
document_output_language: English
output_folder: "{project-root}/_bmad-output"
```

**Conventions:**
- Use `{project-root}` placeholder for paths
- Document file header with module name and version
- Core config values are inherited/included in all module configs

### Error Handling

```python
try:
    result = load_config_file(path)
except FileNotFoundError:
    return None  # Graceful degradation
except yaml.YAMLError as e:
    print(f"Error parsing {path}: {e}", file=sys.stderr)
    sys.exit(1)
```

- Use specific exception types
- Print errors to stderr
- Return None for expected missing resources
- Exit with error code for fatal errors

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Skills | kebab-case with prefix | `bmad-init`, `bmad-distillator` |
| Python modules | snake_case | `bmad_init.py` |
| Classes | PascalCase | `ConfigLoader` |
| Functions | snake_case | `load_module_config` |
| Constants | UPPER_SNAKE_CASE | `CHARS_PER_TOKEN` |
| Config vars | snake_case | `output_folder` |

### Imports Ordering

```python
from __future__ import annotations  # First

import argparse  # Built-ins
import json
import sys
from pathlib import Path

import yaml  # Third-party

from bmad_init import load_config  # Local (if importing from sibling)
```

## Testing Guidelines

- Use Python's built-in `unittest` framework
- Test files: `scripts/tests/test_*.py`
- Use `setUp()` and `tearDown()` for temp directories
- Test names should describe behavior: `test_finds_bmad_folder`
- Use `tempfile.mkdtemp()` for isolated test environments
- Always clean up temp files in `tearDown()` or `try/finally`

## Key Dependencies

- Python >= 3.10
- pyyaml (for YAML parsing)
- Standard library: `pathlib`, `argparse`, `json`, `tempfile`, `unittest`

## Important Paths

- Core config: `_bmad/core/config.yaml`
- Module configs: `_bmad/{module}/config.yaml`
- Skills: `_bmad/{module}/{phase}/{skill-name}/SKILL.md`
- Skill prompts: `_bmad/{module}/{phase}/{skill-name}/prompts/`
- Output: `_bmad-output/` (configurable)
