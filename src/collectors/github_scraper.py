"""
GitHub scraper collector - gathers files from GitHub repositories.
"""

from pathlib import Path
from typing import List, Optional, Set
import logging
import json
from urllib.request import urlopen, Request
from urllib.error import URLError

from .base_collector import BaseCollector, CollectionResult


logger = logging.getLogger(__name__)


class GitHubScraper(BaseCollector):
    """Collect files from GitHub repositories."""
    
    def __init__(
        self,
        repo_url: str,
        output_dir: Path,
        extensions: Optional[Set[str]] = None,
        branch: str = 'main',
        access_token: Optional[str] = None,
        ignore_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize GitHub scraper.
        
        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo)
            output_dir: Directory to organize collected files
            extensions: File extensions to collect
            branch: Branch to scrape (default: main)
            access_token: GitHub API token for higher rate limits
            ignore_patterns: Glob patterns to ignore
        """
        super().__init__(
            output_dir=output_dir,
            extensions=extensions,
            max_depth=100,  # Large depth for deep repos
            ignore_patterns=ignore_patterns,
        )
        
        self.repo_url = repo_url
        self.branch = branch
        self.access_token = access_token
        
        # Parse repo URL
        parts = repo_url.rstrip('/').split('/')
        self.owner = parts[-2]
        self.repo = parts[-1].replace('.git', '')
        
        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        
        logger.info(f"GitHubScraper initialized for {self.owner}/{self.repo}")
    
    def collect(self) -> CollectionResult:
        """
        Collect files from GitHub repository.
        
        Returns:
            CollectionResult with collected files
        """
        logger.info(f"Starting GitHub collection from {self.repo_url}")
        
        files = self._collect_from_github()
        
        logger.info(f"Collected {len(files)} files from GitHub")
        
        return self.organize_files(
            files=files,
            source_description=self.repo_url,
            organize_by='extension'
        )
    
    def _collect_from_github(self) -> List[Path]:
        """Collect files from GitHub API."""
        files = []
        
        try:
            # Get repository tree
            tree_data = self._get_tree()
            
            if not tree_data:
                logger.warning("Could not fetch GitHub tree")
                return files
            
            # Process tree items
            for item in tree_data.get('tree', []):
                if item['type'] == 'blob':  # File
                    path = Path(item['path'])
                    
                    # Check if valid extension
                    if self.is_valid_extension(path):
                        # Download file
                        file_path = self._download_file(item)
                        if file_path:
                            files.append(file_path)
            
        except Exception as e:
            logger.error(f"Error collecting from GitHub: {e}")
        
        return files
    
    def _get_tree(self) -> Optional[dict]:
        """Get repository tree from GitHub API."""
        try:
            url = f"{self.api_base}/git/trees/{self.branch}?recursive=1"
            
            headers = {'User-Agent': 'GitHub-File-Collector'}
            if self.access_token:
                headers['Authorization'] = f'token {self.access_token}'
            
            req = Request(url, headers=headers)
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
                
        except Exception as e:
            logger.error(f"Error fetching GitHub tree: {e}")
            return None
    
    def _download_file(self, tree_item: dict) -> Optional[Path]:
        """Download a file from GitHub."""
        try:
            path = tree_item['path']
            sha = tree_item['sha']
            
            # Use raw content URL for faster downloads
            url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{self.branch}/{path}"
            
            req = Request(url, headers={'User-Agent': 'GitHub-File-Collector'})
            with urlopen(req, timeout=10) as response:
                content = response.read()
            
            # Save locally
            file_path = self.output_dir / Path(path).name
            
            # Handle conflicts
            counter = 1
            while file_path.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                file_path = self.output_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.debug(f"Downloaded: {path} -> {file_path}")
            return file_path
            
        except Exception as e:
            logger.debug(f"Error downloading file {tree_item.get('path')}: {e}")
            return None
