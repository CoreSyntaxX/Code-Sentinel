"""
File metadata model - information about scanned files.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
import hashlib


@dataclass
class FileMetadata:
    """Metadata about a scanned file."""
    path: Path
    size_bytes: int
    extension: str
    mime_type: Optional[str] = None
    
    # Content analysis
    line_count: int = 0
    is_binary: bool = False
    is_minified: bool = False
    is_generated: bool = False
    
    # Security flags
    is_config_file: bool = False
    is_dependency_file: bool = False  # package.json, requirements.txt, etc.
    is_test_file: bool = False
    contains_secrets: bool = False
    
    # Hashes
    md5_hash: Optional[str] = None
    sha256_hash: Optional[str] = None
    
    # Language detection
    primary_language: Optional[str] = None
    frameworks: List[str] = field(default_factory=list)  # e.g., ["react", "express"]
    
    # Custom metadata
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate basic properties."""
        self.extension = self.path.suffix.lower()
        
        # Common config files
        config_files = {
            '.env', '.env.local', '.env.production',
            'config.json', 'settings.json', 'package.json',
            'composer.json', 'pom.xml', 'build.gradle',
            'dockerfile', '.dockerignore', '.gitignore',
        }
        
        self.is_config_file = self.path.name.lower() in config_files
        
        # Common dependency files
        dependency_files = {
            'package.json', 'package-lock.json', 'yarn.lock',
            'composer.json', 'composer.lock', 'requirements.txt',
            'pipfile', 'pipfile.lock', 'gemfile', 'gemfile.lock',
        }
        
        self.is_dependency_file = self.path.name.lower() in dependency_files
        
        # Test file patterns
        test_patterns = ['test_', '_test.', 'spec.', '.spec.']
        self.is_test_file = any(
            pattern in self.path.name.lower() for pattern in test_patterns
        )
    
    @classmethod
    def from_file(cls, file_path: Path) -> 'FileMetadata':
        """Create metadata from an actual file."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file size
        size = file_path.stat().st_size
        
        # Calculate hashes
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    md5.update(chunk)
                    sha256.update(chunk)
        except (IOError, OSError):
            # Can't read file, use empty hashes
            md5_hash = None
            sha256_hash = None
        else:
            md5_hash = md5.hexdigest()
            sha256_hash = sha256.hexdigest()
        
        return cls(
            path=file_path,
            size_bytes=size,
            extension=file_path.suffix.lower(),
            md5_hash=md5_hash,
            sha256_hash=sha256_hash,
        )
