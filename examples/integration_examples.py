"""
Integration Example: Collectors + Security Scanner
Shows how to use collectors to gather files and then scan them with the security scanner.
"""

from pathlib import Path
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example 1: Simple Local Collection and Scan
def example_local_collection_and_scan():
    """
    Collect files from a local project and scan them.
    """
    print("\n" + "="*60)
    print("Example 1: Local Collection and Scan")
    print("="*60 + "\n")
    
    from src.collectors.orchestrator import CollectorOrchestrator
    from src.engine.orchestrator import ScanOrchestrator
    
    # Step 1: Collect files
    print("Step 1: Collecting files from local project...")
    collector = CollectorOrchestrator(
        output_base_dir=Path('./temp_collections/example1')
    )
    
    collection_result = collector.collect_from_local_path(
        source_path=Path('./test_project'),
        extensions={'.js', '.php', '.html'},
    )
    
    print(f"✓ Collected {collection_result.total_files} files")
    print(f"  Organized in: {collection_result.organized_dir}")
    
    # Step 2: Scan organized files
    print("\nStep 2: Scanning collected files...")
    try:
        scanner = ScanOrchestrator()
        scan_result = scanner.scan_directory(
            target=str(collection_result.organized_dir),
            output_format='json'
        )
        
        print(f"✓ Scan complete")
        print(f"  Issues found: {len(scan_result.findings)}")
        
    except Exception as e:
        print(f"✗ Scan failed: {e}")


# Example 2: Multi-Source Collection
def example_multi_source_collection():
    """
    Collect from multiple sources and analyze together.
    """
    print("\n" + "="*60)
    print("Example 2: Multi-Source Collection")
    print("="*60 + "\n")
    
    from src.collectors.orchestrator import CollectorOrchestrator
    
    orchestrator = CollectorOrchestrator(
        output_base_dir=Path('./temp_collections/example2')
    )
    
    # Collect from local project
    print("Collecting from local project...")
    local_result = orchestrator.collect_from_local_path(
        source_path=Path('./src'),
        extensions={'.js', '.py', '.php'},
    )
    print(f"✓ Local: {local_result.total_files} files")
    
    # Collect from test project
    print("Collecting from test project...")
    test_result = orchestrator.collect_from_local_path(
        source_path=Path('./test_project'),
        extensions={'.js', '.html'},
    )
    print(f"✓ Tests: {test_result.total_files} files")
    
    # Print summary
    print("\n" + "-"*60)
    orchestrator.print_summary()


# Example 3: GitHub Collection
def example_github_collection():
    """
    Collect from a GitHub repository.
    Note: This requires internet access.
    """
    print("\n" + "="*60)
    print("Example 3: GitHub Collection (Requires Internet)")
    print("="*60 + "\n")
    
    from src.collectors.orchestrator import CollectorOrchestrator
    
    orchestrator = CollectorOrchestrator(
        output_base_dir=Path('./temp_collections/example3')
    )
    
    # Example: Collect from a small public repo
    # This is just an example - you can use any public repo
    repo_url = 'https://github.com/lodash/lodash'
    
    print(f"Collecting from GitHub repository: {repo_url}")
    print("(This may take a while for large repositories...)\n")
    
    try:
        result = orchestrator.collect_from_github(
            repo_url=repo_url,
            branch='main',
            # Limit to smaller set for demo
        )
        print(f"✓ Collected {result.total_files} files")
        orchestrator.print_summary()
        
    except Exception as e:
        print(f"✗ GitHub collection failed: {e}")
        print("  Make sure you have internet access and valid GitHub URL")


# Example 4: Git Repository Collection
def example_git_collection():
    """
    Collect from the current Git repository.
    """
    print("\n" + "="*60)
    print("Example 4: Git Repository Collection")
    print("="*60 + "\n")
    
    from src.collectors.orchestrator import CollectorOrchestrator
    
    orchestrator = CollectorOrchestrator(
        output_base_dir=Path('./temp_collections/example4')
    )
    
    print("Collecting from current Git repository...")
    
    try:
        result = orchestrator.collect_from_git(
            repo_path=Path('./'),
            extensions={'.js', '.py', '.php', '.html', '.json', '.yaml'},
            include_uncommitted=True,
        )
        print(f"✓ Collected {result.total_files} files")
        orchestrator.print_summary()
        
    except ValueError as e:
        print(f"✗ Not a Git repository: {e}")
    except Exception as e:
        print(f"✗ Collection failed: {e}")


# Example 5: Web Crawling
def example_web_crawling():
    """
    Crawl a website and collect source files.
    Note: This requires internet access.
    """
    print("\n" + "="*60)
    print("Example 5: Web Crawling (Requires Internet)")
    print("="*60 + "\n")
    
    from src.collectors.orchestrator import CollectorOrchestrator
    
    orchestrator = CollectorOrchestrator(
        output_base_dir=Path('./temp_collections/example5')
    )
    
    start_url = 'https://example.com'
    
    print(f"Crawling website: {start_url}")
    print("(Limiting to 2 depth levels and 10 pages for demo...)\n")
    
    try:
        result = orchestrator.collect_from_web(
            start_url=start_url,
            max_depth=2,
            max_pages=10,
        )
        print(f"✓ Crawled and collected {result.total_files} files")
        orchestrator.print_summary()
        
    except Exception as e:
        print(f"✗ Web crawling failed: {e}")
        print("  Make sure you have internet access")


# Example 6: Selective Collection with Filters
def example_selective_collection():
    """
    Collect specific file types with filtering.
    """
    print("\n" + "="*60)
    print("Example 6: Selective Collection with Filters")
    print("="*60 + "\n")
    
    from src.collectors.orchestrator import CollectorOrchestrator
    
    orchestrator = CollectorOrchestrator(
        output_base_dir=Path('./temp_collections/example6')
    )
    
    # Only JavaScript files, ignore test files and minified code
    print("Collecting JavaScript files only (excluding tests and minified)...\n")
    
    result = orchestrator.collect_from_local_path(
        source_path=Path('./src'),
        extensions={'.js', '.jsx', '.ts', '.tsx'},
        ignore_patterns=[
            '**/test/**',
            '**/*.test.js',
            '**/*.spec.js',
            '**/*.min.js',
            '**/node_modules/**',
        ],
    )
    
    print(f"✓ Collected {result.total_files} files")
    print(f"  File types: {result.file_types}")
    print(f"  Organized in: {result.organized_dir}")
    
    # Print directory structure
    print("\nOrganized files:")
    org_dir = result.organized_dir
    if org_dir.exists():
        for item in org_dir.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(org_dir)
                print(f"  └─ {rel_path}")


# Example 7: Custom Analysis Pipeline
def example_custom_analysis_pipeline():
    """
    Advanced example: Collect, organize, and perform custom analysis.
    """
    print("\n" + "="*60)
    print("Example 7: Custom Analysis Pipeline")
    print("="*60 + "\n")
    
    from src.collectors.orchestrator import CollectorOrchestrator
    from pathlib import Path
    import os
    
    orchestrator = CollectorOrchestrator(
        output_base_dir=Path('./temp_collections/example7')
    )
    
    # Collect files
    print("Step 1: Collecting source files...")
    result = orchestrator.collect_from_local_path(
        source_path=Path('./src'),
        extensions={'.js', '.py', '.php'},
    )
    print(f"✓ Collected {result.total_files} files\n")
    
    # Analyze organized files
    print("Step 2: Analyzing organized files...")
    
    organized_dir = result.organized_dir
    stats = {
        'total_files': 0,
        'total_lines': 0,
        'by_type': {}
    }
    
    for file_path in organized_dir.rglob('*'):
        if file_path.is_file():
            stats['total_files'] += 1
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = len(f.readlines())
                    stats['total_lines'] += lines
                    
                    ext = file_path.suffix
                    if ext not in stats['by_type']:
                        stats['by_type'][ext] = {'count': 0, 'lines': 0}
                    stats['by_type'][ext]['count'] += 1
                    stats['by_type'][ext]['lines'] += lines
                    
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
    
    # Print analysis results
    print(f"✓ Analysis complete\n")
    print("Analysis Results:")
    print(f"  Total Files: {stats['total_files']}")
    print(f"  Total Lines of Code: {stats['total_lines']}")
    print("\n  By File Type:")
    
    for ext, info in sorted(stats['by_type'].items()):
        print(f"    {ext}: {info['count']} files, {info['lines']} lines")


# Main menu
def main():
    """Run example menu."""
    print("\n" + "="*60)
    print("Security Scanner - Collectors Integration Examples")
    print("="*60)
    print("\nAvailable Examples:")
    print("1. Local Collection and Scan")
    print("2. Multi-Source Collection")
    print("3. GitHub Collection (requires internet)")
    print("4. Git Repository Collection")
    print("5. Web Crawling (requires internet)")
    print("6. Selective Collection with Filters")
    print("7. Custom Analysis Pipeline")
    print("8. Run All Examples")
    print("0. Exit")
    
    choice = input("\nSelect example (0-8): ").strip()
    
    examples = {
        '1': example_local_collection_and_scan,
        '2': example_multi_source_collection,
        '3': example_github_collection,
        '4': example_git_collection,
        '5': example_web_crawling,
        '6': example_selective_collection,
        '7': example_custom_analysis_pipeline,
    }
    
    if choice == '8':
        # Run offline examples
        example_local_collection_and_scan()
        example_multi_source_collection()
        example_selective_collection()
        example_custom_analysis_pipeline()
        
        print("\n✓ All offline examples completed!")
        print("\nNote: Online examples (GitHub, Web) require internet access.")
        print("Run them individually from the menu above.")
        
    elif choice in examples:
        examples[choice]()
    elif choice != '0':
        print("✗ Invalid choice")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
