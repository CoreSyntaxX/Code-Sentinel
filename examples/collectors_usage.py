"""
Example usage of the collectors module.
"""

from pathlib import Path
from src.collectors.orchestrator import CollectorOrchestrator


def example_local_collection():
    """Example: Collect from local filesystem."""
    orchestrator = CollectorOrchestrator(output_base_dir=Path('./collected_files'))
    
    # Collect from local directory
    result = orchestrator.collect_from_local_path(
        source_path=Path('./test_project'),
        recursive=True,
    )
    
    print(f"Collected {result.total_files} files")
    print(f"Organized in: {result.organized_dir}")


def example_multiple_sources():
    """Example: Collect from multiple sources."""
    orchestrator = CollectorOrchestrator(output_base_dir=Path('./all_collected'))
    
    # Collect from local files
    local_result = orchestrator.collect_from_local_path(
        source_path=Path('./src'),
    )
    
    # Collect from Git repository
    try:
        git_result = orchestrator.collect_from_git(
            repo_path=Path('.'),
        )
    except Exception as e:
        print(f"Git collection failed: {e}")
    
    # Print summary
    orchestrator.print_summary()


def example_github_collection():
    """Example: Collect from GitHub repository."""
    orchestrator = CollectorOrchestrator(output_base_dir=Path('./github_files'))
    
    # Collect from GitHub (requires internet)
    # Note: This is a public repository, so no token needed
    try:
        result = orchestrator.collect_from_github(
            repo_url='https://github.com/torvalds/linux',
            branch='master',
            # You can provide access_token for private repos
            # access_token='your_github_token',
        )
        orchestrator.print_summary()
    except Exception as e:
        print(f"GitHub collection failed: {e}")


def example_web_crawl():
    """Example: Crawl a website."""
    orchestrator = CollectorOrchestrator(output_base_dir=Path('./web_files'))
    
    # Crawl a website (requires internet)
    try:
        result = orchestrator.collect_from_web(
            start_url='http://example.com',
            max_depth=2,
            max_pages=20,
        )
        orchestrator.print_summary()
    except Exception as e:
        print(f"Web crawl failed: {e}")


if __name__ == '__main__':
    print("Running example: Local Collection")
    example_local_collection()
    
    # Uncomment to run other examples
    # print("\nRunning example: Multiple Sources")
    # example_multiple_sources()
    
    # print("\nRunning example: GitHub Collection (requires internet)")
    # example_github_collection()
    
    # print("\nRunning example: Web Crawl (requires internet)")
    # example_web_crawl()
