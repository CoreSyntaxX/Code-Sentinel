"""
Local filesystem collector - gathers files from local directories.
"""

from pathlib import Path
from typing import List, Optional, Set
import logging

from .base_collector import BaseCollector, CollectionResult


logger = logging.getLogger(__name__)


class FileCollector(BaseCollector):
    """Collect files from local filesystem."""
    
    def __init__(
        self,
        source_path: Path,
        output_dir: Path,
        extensions: Optional[Set[str]] = None,
        max_depth: int = 10,
        follow_symlinks: bool = False,
        ignore_patterns: Optional[List[str]] = None,
        recursive: bool = True,
    ):
        """
        Initialize file collector.
        
        Args:
            source_path: Source directory or file to collect from
            output_dir: Directory to organize collected files
            extensions: File extensions to collect
            max_depth: Maximum directory depth to traverse
            follow_symlinks: Whether to follow symbolic links
            ignore_patterns: Glob patterns to ignore
            recursive: Whether to recursively search subdirectories
        """
        super().__init__(
            output_dir=output_dir,
            extensions=extensions,
            max_depth=max_depth,
            follow_symlinks=follow_symlinks,
            ignore_patterns=ignore_patterns,
        )
        
        self.source_path = Path(source_path)
        self.recursive = recursive
        
        if not self.source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
        
        logger.info(f"FileCollector initialized with source: {source_path}")
    
    def collect(self) -> CollectionResult:
        """
        Collect files from the local filesystem.
        
        Returns:
            CollectionResult with collected files
        """
        logger.info(f"Starting collection from {self.source_path}")
        
        files = self._find_files()
        
        logger.info(f"Found {len(files)} files to process")
        
        return self.organize_files(
            files=files,
            source_description=str(self.source_path),
            organize_by='extension'
        )
    
    def _find_files(self) -> List[Path]:
        """Find all valid files in the source path."""
        files = []
        
        if self.source_path.is_file():
            # Single file
            if self.is_valid_extension(self.source_path):
                files.append(self.source_path)
            return files
        
        # Directory traversal
        if self.recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for item in self.source_path.glob(pattern):
            # Check depth
            try:
                depth = len(item.relative_to(self.source_path).parts)
                if depth > self.max_depth:
                    continue
            except ValueError:
                continue
            
            # Skip if should be ignored
            if self.should_ignore(item):
                logger.debug(f"Ignoring path: {item}")
                continue
            
            # Skip symlinks if not following them
            if item.is_symlink() and not self.follow_symlinks:
                logger.debug(f"Skipping symlink: {item}")
                continue
            
            # Check if valid file
            if item.is_file() and self.is_valid_extension(item):
                files.append(item)
                logger.debug(f"Found file: {item}")
        
        return files
