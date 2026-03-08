# Collectors Module Documentation

The collectors module is responsible for gathering files from various sources and organizing them into a structured directory format. It supports multiple collection strategies to fetch source code and related files from different locations.

## Overview

The collectors module provides a unified interface for collecting files from:
- **Local Filesystem** - Collect from local directories and files
- **Web Sources** - Crawl websites and extract files
- **GitHub** - Download files from GitHub repositories
- **Git Repositories** - Collect from local Git repositories

## Architecture

### Base Collector (`base_collector.py`)

The `BaseCollector` class defines the interface that all collectors must implement:

```python
class BaseCollector(ABC):
    @abstractmethod
    def collect(self) -> CollectionResult:
        """Collect files from the source."""
        pass
```

**Key Features:**
- Extensible file extension filtering
- Configurable depth limits
- Pattern-based file ignoring
- Multiple organization strategies (by extension, language, or type)
- Comprehensive error handling

**Supported File Extensions:**
- JavaScript: `.js`, `.jsx`, `.ts`, `.tsx`
- Python: `.py`
- PHP: `.php`, `.phtml`
- HTML/Templates: `.html`, `.htm`, `.vue`, `.svelte`
- Stylesheets: `.css`, `.scss`, `.less`
- Config: `.json`, `.yaml`, `.yml`, `.toml`, `.xml`
- And more...

### Collection Types

#### 1. FileCollector (`file_collector.py`)

Collect files from the local filesystem.

**Features:**
- Recursive and non-recursive directory traversal
- Symlink handling options
- Depth-based limiting
- Pattern-based exclusion

**Example:**
```python
from pathlib import Path
from src.collectors.file_collector import FileCollector

collector = FileCollector(
    source_path=Path('./src'),
    output_dir=Path('./collected/local'),
    extensions={'.js', '.py', '.php'},
    recursive=True,
    max_depth=10,
)

result = collector.collect()
print(f"Collected {result.total_files} files")
```

#### 2. WebCrawler (`web_crawler.py`)

Crawl websites and collect source files via HTTP requests.

**Features:**
- Domain-restricted crawling
- Depth-based link following
- Configurable page limits
- User-agent spoofing
- HTML link extraction

**Example:**
```python
from pathlib import Path
from src.collectors.web_crawler import WebCrawler

crawler = WebCrawler(
    start_url='https://example.com',
    output_dir=Path('./collected/web'),
    max_depth=2,
    max_pages=50,
)

result = crawler.collect()
```

#### 3. GitHubScraper (`github_scraper.py`)

Download files from GitHub repositories using the GitHub API.

**Features:**
- GitHub API integration
- Branch selection
- Token-based authentication for private repos
- Recursive tree traversal
- Rate limit awareness

**Example:**
```python
from pathlib import Path
from src.collectors.github_scraper import GitHubScraper

scraper = GitHubScraper(
    repo_url='https://github.com/owner/repo',
    output_dir=Path('./collected/github'),
    branch='main',
    # access_token='your_github_token',  # For private repos
)

result = scraper.collect()
```

#### 4. GitCollector (`git_collector.py`)

Collect files from local Git repositories.

**Features:**
- Git command-based file listing
- Branch/commit selection
- Uncommitted file detection
- Efficient file tracking

**Example:**
```python
from pathlib import Path
from src.collectors.git_collector import GitCollector

collector = GitCollector(
    repo_path=Path('./'),
    output_dir=Path('./collected/git'),
    branch='main',
    include_uncommitted=True,
)

result = collector.collect()
```

### CollectorOrchestrator (`orchestrator.py`)

The `CollectorOrchestrator` manages multiple collectors and coordinates file collection from various sources.

**Features:**
- Unified interface for all collectors
- Summary reporting
- Result tracking
- Batch operations

**Example:**
```python
from pathlib import Path
from src.collectors.orchestrator import CollectorOrchestrator

orchestrator = CollectorOrchestrator(
    output_base_dir=Path('./all_collected')
)

# Collect from multiple sources
local_result = orchestrator.collect_from_local_path(
    source_path=Path('./src')
)

github_result = orchestrator.collect_from_github(
    repo_url='https://github.com/owner/repo'
)

git_result = orchestrator.collect_from_git(
    repo_path=Path('./')
)

# Print summary
orchestrator.print_summary()
```

## Organization Strategies

Collected files can be organized in different ways:

### By Extension (Default)
```
collected_files/
├── javascript/
│   ├── app.js
│   └── utils.ts
├── python/
│   └── script.py
└── html/
    └── index.html
```

### By Language
```
collected_files/
├── js/
│   ├── app.js
│   └── utils.ts
├── python/
│   └── script.py
└── markup/
    └── index.html
```

### By Type
```
collected_files/
├── source/
│   ├── app.js
│   └── script.py
├── config/
│   ├── .env
│   └── settings.json
└── tests/
    └── test_app.js
```

## Data Models

### CollectionResult

Result of a collection operation:

```python
@dataclass
class CollectionResult:
    source: str                  # Source description
    collected_files: List[Path]  # Files collected
    organized_dir: Path          # Organization directory
    file_types: Set[str]         # File type extensions
    total_files: int             # Number of files
    total_size_bytes: int        # Total size
    errors: List[str]            # Any errors
    
    def summary(self) -> str:
        """Get human-readable summary."""
```

## Configuration Options

### Common Options (All Collectors)

- `output_dir` (Path): Directory to organize files
- `extensions` (Set[str]): File extensions to collect (default: all source types)
- `max_depth` (int): Maximum directory/traversal depth
- `ignore_patterns` (List[str]): Glob patterns to ignore

### Source-Specific Options

**FileCollector:**
- `source_path` (Path): Source directory/file
- `recursive` (bool): Recursively search subdirectories
- `follow_symlinks` (bool): Follow symbolic links

**WebCrawler:**
- `start_url` (str): Starting URL
- `max_pages` (int): Maximum pages to crawl
- `user_agent` (str): Custom user agent
- `timeout` (int): Request timeout in seconds

**GitHubScraper:**
- `repo_url` (str): GitHub repository URL
- `branch` (str): Branch to collect from
- `access_token` (str): GitHub API token (for private repos)

**GitCollector:**
- `repo_path` (Path): Path to Git repository
- `branch` (str): Git branch/commit
- `include_uncommitted` (bool): Include uncommitted changes

## Usage Examples

### Example 1: Collect from Local Project

```python
from pathlib import Path
from src.collectors.orchestrator import CollectorOrchestrator

orchestrator = CollectorOrchestrator(
    output_base_dir=Path('./project_scan')
)

result = orchestrator.collect_from_local_path(
    source_path=Path('./my_project'),
    recursive=True,
)

print(result.summary())
# Output:
# Source: /path/to/my_project
# Total Files: 156
# File Types: .js, .jsx, .py, .html, .css, .json
# Total Size: 12.34 MB
# Organized in: ./project_scan/local/my_project
```

### Example 2: Analyze Security Scanner Repository

```python
# Collect source files from the current project
orchestrator = CollectorOrchestrator(
    output_base_dir=Path('./scanner_analysis')
)

result = orchestrator.collect_from_local_path(
    source_path=Path('./src'),
    extensions={'.js', '.py', '.php', '.html'},
)

# Later, these organized files can be passed to the security scanner
scanner.scan_directory(result.organized_dir)
```

### Example 3: Collect from Multiple Sources

```python
orchestrator = CollectorOrchestrator(
    output_base_dir=Path('./multi_source_scan')
)

sources = [
    Path('./local_project'),
    Path('/path/to/another/project'),
]

for source in sources:
    orchestrator.collect_from_local_path(source_path=source)

orchestrator.print_summary()
```

### Example 4: Integration with Security Scanner

```python
from src.collectors.orchestrator import CollectorOrchestrator
from src.engine.orchestrator import ScanOrchestrator

# Collect files
collector = CollectorOrchestrator(
    output_base_dir=Path('./collected')
)

collection_result = collector.collect_from_local_path(
    source_path=Path('./target_project')
)

# Scan collected files
scanner = ScanOrchestrator()
scan_result = scanner.scan_directory(
    target=collection_result.organized_dir,
    output_format='html'
)

print(f"Collection: {collection_result.total_files} files")
print(f"Scan Results: {len(scan_result.findings)} issues found")
```

## Error Handling

Collectors handle various errors gracefully:

- **File Not Found**: Logged and skipped
- **Permission Errors**: Logged and continued
- **Network Errors**: Retry logic with timeout
- **Git Errors**: Fallback to alternative methods
- **Parse Errors**: Logged, analysis continues

All errors are collected in `CollectionResult.errors` for review.

## Performance Considerations

1. **Depth Limiting**: Use `max_depth` to prevent unnecessary deep traversal
2. **Extension Filtering**: Specify exact extensions to avoid processing unnecessary files
3. **Ignore Patterns**: Use patterns to skip common non-essential directories (node_modules, .git, etc.)
4. **Web Crawling**: Limit `max_pages` and `max_depth` for large websites
5. **GitHub API**: Use access tokens to increase rate limits

## Security Considerations

1. **File Access**: Ensure read permissions on source files/directories
2. **Network**: WebCrawler respects domain restrictions
3. **API Tokens**: GitHub tokens should be kept secure and not committed
4. **Symbolic Links**: Option to disable to prevent directory traversal attacks
5. **File Size**: Collectors should have size limits for large files

## Integration with Scanner

The collectors provide pre-organized files for the security scanner:

```python
# Collectors organize files...
result = orchestrator.collect_from_local_path(source_path)

# Scanner processes organized files...
scanner = ScanOrchestrator()
findings = scanner.scan_directory(
    target=result.organized_dir,  # Pre-organized files
)
```

This creates a clean pipeline: **Collection → Organization → Analysis**

## Extending Collectors

To create a custom collector:

```python
from src.collectors.base_collector import BaseCollector, CollectionResult

class S3Collector(BaseCollector):
    """Collect from AWS S3 buckets."""
    
    def collect(self) -> CollectionResult:
        # Implement S3 file listing
        files = self._list_s3_files()
        # Organize and return
        return self.organize_files(
            files=files,
            source_description=self.bucket_name,
        )
```

See the implementation of existing collectors for detailed patterns.
