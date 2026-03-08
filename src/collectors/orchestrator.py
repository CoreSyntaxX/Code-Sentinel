"""
Collector orchestrator - manages and coordinates multiple collectors.
"""

from pathlib import Path
from typing import List, Dict, Optional, Set
from enum import Enum
import logging
import shutil

from .file_collector import FileCollector
from .web_crawler import WebCrawler
from .github_scraper import GitHubScraper
from .git_collector import GitCollector
from .base_collector import CollectionResult


logger = logging.getLogger(__name__)


class CollectorType(Enum):
    """Types of collectors available."""
    LOCAL_FILES = "local"
    WEB = "web"
    GITHUB = "github"
    GIT = "git"


class CollectorOrchestrator:
    """Orchestrate multiple file collectors."""
    
    def __init__(self, output_base_dir: Path):
        """
        Initialize collector orchestrator.
        
        Args:
            output_base_dir: Base directory for organizing all collections
        """
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        
        self.results: List[CollectionResult] = []
        
        logger.info(f"CollectorOrchestrator initialized with base dir: {output_base_dir}")
    
    def collect_from_local_path(
        self,
        source_path: Path,
        extensions: Optional[Set[str]] = None,
        recursive: bool = True,
        ignore_patterns: Optional[List[str]] = None,
    ) -> CollectionResult:
        """
        Collect files from local filesystem.
        
        Args:
            source_path: Source directory or file
            extensions: File extensions to collect
            recursive: Whether to recurse into subdirectories
            ignore_patterns: Patterns to ignore
        
        Returns:
            CollectionResult
        """
        output_dir = self.output_base_dir / "local" / source_path.name
        self._prepare_output_dir(output_dir)
        
        logger.info(f"Collecting from local path: {source_path}")
        
        collector = FileCollector(
            source_path=source_path,
            output_dir=output_dir,
            extensions=extensions,
            recursive=recursive,
            ignore_patterns=ignore_patterns,
        )
        
        result = collector.collect()
        self.results.append(result)
        
        logger.info(f"Collection complete: {result.summary()}")
        
        return result
    
    def collect_from_web(
        self,
        start_url: str,
        extensions: Optional[Set[str]] = None,
        max_depth: int = 3,
        max_pages: int = 100,
    ) -> CollectionResult:
        """
        Collect files from website.
        
        Args:
            start_url: Starting URL
            extensions: File extensions to collect
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
        
        Returns:
            CollectionResult
        """
        domain = start_url.split('/')[2].replace('www.', '')
        output_dir = self.output_base_dir / "web" / domain
        self._prepare_output_dir(output_dir)
        
        logger.info(f"Collecting from web: {start_url}")
        
        crawler = WebCrawler(
            start_url=start_url,
            output_dir=output_dir,
            extensions=extensions,
            max_depth=max_depth,
            max_pages=max_pages,
        )
        
        result = crawler.collect()
        self.results.append(result)
        
        logger.info(f"Web collection complete: {result.summary()}")
        
        return result
    
    def collect_from_github(
        self,
        repo_url: str,
        extensions: Optional[Set[str]] = None,
        branch: str = 'main',
        access_token: Optional[str] = None,
    ) -> CollectionResult:
        """
        Collect files from GitHub repository.
        
        Args:
            repo_url: GitHub repository URL
            extensions: File extensions to collect
            branch: Branch to collect from
            access_token: GitHub API token
        
        Returns:
            CollectionResult
        """
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        output_dir = self.output_base_dir / "github" / repo_name
        self._prepare_output_dir(output_dir)
        
        logger.info(f"Collecting from GitHub: {repo_url}")
        
        scraper = GitHubScraper(
            repo_url=repo_url,
            output_dir=output_dir,
            extensions=extensions,
            branch=branch,
            access_token=access_token,
        )
        
        result = scraper.collect()
        self.results.append(result)
        
        logger.info(f"GitHub collection complete: {result.summary()}")
        
        return result
    
    def collect_from_git(
        self,
        repo_path: Path,
        extensions: Optional[Set[str]] = None,
        branch: str = 'HEAD',
        include_uncommitted: bool = False,
    ) -> CollectionResult:
        """
        Collect files from local Git repository.
        
        Args:
            repo_path: Path to Git repository
            extensions: File extensions to collect
            branch: Branch to collect from
            include_uncommitted: Include uncommitted files
        
        Returns:
            CollectionResult
        """
        output_dir = self.output_base_dir / "git" / repo_path.name
        self._prepare_output_dir(output_dir)
        
        logger.info(f"Collecting from Git: {repo_path}")
        
        collector = GitCollector(
            repo_path=repo_path,
            output_dir=output_dir,
            extensions=extensions,
            branch=branch,
            include_uncommitted=include_uncommitted,
        )
        
        result = collector.collect()
        self.results.append(result)
        
        logger.info(f"Git collection complete: {result.summary()}")
        
        return result
    
    def get_results_summary(self) -> Dict:
        """Get summary of all collections."""
        return {
            'total_sources': len(self.results),
            'total_files_collected': sum(r.total_files for r in self.results),
            'total_size_bytes': sum(r.total_size_bytes for r in self.results),
            'all_file_types': set().union(*(r.file_types for r in self.results)),
            'total_errors': sum(len(r.errors) for r in self.results),
            'sources': [
                {
                    'source': r.source,
                    'files': r.total_files,
                    'size_mb': r.total_size_bytes / 1024 / 1024,
                    'types': list(r.file_types),
                }
                for r in self.results
            ]
        }
    
    def print_summary(self):
        """Print summary of all collections."""
        summary = self.get_results_summary()
        
        print("\n" + "="*60)
        print("COLLECTION SUMMARY")
        print("="*60)
        print(f"Total Sources: {summary['total_sources']}")
        print(f"Total Files Collected: {summary['total_files_collected']}")
        print(f"Total Size: {summary['total_size_bytes'] / 1024 / 1024 / 1024:.2f} GB")
        print(f"File Types: {', '.join(sorted(summary['all_file_types']))}")
        print(f"Errors: {summary['total_errors']}")
        print("\nDetailed Sources:")
        print("-"*60)
        
        for source_info in summary['sources']:
            print(f"  Source: {source_info['source']}")
            print(f"    Files: {source_info['files']}")
            print(f"    Size: {source_info['size_mb']:.2f} MB")
            print(f"    Types: {', '.join(source_info['types'])}")
        
        print("="*60 + "\n")

    def _prepare_output_dir(self, output_dir: Path):
        """Start each collection with a clean output directory."""
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True, exist_ok=True)
