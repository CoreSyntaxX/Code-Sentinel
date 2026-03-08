"""
Finding model - represents a detected security issue.
This is the core data structure that flows through the entire system.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import hashlib
from datetime import datetime


class Severity(Enum):
    """Risk severity levels following CVSS-like classification."""
    CRITICAL = "CRITICAL"  # 9.0-10.0 CVSS
    HIGH = "HIGH"          # 7.0-8.9
    MEDIUM = "MEDIUM"      # 4.0-6.9
    LOW = "LOW"            # 0.1-3.9
    INFO = "INFO"          # Informational only


class Category(Enum):
    """Categories of security findings."""
    DOM_XSS = "DOM XSS"
    REFLECTED_XSS = "Reflected XSS"
    STORED_XSS = "Stored XSS"
    SQL_INJECTION = "SQL Injection"
    COMMAND_INJECTION = "Command Injection"
    PATH_TRAVERSAL = "Path Traversal"
    SECRET_LEAK = "Secret Leak"
    API_KEY_EXPOSURE = "API Key Exposure"
    JWT_EXPOSURE = "JWT Exposure"
    COOKIE_LEAK = "Cookie Leak"
    EMAIL_LEAK = "Email Leak"
    HARDCODED_CREDENTIAL = "Hardcoded Credential"
    WEAK_CRYPTO = "Weak Cryptography"
    UNSANITIZED_INPUT = "Unsanitized Input"
    INSECURE_CONFIG = "Insecure Configuration"
    HIDDEN_PATH = "Hidden Path"
    INFORMATION_DISCLOSURE = "Information Disclosure"
    OTHER = "Other"


@dataclass
class Location:
    """File location information."""
    file_path: str
    line_start: int
    line_end: Optional[int] = None
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    code_snippet: Optional[str] = None
    
    def __str__(self):
        return f"{self.file_path}:{self.line_start}"


@dataclass
class Finding:
    """A security finding/vulnerability."""
    # Required fields
    title: str
    severity: Severity
    category: Category
    location: Location
    
    # Descriptive fields
    description: str
    recommendation: str
    
    # Technical details
    rule_id: str  # e.g., "JS-DOM-XSS-001"
    confidence: float = 1.0  # 0.0 to 1.0
    
    # Contextual information
    vulnerable_code: Optional[str] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    
    # Metadata
    detector_name: Optional[str] = None  # Which detector found it
    timestamp: datetime = field(default_factory=datetime.now)
    unique_id: str = field(init=False)
    
    # Additional data for extensibility
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Generate a unique ID for the finding."""
        # Create a hash based on title, location, and rule_id
        content = f"{self.title}:{self.rule_id}:{self.location.file_path}:{self.location.line_start}"
        self.unique_id = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary for serialization."""
        return {
            "unique_id": self.unique_id,
            "title": self.title,
            "severity": self.severity.value,
            "category": self.category.value,
            "location": {
                "file_path": self.location.file_path,
                "line_start": self.location.line_start,
                "line_end": self.location.line_end,
                "code_snippet": self.location.code_snippet,
            },
            "description": self.description,
            "recommendation": self.recommendation,
            "rule_id": self.rule_id,
            "confidence": self.confidence,
            "vulnerable_code": self.vulnerable_code,
            "detector_name": self.detector_name,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
        }
    
    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.title} at {self.location}"


@dataclass
class FindingGroup:
    """Group of related findings (e.g., same file, same type)."""
    findings: List[Finding]
    group_key: str  # e.g., "file:app.js" or "type:DOM_XSS"
    
    @property
    def severity(self) -> Severity:
        """Get highest severity in the group."""
        if not self.findings:
            return Severity.INFO
        return max(self.findings, key=lambda f: f.severity.value).severity
    
    def count_by_severity(self) -> Dict[Severity, int]:
        """Count findings by severity level."""
        counts = {severity: 0 for severity in Severity}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts
