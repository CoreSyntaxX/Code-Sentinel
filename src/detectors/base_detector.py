"""
Base detector class for cross-language detection.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
import logging

from models.finding import Finding, Severity, Category, Location
from models.scan_context import ScanContext


logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """
    Abstract base class for all detectors.
    
    Detectors look for specific types of issues across all languages:
    - Secrets (API keys, tokens, passwords)
    - JWTs
    - Emails
    - High-entropy strings
    - Configuration issues
    """
    
    def __init__(self):
        self.name = self.get_name()
        self.confidence = 0.7  # Default confidence
        
        # Cache for performance
        self._cache: Dict[str, Any] = {}
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of the detector."""
        pass
    
    @abstractmethod
    def detect(self, content: str, file_path: Path, context: ScanContext) -> List[Finding]:
        """
        Detect issues in content.
        
        Args:
            content: File content to analyze
            file_path: Path to the file
            context: Scan context with settings and state
            
        Returns:
            List of findings
        """
        pass
    
    def supports_file(self, file_path: Path) -> bool:
        """
        Check if detector supports this file type.
        Override in subclasses to limit to specific file types.
        """
        return True
    
    def _create_finding(
        self,
        title: str,
        severity: Severity,
        category: Category,
        file_path: Path,
        line_start: int,
        line_end: Optional[int] = None,
        code_snippet: Optional[str] = None,
        description: str = "",
        recommendation: str = "",
        rule_id: str = "",
        confidence: float = None,
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Finding:
        """
        Helper method to create a finding with consistent structure.
        """
        if confidence is None:
            confidence = self.confidence
            
        location = Location(
            file_path=str(file_path),
            line_start=line_start,
            line_end=line_end or line_start,
            code_snippet=code_snippet,
        )
        
        return Finding(
            title=title,
            severity=severity,
            category=category,
            location=location,
            description=description or title,
            recommendation=recommendation or "Review and secure the identified issue.",
            rule_id=rule_id or f"{self.name}-{category.value}",
            confidence=confidence,
            detector_name=self.name,
            context_before=context_before,
            context_after=context_after,
            tags=tags or [],
        )
    
    def _find_pattern_matches(
        self,
        content: str,
        patterns: List[Tuple[str, str, Severity, Category]],
        file_path: Path,
    ) -> List[Finding]:
        """
        Search for multiple regex patterns in content.
        
        Args:
            content: Content to search
            patterns: List of (pattern, title, severity, category)
            file_path: Path to the file
            
        Returns:
            List of findings
        """
        findings = []
        
        for pattern, title, severity, category in patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                logger.error(f"Invalid regex pattern {pattern}: {e}")
                continue
            
            for match in compiled.finditer(content):
                line_start = content[:match.start()].count('\n') + 1
                
                # Get the line where match occurs
                lines = content.split('\n')
                if line_start <= len(lines):
                    line_content = lines[line_start - 1]
                else:
                    line_content = ""
                
                # Get context (2 lines before and after)
                context_before = '\n'.join(lines[max(0, line_start - 3):line_start - 1])
                context_after = '\n'.join(lines[line_start:min(len(lines), line_start + 2)])
                
                finding = self._create_finding(
                    title=title,
                    severity=severity,
                    category=category,
                    file_path=file_path,
                    line_start=line_start,
                    code_snippet=line_content[:200],
                    description=f"Found {title.lower()} in the code.",
                    recommendation=f"Remove or secure the {title.lower()}.",
                    rule_id=f"{self.name.upper()}-{title.upper().replace(' ', '-')}",
                    context_before=context_before,
                    context_after=context_after,
                )
                
                findings.append(finding)
        
        return findings
    
    def _calculate_entropy(self, string: str) -> float:
        """
        Calculate Shannon entropy of a string.
        
        Args:
            string: Input string
            
        Returns:
            Entropy value (bits per character)
        """
        import math
        if not string:
            return 0
            
        # Count frequency of each character
        freq = {}
        for char in string:
            freq[char] = freq.get(char, 0) + 1
        
        # Calculate entropy
        entropy = 0
        length = len(string)
        for count in freq.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _is_high_entropy(self, string: str, threshold: float = 3.5) -> bool:
        """
        Check if a string has high entropy (likely a secret).
        
        Args:
            string: String to check
            threshold: Entropy threshold (default 3.5)
            
        Returns:
            True if entropy is above threshold
        """
        # Skip short strings
        if len(string) < 10:
            return False
        
        # Skip strings that are mostly numbers or simple patterns
        if re.match(r'^[0-9]+$', string):
            return False
        if re.match(r'^[a-f0-9]+$', string, re.IGNORECASE):
            return False  # Hex strings
        
        entropy = self._calculate_entropy(string)
        return entropy > threshold
    
    def pre_process_content(self, content: str) -> str:
        """
        Pre-process content before detection.
        Can be overridden by subclasses.
        """
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """
        Post-process findings (filter false positives, etc.).
        Can be overridden by subclasses.
        """
        return findings
