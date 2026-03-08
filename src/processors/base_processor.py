"""
Base processor class for code transformation and normalization.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any, List
import logging
import re

from models.scan_context import ScanContext


logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """
    Abstract base class for all processors.
    
    Processors transform or normalize code before analysis:
    - Beautify minified code
    - Normalize formatting
    - Remove comments
    - Deobfuscate code
    - Tokenize for analysis
    """
    
    def __init__(self):
        self.name = self.get_name()
        self.enabled = True
        
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of the processor."""
        pass
    
    @abstractmethod
    def process(self, content: str, context: ScanContext) -> str:
        """
        Process the content.
        
        Args:
            content: Input content to process
            context: Scan context
            
        Returns:
            Processed content
        """
        pass
    
    def should_process(self, content: str, file_path: Optional[str] = None) -> bool:
        """
        Check if processor should run on this content.
        Override in subclasses for conditional processing.
        """
        return self.enabled and bool(content.strip())
    
    def _detect_language(self, content: str, file_path: Optional[str] = None) -> str:
        """
        Detect programming language from content or file extension.
        
        Returns:
            Language code: 'javascript', 'php', 'html', 'python', etc.
        """
        if file_path:
            # Try to detect from file extension
            if file_path.endswith(('.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs')):
                return 'javascript'
            elif file_path.endswith(('.php', '.php3', '.php4', '.php5', '.php7', '.phtml')):
                return 'php'
            elif file_path.endswith(('.html', '.htm', '.xhtml')):
                return 'html'
            elif file_path.endswith('.py'):
                return 'python'
            elif file_path.endswith('.java'):
                return 'java'
            elif file_path.endswith('.go'):
                return 'go'
            elif file_path.endswith('.rb'):
                return 'ruby'
        
        # Detect from content heuristics
        content_lower = content.lower()
        
        # Check for PHP tags
        if '<?php' in content_lower or '<?=' in content_lower:
            return 'php'
        
        # Check for HTML tags
        if re.search(r'<html|<head|<body|<div|<p>', content_lower, re.IGNORECASE):
            return 'html'
        
        # Check for JavaScript patterns
        if re.search(r'function\s*\w*\s*\(|var\s+\w+|const\s+\w+|let\s+\w+', content):
            return 'javascript'
        
        # Check for Python patterns
        if re.search(r'def\s+\w+\s*\(|import\s+\w+|from\s+\w+', content):
            return 'python'
        
        return 'unknown'
    
    def _is_minified(self, content: str) -> bool:
        """
        Check if content appears to be minified.
        
        Heuristics:
        - Very long lines (> 500 chars)
        - Low comment ratio
        - High density of code
        - No whitespace between tokens
        """
        if not content:
            return False
        
        lines = content.split('\n')
        if not lines:
            return False
        
        # Check for very long lines
        long_lines = sum(1 for line in lines if len(line.strip()) > 500)
        if long_lines > len(lines) * 0.3:  # 30% of lines are very long
            return True
        
        # Check comment ratio
        comment_patterns = [
            r'//.*$',  # Single line comments
            r'#.*$',   # Hash comments
            r'/\*.*?\*/',  # Multi-line comments
            r'<!--.*?-->',  # HTML comments
        ]
        
        total_chars = len(content)
        comment_chars = 0
        
        for pattern in comment_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                comment_chars += len(match.group())
        
        comment_ratio = comment_chars / total_chars if total_chars > 0 else 0
        
        # Minified code usually has very few comments
        if comment_ratio < 0.01:  # Less than 1% comments
            return True
        
        # Check whitespace ratio
        whitespace_chars = sum(1 for c in content if c.isspace())
        whitespace_ratio = whitespace_chars / total_chars if total_chars > 0 else 0
        
        # Minified code has very little whitespace
        if whitespace_ratio < 0.1:  # Less than 10% whitespace
            return True
        
        return False
    
    def _normalize_line_endings(self, content: str) -> str:
        """Normalize line endings to \n."""
        return content.replace('\r\n', '\n').replace('\r', '\n')
    
    def _remove_bom(self, content: str) -> str:
        """Remove Byte Order Mark if present."""
        if content.startswith('\ufeff'):
            return content[1:]
        return content
