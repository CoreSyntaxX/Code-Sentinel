# SourceSentinel Installation Guide

## Quick Start

The project is now fully installable using modern Python packaging standards.

### Installation in Development Mode

```bash
# Install in editable mode (development)
pip install -e .
```

### Installation with Optional Dependencies

```bash
# With development tools (pytest, black, flake8, mypy, etc.)
pip install -e ".[dev]"

# With web crawling support (requests, beautifulsoup4)
pip install -e ".[web]"

# With GitHub API support (pygithub)
pip install -e ".[github]"

# With all optional dependencies
pip install -e ".[all]"
```

### Standard Installation

```bash
# Install normally (not editable)
pip install .
```

### Installation from PyPI (Future)

Once published to PyPI:

```bash
pip install sourcesentinel
pip install sourcesentinel[dev]
pip install sourcesentinel[web,github]
```

## Verification

After installation, verify that the CLI tool works:

```bash
sourcesentinel --help
```

## Project Structure

- **pyproject.toml** - Modern Python project configuration (PEP 517/518)
- **setup.py** - Minimal setup script (defers to pyproject.toml)
- **README.md** - Project documentation
- **src/** - Main source code
  - `main.py` - CLI entry point
  - `analyzers/` - Language-specific code analyzers
  - `collectors/` - Code source collectors (local, web, GitHub, Git)
  - `detectors/` - Security vulnerability detectors
  - `engine/` - Core scanning orchestration engine
  - `models/` - Data models
  - `processors/` - Code processing utilities
  - `reporting/` - Report generation

## Key Features

✅ **Modern Packaging** - Uses pyproject.toml with PEP 517/518 standards
✅ **Entry Points** - CLI command `sourcesentinel` available after installation
✅ **Optional Dependencies** - Install only what you need
✅ **Editable Installation** - Development-friendly with `pip install -e .`
✅ **Cross-Platform** - Python 3.8+ support

## Dependencies

### Core
- `pyyaml>=6.0` - YAML parsing for rules
- `esprima>=4.0.1` - JavaScript AST parsing

### Optional (Web)
- `requests>=2.28.0` - HTTP requests
- `beautifulsoup4>=4.11.0` - HTML parsing

### Optional (GitHub)
- `pygithub>=1.55` - GitHub API client

### Optional (Development)
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `black>=23.0.0` - Code formatter
- `flake8>=6.0.0` - Linter
- `mypy>=1.0.0` - Type checker
- `isort>=5.12.0` - Import sorter

## Configuration

All project metadata is defined in `pyproject.toml`:

- Project information (name, version, description, authors, etc.)
- Dependencies and optional dependency groups
- CLI entry points
- Tool configurations (pytest, black, isort, mypy)
- Build system configuration

## Troubleshooting

### "externally-managed-environment" Error

If you encounter this error, use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Linux/macOS
.venv\Scripts\activate     # On Windows
pip install -e .
```

### Cannot find `sourcesentinel` command

Make sure the virtual environment is activated:

```bash
source .venv/bin/activate
sourcesentinel --help
```

### Import errors

Reinstall in development mode:

```bash
pip install -e . --force-reinstall
```
