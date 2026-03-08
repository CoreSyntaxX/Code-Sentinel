# SourceSentinel

Multi-language source code security scanner and vulnerability detector.

## Features

- Multi-language support (JavaScript, HTML, PHP, and more)
- Comprehensive vulnerability detection
- Static code analysis
- Security rule engine
- Multiple output formats (JSON, HTML, Markdown, SARIF)

## Installation

### From Source

```bash
pip install .
```

### With Development Dependencies

```bash
pip install ".[dev]"
```

### With All Optional Dependencies

```bash
pip install ".[all]"
```

### Specific Feature Sets

```bash
# Web crawling support
pip install ".[web]"

# GitHub API support
pip install ".[github]"
```

## Usage

### Command Line

```bash
sourcesentinel [options]
```

## Project Structure

- `src/` - Main source code
  - `main.py` - CLI entry point
  - `analyzers/` - Language-specific analyzers
  - `collectors/` - Code collection strategies
  - `detectors/` - Vulnerability detectors
  - `engine/` - Core scanning engine
  - `models/` - Data models
  - `processors/` - Code processors
  - `reporting/` - Report generators

## License

MIT
