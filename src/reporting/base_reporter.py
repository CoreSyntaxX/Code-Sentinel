"""
Base reporter class for all report formats.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta

from models.finding import Finding, Severity, Category
from models.scan_context import ScanContext


logger = logging.getLogger(__name__)


class BaseReporter(ABC):
    """
    Abstract base class for all reporters.
    
    Reporters generate output in various formats:
    - JSON (machine-readable)
    - HTML (visual, interactive)
    - Markdown (for GitHub/GitLab)
    - SARIF (security tool standard)
    - Console (CLI output)
    """
    
    def __init__(self):
        self.name = self.get_name()
        self.output_dir = Path("./reports")
        self.timestamp = datetime.now()
        
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of the reporter."""
        pass
    
    @abstractmethod
    def generate_report(self, context: ScanContext, output_path: Optional[Path] = None) -> Path:
        """
        Generate a report.
        
        Args:
            context: Scan context with findings
            output_path: Optional specific output path
            
        Returns:
            Path to generated report
        """
        pass
    
    def _ensure_output_dir(self, output_path: Optional[Path] = None) -> Path:
        """Ensure output directory exists and return full path."""
        if output_path:
            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_path
        else:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            timestamp_str = self.timestamp.strftime("%Y%m%d_%H%M%S")
            return self.output_dir / f"scan_report_{timestamp_str}.{self.get_extension()}"
    
    @abstractmethod
    def get_extension(self) -> str:
        """Get file extension for this report format."""
        pass
    
    def _prepare_report_data(self, context: ScanContext) -> Dict[str, Any]:
        """
        Prepare common report data structure.
        """
        summary = context.get_summary()
        
        # Organize findings
        findings_by_file = self._group_findings_by_file(context.findings)
        findings_by_severity = self._group_findings_by_severity(context.findings)
        findings_by_category = self._group_findings_by_category(context.findings)
        
        # Calculate statistics
        stats = {
            "total_findings": len(context.findings),
            "critical_count": len([f for f in context.findings if f.severity == Severity.CRITICAL]),
            "high_count": len([f for f in context.findings if f.severity == Severity.HIGH]),
            "medium_count": len([f for f in context.findings if f.severity == Severity.MEDIUM]),
            "low_count": len([f for f in context.findings if f.severity == Severity.LOW]),
            "info_count": len([f for f in context.findings if f.severity == Severity.INFO]),
            "files_with_findings": len(findings_by_file),
            "total_files_scanned": len(context.files_collected),
            "duration_seconds": summary.get("duration_seconds", 0),
        }
        
        # Risk score calculation (0-100)
        risk_score = self._calculate_risk_score(context.findings)
        
        return {
            "metadata": {
                "generated_at": self.timestamp.isoformat(),
                "tool_name": "Security Scanner",
                "tool_version": "1.0.0",
                "scan_target": context.settings.target,
                "scan_mode": context.settings.mode.value,
                "duration_seconds": stats["duration_seconds"],
                "risk_score": risk_score,
            },
            "summary": stats,
            "findings_by_severity": findings_by_severity,
            "findings_by_category": findings_by_category,
            "findings_by_file": findings_by_file,
            "all_findings": [self._finding_to_dict(f) for f in context.findings],
            "scan_statistics": {
                "files_collected": len(context.files_collected),
                "files_processed": len(context.files_processed),
                "processing_time": summary.get("processing_time", 0),
            },
        }
    
    def _group_findings_by_file(self, findings: List[Finding]) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by file path."""
        grouped = {}
        for finding in findings:
            file_path = finding.location.file_path
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append(self._finding_to_dict(finding))
        return grouped
    
    def _group_findings_by_severity(self, findings: List[Finding]) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by severity."""
        grouped = {}
        for finding in findings:
            severity = finding.severity.value
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(self._finding_to_dict(finding))
        return grouped
    
    def _group_findings_by_category(self, findings: List[Finding]) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by category."""
        grouped = {}
        for finding in findings:
            category = finding.category.value
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(self._finding_to_dict(finding))
        return grouped
    
    def _finding_to_dict(self, finding: Finding) -> Dict[str, Any]:
        """Convert finding to dictionary for serialization."""
        return {
            "id": finding.unique_id,
            "title": finding.title,
            "severity": finding.severity.value,
            "category": finding.category.value,
            "confidence": finding.confidence,
            "file_path": finding.location.file_path,
            "line_start": finding.location.line_start,
            "line_end": finding.location.line_end,
            "code_snippet": finding.location.code_snippet,
            "description": finding.description,
            "recommendation": finding.recommendation,
            "rule_id": finding.rule_id,
            "detector_name": finding.detector_name,
            "context_before": finding.context_before,
            "context_after": finding.context_after,
            "tags": finding.tags,
            "timestamp": finding.timestamp.isoformat() if hasattr(finding.timestamp, 'isoformat') else str(finding.timestamp),
        }
    
    def _calculate_risk_score(self, findings: List[Finding]) -> float:
        """Calculate overall risk score (0-100)."""
        if not findings:
            return 0.0
        
        # Weighted score based on severity
        severity_weights = {
            Severity.CRITICAL: 10.0,
            Severity.HIGH: 7.5,
            Severity.MEDIUM: 5.0,
            Severity.LOW: 2.5,
            Severity.INFO: 1.0,
        }
        
        total_score = 0.0
        max_possible_score = len(findings) * 10.0  # All critical
        
        for finding in findings:
            weight = severity_weights.get(finding.severity, 1.0)
            # Adjust by confidence
            weighted_score = weight * finding.confidence
            total_score += weighted_score
        
        # Normalize to 0-100
        if max_possible_score == 0:
            return 0.0
        
        risk_score = (total_score / max_possible_score) * 100
        return min(risk_score, 100.0)
    
    def _get_severity_color(self, severity: Severity) -> str:
        """Get color for severity level."""
        colors = {
            Severity.CRITICAL: "#dc3545",  # Red
            Severity.HIGH: "#fd7e14",      # Orange
            Severity.MEDIUM: "#ffc107",    # Yellow
            Severity.LOW: "#28a745",       # Green
            Severity.INFO: "#17a2b8",      # Blue
        }
        return colors.get(severity, "#6c757d")
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
