"""
Base collector abstract class - defines the collector interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """Result of a collection operation."""
    source: str  # Source description (URL, path, repo, etc.)
    collected_files: List[Path]  # Files collected
    organized_dir: Path  # Directory where files are organized
    file_types: Set[str]  # File types collected
    total_files: int
    total_size_bytes: int
    errors: List[str]  # Any errors that occurred
    
    def summary(self) -> str:
        """Return a summary of the collection result."""
        return (
            f"Source: {self.source}\n"
            f"Total Files: {self.total_files}\n"
            f"File Types: {', '.join(sorted(self.file_types))}\n"
            f"Total Size: {self.total_size_bytes / 1024 / 1024:.2f} MB\n"
            f"Organized in: {self.organized_dir}\n"
            f"Errors: {len(self.errors)}"
        )


class BaseCollector(ABC):
    """Abstract base class for all collectors."""
    
    # Default file extensions to collect
    DEFAULT_EXTENSIONS = {
        '.js', '.jsx', '.ts', '.tsx',  # JavaScript/TypeScript
        '.py',  # Python
        '.php', '.phtml',  # PHP
        '.html', '.htm', '.vue', '.svelte',  # HTML/Template
        '.css', '.scss', '.less',  # Stylesheets
        '.json', '.yaml', '.yml', '.toml', '.xml',  # Config
        '.java', '.class',  # Java
        '.cpp', '.c', '.h', '.hpp',  # C/C++
        '.go',  # Go
        '.rs',  # Rust
        '.rb',  # Ruby
    }
    
    def __init__(
        self,
        output_dir: Path,
        extensions: Optional[Set[str]] = None,
        max_depth: int = 10,
        follow_symlinks: bool = False,
        ignore_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize the collector.
        
        Args:
            output_dir: Directory to organize collected files
            extensions: File extensions to collect (default to DEFAULT_EXTENSIONS)
            max_depth: Maximum directory depth to traverse
            follow_symlinks: Whether to follow symbolic links
            ignore_patterns: Glob patterns to ignore
        """
        self.output_dir = Path(output_dir)
        self.extensions = extensions or self.DEFAULT_EXTENSIONS
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks
        self.ignore_patterns = ignore_patterns or []
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Collector initialized with output: {self.output_dir}")
    
    @abstractmethod
    def collect(self) -> CollectionResult:
        """
        Collect files from the source.
        
        Returns:
            CollectionResult with collected files and organization info
        """
        pass
    
    def organize_files(
        self,
        files: List[Path],
        source_description: str,
        organize_by: str = 'extension'
    ) -> CollectionResult:
        """
        Organize collected files into directories.
        
        Args:
            files: List of file paths to organize
            source_description: Description of the source
            organize_by: How to organize ('extension', 'language', or 'type')
        
        Returns:
            CollectionResult with organization information
        """
        errors = []
        file_types = set()
        total_size = 0
        organized_files = []
        
        for file_path in files:
            try:
                # Skip non-existent files
                if not file_path.exists():
                    errors.append(f"File not found: {file_path}")
                    continue
                
                # Determine destination directory
                if organize_by == 'extension':
                    dest_subdir = self._get_extension_category(file_path)
                elif organize_by == 'language':
                    dest_subdir = self._get_language_category(file_path)
                else:
                    dest_subdir = self._get_type_category(file_path)
                
                # Create destination directory
                dest_dir = self.output_dir / dest_subdir
                dest_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                dest_file = dest_dir / file_path.name
                
                # Handle file name conflicts
                if dest_file.exists():
                    counter = 1
                    stem = file_path.stem
                    suffix = file_path.suffix
                    while dest_file.exists():
                        dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                
                # Copy the file
                with open(file_path, 'rb') as src:
                    with open(dest_file, 'wb') as dst:
                        dst.write(src.read())
                
                organized_files.append(dest_file)
                file_types.add(file_path.suffix.lower() or 'no-extension')
                total_size += file_path.stat().st_size
                
                logger.debug(f"Organized: {file_path} -> {dest_file}")
                
            except Exception as e:
                errors.append(f"Error organizing {file_path}: {str(e)}")
                logger.error(f"Error organizing file: {e}")
        
        return CollectionResult(
            source=source_description,
            collected_files=organized_files,
            organized_dir=self.output_dir,
            file_types=file_types,
            total_files=len(organized_files),
            total_size_bytes=total_size,
            errors=errors,
        )
    
    @staticmethod
    def _get_extension_category(file_path: Path) -> str:
        """Categorize file by extension."""
        ext = file_path.suffix.lower()
        
        categories = {
            '.js': 'javascript', '.jsx': 'javascript', '.ts': 'javascript', '.tsx': 'javascript',
            '.py': 'python',
            '.php': 'php', '.phtml': 'php',
            '.html': 'html', '.htm': 'html', '.vue': 'html', '.svelte': 'html',
            '.css': 'stylesheets', '.scss': 'stylesheets', '.less': 'stylesheets',
            '.json': 'config', '.yaml': 'config', '.yml': 'config', '.toml': 'config', '.xml': 'config',
            '.java': 'java', '.class': 'java',
            '.cpp': 'cpp', '.c': 'cpp', '.h': 'cpp', '.hpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
        }
        
        return categories.get(ext, 'other')
    
    @staticmethod
    def _get_language_category(file_path: Path) -> str:
        """Categorize file by programming language."""
        ext = file_path.suffix.lower()
        
        lang_map = {
            '.js': 'js', '.jsx': 'js', '.ts': 'js', '.tsx': 'js',
            '.py': 'python',
            '.php': 'php',
            '.html': 'markup', '.htm': 'markup', '.vue': 'markup', '.svelte': 'markup',
            '.css': 'styling', '.scss': 'styling', '.less': 'styling',
            '.java': 'java',
            '.cpp': 'cpp', '.c': 'cpp', '.h': 'cpp', '.hpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
        }
        
        return lang_map.get(ext, 'other')
    
    @staticmethod
    def _get_type_category(file_path: Path) -> str:
        """Categorize file by type (source, config, assets, etc.)."""
        name = file_path.name.lower()
        ext = file_path.suffix.lower()
        
        # Config files
        if any(x in name for x in ['config', '.env', 'settings', 'docker']):
            return 'config'
        
        # Test files
        if any(x in name for x in ['test', 'spec', 'mock']):
            return 'tests'
        
        # Package/dependency files
        if name in ['package.json', 'requirements.txt', 'composer.json', 'pom.xml']:
            return 'dependencies'
        
        # Stylesheets
        if ext in ['.css', '.scss', '.less']:
            return 'stylesheets'
        
        # Assets
        if ext in ['.png', '.jpg', '.gif', '.svg', '.ico', '.ttf', '.woff']:
            return 'assets'
        
        # Source code (default)
        return 'source'
    
    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored based on patterns."""
        for pattern in self.ignore_patterns:
            if path.match(pattern):
                return True
        return False
    
    def is_valid_extension(self, file_path: Path) -> bool:
        """Check if file has a valid extension."""
        return file_path.suffix.lower() in self.extensions
