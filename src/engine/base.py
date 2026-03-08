"""
Base classes for engine components.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from models.finding import Finding
from models.scan_context import ScanContext
from models.file_meta import FileMetadata


class BaseCollector(ABC):
    """Abstract base class for file collectors."""
    
    @abstractmethod
    def collect(self, context: ScanContext) -> List[Path]:
        """
        Collect files to be scanned.
        Returns list of file paths.
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get collector name."""
        pass


class BaseAnalyzer(ABC):
    """Abstract base class for analyzers."""
    
    @abstractmethod
    def analyze(self, file_path: Path, context: ScanContext) -> List[Finding]:
        """
        Analyze a file for security issues.
        Returns list of findings.
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get analyzer name."""
        pass
    
    @abstractmethod
    def supports_file(self, file_path: Path, metadata: FileMetadata) -> bool:
        """Check if analyzer supports this file type."""
        pass


class BaseProcessor(ABC):
    """Abstract base class for processors (pre/post processing)."""
    
    @abstractmethod
    def process(self, content: str, context: ScanContext) -> str:
        """Process file content."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get processor name."""
        pass


class BaseDetector(ABC):
    """Abstract base class for detectors."""
    
    @abstractmethod
    def detect(self, content: str, file_path: Path, context: ScanContext) -> List[Finding]:
        """Detect issues in content."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get detector name."""
        pass
