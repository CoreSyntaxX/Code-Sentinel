# Collectors Configuration Template

# This file provides example configurations for different collector scenarios

## Example 1: Basic Local Collection

```python
from pathlib import Path
from src.collectors.file_collector import FileCollector

config = {
    'source_path': Path('./my_project'),
    'output_dir': Path('./collections/my_project'),
    'extensions': {'.js', '.py', '.php', '.html'},
    'recursive': True,
    'max_depth': 10,
    'follow_symlinks': False,
    'ignore_patterns': [
        '**/node_modules/**',
        '**/.git/**',
        '**/__pycache__/**',
        '**/venv/**',
        '**/dist/**',
        '**/build/**',
    ]
}

collector = FileCollector(**config)
result = collector.collect()
```

## Example 2: Security Scan Configuration

```python
# Configuration for scanning source files for security issues

from pathlib import Path
from src.collectors.file_collector import FileCollector

# Collect all source code files
config = {
    'source_path': Path('./src'),
    'output_dir': Path('./security_scan/source'),
    'extensions': {
        # Web technologies
        '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss',
        # Backend
        '.py', '.php', '.java', '.go', '.rs', '.rb',
        # Config files
        '.json', '.yaml', '.yml', '.xml', '.toml', '.env',
    },
    'recursive': True,
    'ignore_patterns': [
        '**/node_modules/**',
        '**/venv/**',
        '**/.git/**',
        '**/dist/**',
        '**/__pycache__/**',
        '**/vendor/**',
        '**/target/**',
    ]
}

collector = FileCollector(**config)
result = collector.collect()

# Now scan with security scanner
# scanner.scan_directory(result.organized_dir)
```

## Example 3: GitHub Batch Collection

```python
# Collect multiple repositories from GitHub

from pathlib import Path
from src.collectors.orchestrator import CollectorOrchestrator

orchestrator = CollectorOrchestrator(
    output_base_dir=Path('./github_analysis')
)

repositories = [
    'https://github.com/facebook/react',
    'https://github.com/angular/angular',
    'https://github.com/vuejs/vue',
    'https://github.com/django/django',
]

for repo_url in repositories:
    try:
        result = orchestrator.collect_from_github(
            repo_url=repo_url,
            branch='main',
            access_token='your_github_token',  # Optional for higher rate limits
        )
        print(f"✓ Collected {result.total_files} files from {repo_url}")
    except Exception as e:
        print(f"✗ Error collecting {repo_url}: {e}")

orchestrator.print_summary()
```

## Example 4: Comprehensive Multi-Source Collection

```python
# Collect from all sources for comprehensive analysis

from pathlib import Path
from src.collectors.orchestrator import CollectorOrchestrator

def comprehensive_collection():
    orchestrator = CollectorOrchestrator(
        output_base_dir=Path('./comprehensive_scan')
    )
    
    # 1. Local projects
    local_projects = [
        Path('./project1'),
        Path('./project2'),
        Path('./project3'),
    ]
    
    for project_path in local_projects:
        try:
            result = orchestrator.collect_from_local_path(
                source_path=project_path,
                extensions={'.js', '.py', '.php'},
            )
            print(f"✓ Local: {result.total_files} files")
        except Exception as e:
            print(f"✗ Local error: {e}")
    
    # 2. Git repositories
    git_repos = [
        Path('./repo1'),
        Path('./repo2'),
    ]
    
    for repo_path in git_repos:
        try:
            result = orchestrator.collect_from_git(
                repo_path=repo_path,
                include_uncommitted=True,
            )
            print(f"✓ Git: {result.total_files} files")
        except Exception as e:
            print(f"✗ Git error: {e}")
    
    # 3. Print comprehensive summary
    orchestrator.print_summary()

comprehensive_collection()
```

## Example 5: Development Environment Collection

```python
# Collect source files for development/testing

from pathlib import Path
from src.collectors.file_collector import FileCollector

dev_config = {
    'source_path': Path('./src'),
    'output_dir': Path('./dev_analysis/source'),
    'extensions': {'.js', '.jsx', '.ts', '.tsx', '.py', '.json'},
    'ignore_patterns': [
        '**/.git/**',
        '**/node_modules/**',
        '**/__pycache__/**',
        '**/*.min.js',  # Skip minified files
        '**/dist/**',
        '**/build/**',
        '**/.next/**',
        '**/.nuxt/**',
    ]
}

collector = FileCollector(**dev_config)
result = collector.collect()

print(f"Collected {result.total_files} files for development analysis")
print(f"Organized in: {result.organized_dir}")
print(f"File types: {result.file_types}")
```

## Example 6: Production Code Analysis

```python
# Analyze only production code

from pathlib import Path
from src.collectors.file_collector import FileCollector

prod_config = {
    'source_path': Path('./src'),
    'output_dir': Path('./prod_analysis/source'),
    'extensions': {'.js', '.jsx', '.ts', '.tsx', '.py', '.php'},
    'ignore_patterns': [
        '**/test/**',
        '**/tests/**',
        '**/*.test.js',
        '**/*.test.ts',
        '**/*.spec.js',
        '**/*.spec.ts',
        '**/mock/**',
        '**/__mocks__/**',
        '**/fixtures/**',
        '**/examples/**',
    ]
}

collector = FileCollector(**prod_config)
result = collector.collect()

# Use for production security scanning
```

## Example 7: Configuration Files Collection

```python
# Collect only configuration files

from pathlib import Path
from src.collectors.file_collector import FileCollector

config_collector = FileCollector(
    source_path=Path('./'),
    output_dir=Path('./configs_analysis'),
    extensions={
        '.json', '.yaml', '.yml', '.xml', '.toml',
        '.env', '.env.example',
        '.htaccess', '.nginx', '.conf',
    },
    ignore_patterns=[
        '**/node_modules/**',
        '**/dist/**',
        '**/.git/**',
    ]
)

result = config_collector.collect()
print(f"Collected {result.total_files} configuration files")
```

## Example 8: API and Integration Collection

```python
# Use orchestrator with environment-based configuration

from pathlib import Path
from src.collectors.orchestrator import CollectorOrchestrator
import os

def api_based_collection():
    # Environment-based configuration
    github_token = os.getenv('GITHUB_TOKEN')
    base_output = Path(os.getenv('COLLECTION_OUTPUT', './collections'))
    
    orchestrator = CollectorOrchestrator(output_base_dir=base_output)
    
    # Collections configuration
    collections_config = [
        {
            'type': 'local',
            'path': './src',
            'extensions': {'.js', '.py'},
        },
        {
            'type': 'github',
            'repo': 'https://github.com/owner/repo',
            'token': github_token,
        },
        {
            'type': 'git',
            'path': './',
        },
    ]
    
    for config in collections_config:
        try:
            if config['type'] == 'local':
                orchestrator.collect_from_local_path(
                    source_path=Path(config['path']),
                    extensions=config.get('extensions'),
                )
            elif config['type'] == 'github':
                orchestrator.collect_from_github(
                    repo_url=config['repo'],
                    access_token=config.get('token'),
                )
            elif config['type'] == 'git':
                orchestrator.collect_from_git(repo_path=Path(config['path']))
        except Exception as e:
            print(f"Error in {config['type']}: {e}")
    
    return orchestrator

orchestrator = api_based_collection()
orchestrator.print_summary()
```

## Example 9: High-Performance Batch Collection

```python
# Optimized configuration for batch collection

from pathlib import Path
from src.collectors.file_collector import FileCollector

# Large project collection with optimization
batch_config = {
    'source_path': Path('./monorepo'),
    'output_dir': Path('./batch_analysis'),
    'extensions': {'.js', '.jsx', '.ts', '.tsx'},  # Fewer extensions = faster
    'max_depth': 5,  # Limit depth for speed
    'recursive': True,
    'ignore_patterns': [
        # Exclude common large directories
        '**/node_modules/**',
        '**/.next/**',
        '**/dist/**',
        '**/.git/**',
        '**/coverage/**',
        '**/build/**',
        # Exclude build artifacts
        '**/*.min.js',
        '**/*.min.css',
        # Exclude common non-essential directories
        '**/docs/**',
        '**/examples/**',
        '**/tests/**',
    ]
}

collector = FileCollector(**batch_config)
result = collector.collect()

print(f"Collected {result.total_files} files in {len(result.errors)} milliseconds")
```

## Example 10: Filtered Dependency Analysis

```python
# Collect only dependency/package files for analysis

from pathlib import Path
from src.collectors.file_collector import FileCollector

# Create custom extension set for dependencies
dependency_extensions = {
    # npm/yarn
    'package.json', 'package-lock.json', 'yarn.lock',
    # Python
    'requirements.txt', 'Pipfile', 'Pipfile.lock',
    # Composer (PHP)
    'composer.json', 'composer.lock',
    # Maven (Java)
    'pom.xml',
    # Gradle (Java)
    'build.gradle', 'build.gradle.kts',
    # Ruby
    'Gemfile', 'Gemfile.lock',
    # .NET
    'packages.config', '*.csproj',
}

# Note: FileCollector uses extensions, you may need to customize
# For dependency files, consider custom implementation
```

## Environment Variables Template

Create a `.env.collectors` file:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_API_RATE_LIMIT=true

# Collection Configuration
COLLECTOR_OUTPUT_DIR=./collections
COLLECTOR_MAX_DEPTH=10
COLLECTOR_TIMEOUT=30

# Logging
COLLECTOR_LOG_LEVEL=INFO
COLLECTOR_LOG_FILE=./logs/collector.log

# Web Crawler
WEB_CRAWLER_MAX_PAGES=100
WEB_CRAWLER_USER_AGENT=Mozilla/5.0

# Performance
COLLECTOR_PARALLEL_JOBS=4
COLLECTOR_CHUNK_SIZE=100
```

Usage:
```python
import os
from dotenv import load_dotenv

load_dotenv('.env.collectors')

github_token = os.getenv('GITHUB_TOKEN')
output_dir = os.getenv('COLLECTOR_OUTPUT_DIR', './collections')
```
