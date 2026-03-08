"""
Collectors Quick Start Guide
"""

# QUICK START EXAMPLES

# 1. Collect from local filesystem
from pathlib import Path
from src.collectors.file_collector import FileCollector

collector = FileCollector(
    source_path=Path('./my_project'),
    output_dir=Path('./collected'),
)
result = collector.collect()


# 2. Use the orchestrator for simplicity
from src.collectors.orchestrator import CollectorOrchestrator

orchestrator = CollectorOrchestrator(Path('./collections'))

# Collect from local
result = orchestrator.collect_from_local_path(Path('./src'))

# Collect from GitHub
result = orchestrator.collect_from_github(
    'https://github.com/owner/repo'
)

# Collect from Git repository
result = orchestrator.collect_from_git(Path('./'))

# Collect from website
result = orchestrator.collect_from_web('https://example.com')

# Print summary
orchestrator.print_summary()


# 3. Detailed configuration
from src.collectors.web_crawler import WebCrawler

crawler = WebCrawler(
    start_url='https://example.com',
    output_dir=Path('./web_files'),
    extensions={'.js', '.html', '.json'},
    max_depth=3,
    max_pages=50,
)
result = crawler.collect()


# 4. GitHub with private repository access
from src.collectors.github_scraper import GitHubScraper

scraper = GitHubScraper(
    repo_url='https://github.com/owner/private-repo',
    output_dir=Path('./github_files'),
    branch='develop',
    access_token='ghp_xxxxxxxxxxxxxxxxxxxx',  # GitHub personal access token
)
result = scraper.collect()


# 5. Git with uncommitted changes
from src.collectors.git_collector import GitCollector

collector = GitCollector(
    repo_path=Path('./'),
    output_dir=Path('./git_files'),
    branch='HEAD',
    include_uncommitted=True,
)
result = collector.collect()


# ORGANIZE FILES BY DIFFERENT STRATEGIES

# Strategy 1: By File Extension (default)
# javascript/, python/, html/, config/, etc.
collector.organize_files(files, organize_by='extension')

# Strategy 2: By Programming Language
# js/, python/, markup/, styling/, etc.
collector.organize_files(files, organize_by='language')

# Strategy 3: By File Type/Purpose
# source/, config/, tests/, dependencies/, etc.
collector.organize_files(files, organize_by='type')


# FILTERING AND CONFIGURATION

# Collect only specific extensions
result = orchestrator.collect_from_local_path(
    source_path=Path('./src'),
    extensions={'.js', '.py'},  # Only JavaScript and Python
)

# Ignore specific patterns
result = orchestrator.collect_from_local_path(
    source_path=Path('./src'),
    ignore_patterns=[
        '**/.git/**',
        '**/node_modules/**',
        '**/__pycache__/**',
        '**/*.min.js',
    ]
)

# Limit depth and recursion
from src.collectors.file_collector import FileCollector

collector = FileCollector(
    source_path=Path('./src'),
    output_dir=Path('./collected'),
    max_depth=5,  # Only 5 levels deep
    recursive=True,  # Recurse into subdirectories
)


# RESULT HANDLING

result = orchestrator.collect_from_local_path(Path('./src'))

# Check collection results
print(f"Files collected: {result.total_files}")
print(f"File types: {result.file_types}")
print(f"Total size: {result.total_size_bytes / 1024 / 1024:.2f} MB")
print(f"Organized in: {result.organized_dir}")
print(f"Errors: {result.errors}")

# Get human-readable summary
print(result.summary())

# Get orchestrator summary
summary = orchestrator.get_results_summary()
print(f"Total sources: {summary['total_sources']}")
print(f"Total files: {summary['total_files_collected']}")
print(f"All file types: {summary['all_file_types']}")


# INTEGRATION WITH SCANNER

from src.engine.orchestrator import ScanOrchestrator

# 1. Collect files
orchestrator = CollectorOrchestrator(Path('./temp_collections'))
collection_result = orchestrator.collect_from_local_path(Path('./target'))

# 2. Scan the organized files
scanner = ScanOrchestrator()
findings = scanner.scan_directory(
    target=collection_result.organized_dir,
)

# 3. Generate report
findings.generate_html_report('report.html')


# FILE ORGANIZATION EXAMPLES

# Before collection:
# project/
# ├── src/
# │   ├── app.js
# │   ├── utils.ts
# │   └── styles/
# │       └── main.css
# ├── tests/
# │   ├── app.test.js
# │   └── utils.test.js
# └── config.json

# After collection (by extension):
# collected/
# ├── javascript/
# │   ├── app.js
# │   ├── utils.ts (renamed to utils_1.ts if conflict)
# │   └── app.test.js
# ├── stylesheets/
# │   └── main.css
# └── config/
#     └── config.json

# After collection (by language):
# collected/
# ├── js/
# │   ├── app.js
# │   ├── utils.ts
# │   └── app.test.js
# ├── styling/
# │   └── main.css
# └── (other types in separate dirs)

# After collection (by type):
# collected/
# ├── source/
# │   ├── app.js
# │   ├── utils.ts
# │   └── main.css
# ├── config/
# │   └── config.json
# └── tests/
#     └── app.test.js
