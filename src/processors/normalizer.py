"""
Code normalizer - removes comments, standardizes formatting.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

from models.scan_context import ScanContext
from processors.base_processor import BaseProcessor


logger = logging.getLogger(__name__)


class CodeNormalizer(BaseProcessor):
    """
    Normalizes code by removing comments and standardizing formatting.
    Makes patterns easier to match.
    """
    
    def __init__(self):
        super().__init__()
        
        # Language-specific comment patterns
        self.comment_patterns = {
            'javascript': [
                (r'//.*$', re.MULTILINE),  # Single-line
                (r'/\*.*?\*/', re.DOTALL),  # Multi-line
            ],
            'php': [
                (r'//.*$', re.MULTILINE),  # Single-line
                (r'#.*$', re.MULTILINE),    # Hash comments
                (r'/\*.*?\*/', re.DOTALL),  # Multi-line
            ],
            'html': [
                (r'<!--.*?-->', re.DOTALL),  # HTML comments
                (r'//.*$', re.MULTILINE),    # JavaScript in HTML
                (r'/\*.*?\*/', re.DOTALL),   # CSS/JS in HTML
            ],
            'python': [
                (r'#.*$', re.MULTILINE),    # Single-line
                (r'""".*?"""', re.DOTALL),  # Multi-line (triple double)
                (r"'''.*?'''", re.DOTALL),  # Multi-line (triple single)
            ],
            'java': [
                (r'//.*$', re.MULTILINE),  # Single-line
                (r'/\*.*?\*/', re.DOTALL),  # Multi-line
                (r'/\*\*.*?\*/', re.DOTALL),  # Javadoc
            ],
            'generic': [
                (r'//.*$', re.MULTILINE),  # Single-line
                (r'#.*$', re.MULTILINE),    # Hash comments
                (r'/\*.*?\*/', re.DOTALL),  # Multi-line
                (r'<!--.*?-->', re.DOTALL), # HTML comments
            ],
        }
        
        # String patterns to preserve (so we don't remove comments inside strings)
        self.string_patterns = [
            (r'"(?:[^"\\]|\\.)*"', '"'),  # Double quotes
            (r"'(?:[^'\\]|\\.)*'", "'"),  # Single quotes
            (r'`(?:[^`\\]|\\.)*`', '`'),  # Backticks
        ]
    
    def get_name(self) -> str:
        return "CodeNormalizer"
    
    def process(self, content: str, context: ScanContext) -> str:
        """
        Normalize code by removing comments and standardizing.
        
        Args:
            content: Code content to normalize
            context: Scan context
            
        Returns:
            Normalized code
        """
        if not self.should_process(content):
            return content
        
        logger.debug(f"Normalizing code (length: {len(content)})")
        
        # Step 1: Remove BOM and normalize line endings
        normalized = self._remove_bom(content)
        normalized = self._normalize_line_endings(normalized)
        
        # Step 2: Detect language
        file_path = getattr(context, "current_file", None)
        file_path_str = str(file_path) if file_path else None
        language = self._detect_language(normalized, file_path=file_path_str)
        
        # Step 3: Protect strings before removing comments
        protected, replacements = self._protect_strings(normalized)
        
        # Step 4: Remove comments based on language
        comment_removed = self._remove_comments(protected, language)
        
        # Step 5: Restore protected strings
        result = self._restore_strings(comment_removed, replacements)
        
        # Step 6: Normalize whitespace (but be careful)
        result = self._normalize_whitespace(result)
        
        logger.debug(f"Normalized from {len(content)} to {len(result)} chars")
        return result
    
    def _protect_strings(self, content: str) -> Tuple[str, Dict[str, str]]:
        """
        Protect string literals by replacing them with placeholders.
        This prevents removing comments inside strings.
        
        Returns:
            Tuple of (protected_content, replacements_dict)
        """
        protected = content
        replacements = {}
        placeholder_template = "__STRING_{}__"
        counter = 0
        
        for pattern, quote_char in self.string_patterns:
            # Find all matches
            matches = list(re.finditer(pattern, protected, re.DOTALL))
            
            # Replace from end to beginning to preserve positions
            for match in reversed(matches):
                string_content = match.group()
                placeholder = placeholder_template.format(counter)
                replacements[placeholder] = string_content
                
                # Replace in content
                start, end = match.span()
                protected = protected[:start] + placeholder + protected[end:]
                counter += 1
        
        return protected, replacements
    
    def _remove_comments(self, content: str, language: str) -> str:
        """Remove comments based on language."""
        if language not in self.comment_patterns:
            language = 'generic'
        
        result = content
        for pattern, flags in self.comment_patterns[language]:
            # Compile pattern with flags
            if flags & re.DOTALL:
                # For DOTALL, we need to be careful not to remove too much
                result = re.sub(pattern, '', result, flags=flags)
            else:
                result = re.sub(pattern, '', result, flags=flags)
        
        return result
    
    def _restore_strings(self, content: str, replacements: Dict[str, str]) -> str:
        """Restore protected strings."""
        result = content
        for placeholder, original in replacements.items():
            result = result.replace(placeholder, original)
        return result
    
    def _normalize_whitespace(self, content: str) -> str:
        """
        Normalize whitespace while preserving structure.
        Removes excessive blank lines and trailing spaces.
        """
        lines = content.split('\n')
        normalized_lines = []
        
        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            
            # Skip empty lines that follow empty lines
            if not line and normalized_lines and not normalized_lines[-1]:
                continue
            
            normalized_lines.append(line)
        
        # Remove leading/trailing empty lines
        while normalized_lines and not normalized_lines[0]:
            normalized_lines.pop(0)
        while normalized_lines and not normalized_lines[-1]:
            normalized_lines.pop()
        
        return '\n'.join(normalized_lines)
    
    def should_process(self, content: str, file_path: Optional[str] = None) -> bool:
        """Only process if content is not empty and processor is enabled."""
        return (
            self.enabled and 
            bool(content.strip()) and
            len(content) < 10000000  # Don't process huge files
        )
