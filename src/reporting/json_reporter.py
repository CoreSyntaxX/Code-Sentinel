"""
JSON reporter - machine-readable output.
"""

import json
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from models.scan_context import ScanContext
from models.finding import Finding
from reporting.base_reporter import BaseReporter


logger = logging.getLogger(__name__)


class JSONReporter(BaseReporter):
    """
    JSON reporter for machine-readable output.
    Good for integration with other tools.
    """
    
    def __init__(self):
        super().__init__()
    
    def get_name(self) -> str:
        return "JSONReporter"
    
    def get_extension(self) -> str:
        return "json"
    
    def generate_report(self, context: ScanContext, output_path: Optional[Path] = None) -> Path:
        """
        Generate JSON report.
        """
        logger.info("Generating JSON report...")
        
        # Prepare data
        report_data = self._prepare_report_data(context)
        
        # Add additional metadata
        report_data["report_format"] = "json"
        report_data["report_version"] = "1.0"
        
        # Determine output path
        output_file = self._ensure_output_dir(output_path)
        
        # Write JSON with pretty formatting
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"JSON report saved to: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}")
            raise
    
    def _prepare_report_data(self, context: ScanContext) -> Dict[str, Any]:
        """Prepare concise JSON report with snippet-focused findings."""
        duration = (
            context.end_time - context.start_time
            if context.end_time and context.start_time
            else 0
        )
        findings = [self._finding_excerpt(finding) for finding in context.findings]
        sensitive_paths = self._collect_sensitive_paths(context.findings)

        return {
            "metadata": {
                "generated_at": self.timestamp.isoformat(),
                "tool_name": "Security Scanner",
                "tool_version": "1.0.0",
                "scan_target": context.settings.target,
                "scan_mode": context.settings.mode.value,
                "duration_seconds": duration,
                "total_files_scanned": len(context.files_collected),
                "total_findings": len(findings),
            },
            "findings": findings,
            "sensitive_paths": sensitive_paths,
        }

    def _finding_excerpt(self, finding: Finding) -> Dict[str, Any]:
        """Return only the fields needed to understand why code is vulnerable."""
        return {
            "title": finding.title,
            "severity": finding.severity.value,
            "file_path": finding.location.file_path,
            "line_start": finding.location.line_start,
            "line_end": finding.location.line_end,
            "why_vulnerable": finding.description,
            "code_snippet": finding.location.code_snippet,
            "context_before": finding.context_before,
            "context_after": finding.context_after,
        }

    def _collect_sensitive_paths(self, findings: List[Finding]) -> List[Dict[str, Any]]:
        """Aggregate sensitive path hits from findings metadata."""
        paths = {}
        for f in findings:
            spath = f.metadata.get("sensitive_path") if f.metadata else None
            if not spath:
                continue
            key = (f.location.file_path, spath)
            if key in paths:
                continue
            paths[key] = {
                "file_path": f.location.file_path,
                "line_start": f.location.line_start,
                "path": spath,
                "severity": f.severity.value,
                "title": f.title,
            }
        return list(paths.values())
    
    def _count_files_by_extension(self, files: List[Path]) -> Dict[str, int]:
        """Count files by extension."""
        extensions = {}
        for file_path in files:
            ext = file_path.suffix.lower()
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1
            else:
                extensions["no_extension"] = extensions.get("no_extension", 0) + 1
        return extensions
