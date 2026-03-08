"""
Base analyzer class that all language analyzers inherit from.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import logging
import re

from models.finding import Finding, Severity, Category, Location
from models.scan_context import ScanContext
from models.file_meta import FileMetadata
from models.rule import RuleLanguage


logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    Abstract base class for all language analyzers.
    
    Each analyzer is responsible for:
    1. Checking if it supports a given file type
    2. Analyzing file content for security issues
    3. Returning findings in a standardized format
    """
    
    def __init__(self):
        self.name = self.get_name()
        self.supported_extensions: Set[str] = set()
        self.supported_languages: Set[RuleLanguage] = set()
        self._initialize_supported_formats()
        
        # Cache for AST or other parsed structures
        self._cache: Dict[Path, Any] = {}
        
        # Common patterns for all analyzers
        self.common_patterns = {
            "hardcoded_password": r'(?i)(password|passwd|pwd)\s*[:=]\s*[\'"][^\'"]+[\'"]',
            "hardcoded_secret": r'(?i)(secret|token|key)\s*[:=]\s*[\'"][^\'"]+[\'"]',
            "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        }
    
    def _initialize_supported_formats(self):
        """Initialize supported file extensions and languages. Override in subclasses."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of the analyzer."""
        pass
    
    def supports_file(self, file_path: Path, metadata: Optional[FileMetadata] = None) -> bool:
        """
        Check if this analyzer supports the given file.
        
        Args:
            file_path: Path to the file
            metadata: Optional file metadata
            
        Returns:
            True if analyzer supports this file type
        """
        extension = file_path.suffix.lower()
        return extension in self.supported_extensions
    
    @abstractmethod
    def analyze(self, file_path: Path, content: str, context: ScanContext) -> List[Finding]:
        """
        Main analysis method. Analyzes file content for security issues.
        
        Args:
            file_path: Path to the file being analyzed
            content: File content as string
            context: Scan context with settings and state
            
        Returns:
            List of security findings
        """
        pass
    
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
        confidence: float = 1.0,
        detector_name: Optional[str] = None,
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Finding:
        """
        Helper method to create a finding with consistent structure.
        """
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
            recommendation=recommendation or "Review and fix the identified issue.",
            rule_id=rule_id or f"{self.name}-{category.value}",
            confidence=confidence,
            detector_name=detector_name or self.name,
            context_before=context_before,
            context_after=context_after,
            tags=tags or [],
        )
    
    def _get_lines_with_numbers(self, content: str) -> List[Tuple[int, str]]:
        """
        Get content as list of (line_number, line_content) tuples.
        """
        lines = content.split('\n')
        return list(enumerate(lines, start=1))
    
    def _find_pattern_in_content(
        self,
        pattern: str,
        content: str,
        file_path: Path,
        category: Category,
        severity: Severity,
        title: str,
        description: str = "",
        recommendation: str = "",
        rule_id: str = "",
    ) -> List[Finding]:
        """
        Search for regex pattern in content and create findings.
        
        Args:
            pattern: Regex pattern to search for
            content: File content to search
            file_path: Path to the file
            category: Finding category
            severity: Finding severity
            title: Finding title
            description: Finding description
            recommendation: Recommendation for fixing
            rule_id: Rule identifier
            
        Returns:
            List of findings
        """
        findings = []
        
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        except re.error as e:
            logger.error(f"Invalid regex pattern {pattern}: {e}")
            return findings
        
        for match in compiled_pattern.finditer(content):
            # Calculate line number
            line_start = content[:match.start()].count('\n') + 1
            
            # Get the line where match occurs
            lines = content.split('\n')
            line_content = lines[line_start - 1] if line_start <= len(lines) else ""
            
            # Get context (2 lines before and after)
            context_before = '\n'.join(lines[max(0, line_start - 3):line_start - 1])
            context_after = '\n'.join(lines[line_start:min(len(lines), line_start + 2)])
            
            finding = self._create_finding(
                title=title,
                severity=severity,
                category=category,
                file_path=file_path,
                line_start=line_start,
                code_snippet=line_content[:200],  # Limit snippet length
                description=description,
                recommendation=recommendation,
                rule_id=rule_id,
                confidence=0.7,  # Pattern matches have medium confidence
                context_before=context_before,
                context_after=context_after,
                tags=["regex-pattern", self.name],
            )
            
            findings.append(finding)
        
        return findings
    
    def _analyze_with_ast(self, file_path: Path, content: str, context: ScanContext) -> List[Finding]:
        """
        Analyze content using AST parsing (if supported).
        To be implemented by subclasses that support AST.
        """
        return []
    
    def pre_process_content(self, content: str) -> str:
        """
        Pre-process content before analysis.
        Can be overridden by subclasses for language-specific processing.
        """
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """
        Post-process findings (filter false positives, adjust severity, etc.).
        Can be overridden by subclasses.
        """
        return findings
