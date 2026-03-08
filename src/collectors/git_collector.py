"""
Git repository collector - gathers files from local Git repositories.
"""

from pathlib import Path
from typing import List, Optional, Set
import logging
import subprocess

from .base_collector import BaseCollector, CollectionResult


logger = logging.getLogger(__name__)


class GitCollector(BaseCollector):
    """Collect files from Git repositories."""
    
    def __init__(
        self,
        repo_path: Path,
        output_dir: Path,
        extensions: Optional[Set[str]] = None,
        branch: str = 'HEAD',
        include_uncommitted: bool = False,
        max_depth: int = 10,
        ignore_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize Git collector.
        
        Args:
            repo_path: Path to Git repository
            output_dir: Directory to organize collected files
            extensions: File extensions to collect
            branch: Git branch to collect from
            include_uncommitted: Include uncommitted changes
            max_depth: Maximum directory depth
            ignore_patterns: Glob patterns to ignore
        """
        super().__init__(
            output_dir=output_dir,
            extensions=extensions,
            max_depth=max_depth,
            ignore_patterns=ignore_patterns,
        )
        
        self.repo_path = Path(repo_path)
        self.branch = branch
        self.include_uncommitted = include_uncommitted
        
        if not (self.repo_path / '.git').exists():
            raise ValueError(f"Not a Git repository: {repo_path}")
        
        logger.info(f"GitCollector initialized for {repo_path}")
    
    def collect(self) -> CollectionResult:
        """
        Collect files from Git repository.
        
        Returns:
            CollectionResult with collected files
        """
        logger.info(f"Starting Git collection from {self.repo_path}")
        
        files = self._collect_from_git()
        
        logger.info(f"Collected {len(files)} files from Git")
        
        return self.organize_files(
            files=files,
            source_description=str(self.repo_path),
            organize_by='extension'
        )
    
    def _collect_from_git(self) -> List[Path]:
        """Collect files from Git repository."""
        files = []
        
        try:
            # Get list of files from Git
            if self.include_uncommitted:
                # Include both tracked and untracked files
                cmd = ['git', 'status', '--porcelain']
                result = subprocess.run(
                    cmd,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                # Parse git status output
                for line in result.stdout.strip().split('\n'):
                    if line:
                        file_path = Path(line[3:].strip())
                        if file_path.exists():
                            files.append(self.repo_path / file_path)
            
            # Get committed files
            cmd = ['git', 'ls-tree', '-r', '--name-only', self.branch]
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                logger.error(f"Git command failed: {result.stderr}")
                return files
            
            # Process files
            for file_path_str in result.stdout.strip().split('\n'):
                if file_path_str:
                    file_path = self.repo_path / file_path_str
                    
                    # Check depth
                    try:
                        depth = len(file_path.relative_to(self.repo_path).parts)
                        if depth > self.max_depth:
                            continue
                    except ValueError:
                        continue
                    
                    # Check extension and add if valid
                    if self.is_valid_extension(file_path):
                        files.append(file_path)
                        logger.debug(f"Found Git file: {file_path_str}")
            
        except subprocess.TimeoutExpired:
            logger.error("Git command timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command error: {e}")
        except Exception as e:
            logger.error(f"Error collecting from Git: {e}")
        
        return files
