"""
Scan context - holds configuration, state, and shared data during a scan.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from enum import Enum
import os

from .finding import Finding, Severity, Category


class ScanMode(Enum):
    """Scanning modes."""
    FAST = "fast"          # Quick scan, limited analysis
    NORMAL = "normal"      # Balanced speed/coverage
    DEEP = "deep"          # Thorough analysis, slower
    CUSTOM = "custom"      # User-defined settings


class TargetType(Enum):
    """Types of scan targets."""
    LOCAL_DIRECTORY = "local_directory"
    GIT_REPOSITORY = "git_repository"
    WEB_URL = "web_url"
    GITHUB_REPO = "github_repo"
    DOCKER_IMAGE = "docker_image"
    ZIP_FILE = "zip_file"
    
    # Simplified names for CLI compatibility
    @classmethod
    def _missing_(cls, value):
        """Allow string aliases for target types."""
        aliases = {
            'local': cls.LOCAL_DIRECTORY,
            'git': cls.GIT_REPOSITORY,
            'web': cls.WEB_URL,
            'github': cls.GITHUB_REPO,
        }
        return aliases.get(value, None)


@dataclass
class ScanSettings:
    """Scan configuration settings."""
    # Basic settings
    target: str  # Path, URL, or identifier
    target_type: str = "web"  # web, local, git, github
    output_dir: Path = Path("./reports")
    
    # Scan mode
    mode: ScanMode = ScanMode.NORMAL
    
    # File filters
    include_extensions: Set[str] = field(default_factory=lambda: {
        '.js', '.jsx', '.ts', '.tsx', '.php', '.html', '.htm',
        '.py', '.java', '.go', '.rb', '.cs', '.cpp', '.c', '.h'
    })
    exclude_extensions: Set[str] = field(default_factory=lambda: {
        '.min.js', '.min.css', '.map', '.log', '.md', '.txt'
    })
    
    # Size limits
    max_file_size_mb: int = 10
    max_total_files: int = 10000
    
    # Analysis options
    enable_secret_detection: bool = True
    enable_dom_xss_detection: bool = True
    enable_sqli_detection: bool = True
    enable_path_traversal_detection: bool = True
    enable_info_disclosure_detection: bool = True
    
    # Performance
    max_workers: int = field(default_factory=lambda: os.cpu_count() or 4)
    timeout_per_file_seconds: int = 30
    
    # Reporting
    output_format: str = "json"  # json, html, markdown, console
    verbose: bool = False
    debug: bool = False
    
    # Custom rules
    custom_rules_path: Optional[Path] = None
    
    # Collector-specific settings
    github_token: Optional[str] = None
    git_branch: str = "main"
    include_uncommitted: bool = False
    web_max_depth: int = 3
    web_max_pages: int = 100
    ignore_patterns: Optional[List[str]] = None
    strict: bool = False


@dataclass
class ScanContext:
    """Context object passed through the scanning pipeline."""
    # Configuration
    settings: ScanSettings
    
    # State tracking
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    # Collected data
    files_collected: List[Path] = field(default_factory=list)
    files_processed: List[Path] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    collection_result: Optional[Any] = None  # CollectionResult from collectors
    
    # Statistics
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "total_files": 0,
        "processed_files": 0,
        "skipped_files": 0,
        "total_findings": 0,
        "findings_by_severity": {},
        "findings_by_category": {},
        "processing_time": 0.0,
    })
    
    # Caches and shared data
    file_content_cache: Dict[Path, str] = field(default_factory=dict)
    ast_cache: Dict[Path, Any] = field(default_factory=dict)
    seen_finding_ids: Set[str] = field(default_factory=set)
    
    def add_finding(self, finding: Finding):
        """Add a finding to the context."""
        # Keep output focused on actionable security findings.
        if finding.severity == Severity.INFO:
            return
        if finding.confidence < 0.65:
            return
        if self.settings.strict:
            if finding.confidence < 0.8:
                return
            if finding.severity in (Severity.LOW, Severity.INFO):
                return
        if finding.unique_id in self.seen_finding_ids:
            return
        self.seen_finding_ids.add(finding.unique_id)

        self.findings.append(finding)
        self.stats["total_findings"] += 1
        
        # Update severity stats
        severity_key = finding.severity.value
        self.stats["findings_by_severity"][severity_key] = \
            self.stats["findings_by_severity"].get(severity_key, 0) + 1
        
        # Update category stats
        category_key = finding.category.value
        self.stats["findings_by_category"][category_key] = \
            self.stats["findings_by_category"].get(category_key, 0) + 1
    
    def get_findings_by_severity(self, severity: Severity) -> List[Finding]:
        """Get all findings of a specific severity."""
        return [f for f in self.findings if f.severity == severity]
    
    def get_findings_by_category(self, category: Category) -> List[Finding]:
        """Get all findings of a specific category."""
        return [f for f in self.findings if f.category == category]
    
    @property
    def is_complete(self) -> bool:
        """Check if scan is complete."""
        return self.end_time is not None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get scan summary statistics."""
        return {
            "total_files": len(self.files_collected),
            "processed_files": len(self.files_processed),
            "total_findings": len(self.findings),
            "findings_by_severity": self.stats["findings_by_severity"],
            "findings_by_category": self.stats["findings_by_category"],
            "duration_seconds": self.end_time - self.start_time if self.end_time and self.start_time else 0,
        }
