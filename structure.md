source-scanner/
├── src/
│   ├── __init__.py
│   ├── main.py                     # CLI entry point
│   ├── api.py                      # REST API entry point (optional)
│   │
│   ├── engine/                     # Core orchestration
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Main analysis pipeline
│   │   ├── rule_engine.py          # Rule loading/execution
│   │   ├── context_manager.py      # Analysis state tracking
│   │   ├── pipeline.py             # Processor pipeline builder
│   │   └── taint_tracker.py        # Data flow analysis
│   │
│   ├── collectors/                 # File collection
│   │   ├── __init__.py
│   │   ├── base_collector.py       # Abstract collector
│   │   ├── file_collector.py       # Local filesystem
│   │   ├── web_crawler.py          # URL spidering
│   │   ├── github_scraper.py       # GitHub API/scanning
│   │   ├── s3_collector.py         # AWS S3 buckets
│   │   └── git_collector.py        # Git repositories
│   │
│   ├── analyzers/                  # Language-specific analysis
│   │   ├── __init__.py
│   │   ├── base_analyzer.py        # Abstract analyzer class
│   │   ├── javascript/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py         # Main JS analyzer
│   │   │   ├── dom_sink_detector.py
│   │   │   ├── ast_parser.py       # AST-based analysis
│   │   │   └── framework_detector.py # React/Vue/Angular
│   │   │
│   │   ├── php/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py
│   │   │   ├── sink_detector.py
│   │   │   └── function_tracker.py
│   │   │
│   │   ├── html/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py
│   │   │   ├── xss_detector.py
│   │   │   └── template_scanner.py # Jinja2, Twig, etc.
│   │   │
│   │   ├── python/
│   │   │   └── ... (for future)
│   │   │
│   │   └── multi_language/
│   │       ├── secrets_detector.py # API keys, tokens, passwords
│   │       ├── sanitization_checker.py
│   │       ├── jwt_detector.py
│   │       ├── cookie_analyzer.py
│   │       └── email_scanner.py
│   │
│   ├── detectors/                  # Specialized detectors
│   │   ├── __init__.py
│   │   ├── pattern_detector.py     # Regex-based detection
│   │   ├── entropy_detector.py     # High-entropy strings
│   │   ├── structural_detector.py  # Code structure analysis
│   │   └── config_detector.py      # Config file analysis
│   │
│   ├── processors/                 # Pre/post processing
│   │   ├── __init__.py
│   │   ├── normalizer.py           # Code normalization
│   │   ├── beautifier.py           # JS/PHP beautification
│   │   ├── minifier.py             # Handle minified code
│   │   ├── tokenizer.py            # Code tokenization
│   │   └── deobfuscator.py         # Basic deobfuscation
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── cache_manager.py        # File/result caching
│   │   ├── security.py             # Input validation, safe ops
│   │   ├── parallel_executor.py    # Parallel processing
│   │   ├── file_utils.py           # Safe file operations
│   │   ├── network_utils.py        # Safe HTTP operations
│   │   ├── string_utils.py         # String manipulation
│   │   └── logging_config.py       # Centralized logging
│   │
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── base_reporter.py        # Abstract reporter
│   │   ├── json_reporter.py
│   │   ├── html_reporter.py        # Visual HTML report
│   │   ├── markdown_reporter.py
│   │   ├── sarif_reporter.py       # SARIF format
│   │   ├── console_reporter.py     # CLI output
│   │   └── report_builder.py       # Report assembly
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py             # Main settings loader
│   │   ├── defaults.py             # Default configurations
│   │   └── rules/                  # Rule definitions
│   │       ├── __init__.py
│   │       ├── javascript/
│   │       │   ├── dom_sinks.yaml
│   │       │   ├── xss_patterns.yaml
│   │       │   └── framework_rules.yaml
│   │       │
│   │       ├── php/
│   │       │   ├── sql_injection.yaml
│   │       │   ├── file_inclusion.yaml
│   │       │   └── command_injection.yaml
│   │       │
│   │       ├── secrets/
│   │       │   ├── api_keys.yaml
│   │       │   ├── jwt_patterns.yaml
│   │       │   └── credential_patterns.yaml
│   │       │
│   │       └── sanitization/
│   │           ├── escape_functions.yaml
│   │           └── filter_functions.yaml
│   │
│   └── models/                     # Data models
│       ├── __init__.py
│       ├── findings.py             # Finding/Issue model
│       ├── file_meta.py           # File metadata
│       ├── scan_context.py        # Scan context/state
│       └── rule.py                # Rule definition model
│
├── plugins/                       # User extensions
│   ├── __init__.py
│   ├── base_plugin.py             # Plugin interface
│   ├── custom_rules/              # User-defined rules
│   └── extensions/                # Third-party integrations
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_js_analyzer.py
│   │   ├── test_secrets_detector.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_full_scan.py
│   │   └── test_collectors.py
│   ├── fixtures/
│   │   ├── vulnerable_code/
│   │   ├── clean_code/
│   │   └── test_configs/
│   └── conftest.py                # Pytest fixtures
│
├── docs/
│   ├── api/
│   ├── rules/
│   ├── plugins/
│   └── getting_started.md
│
├── examples/
│   ├── configs/
│   │   ├── basic_config.yaml
│   │   └── advanced_config.yaml
│   ├── plugins/
│   │   └── custom_detector.py
│   └── sample_reports/
│
├── scripts/                       # Utility scripts
│   ├── setup.py                   # Installation script
│   ├── update_rules.py            # Rule updater
│   └── benchmark.py               # Performance testing
│
├── data/                          # Persistent data
│   ├── cache/
│   ├── signatures/                # Rule signatures
│   └── wordlists/                 # For fuzzing/bruteforce
│
├── reports/                       # Generated reports (gitignored)
├── logs/                          # Log files (gitignored)
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt           # Development dependencies
├── pyproject.toml                 # Modern Python project config
├── .env.example                   # Environment variables template
├── .gitignore
├── Makefile                       # Common commands
├── CHANGELOG.md
└── README.md