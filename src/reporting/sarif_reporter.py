"""
SARIF (Static Analysis Results Interchange Format) reporter.
Industry standard for security tools.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import logging
import uuid
from datetime import datetime

from models.scan_context import ScanContext
from models.finding import Severity
from reporting.base_reporter import BaseReporter


logger = logging.getLogger(__name__)


class SARIFReporter(BaseReporter):
    """
    SARIF reporter for industry-standard output.
    Compatible with GitHub Security, Azure DevOps, etc.
    """
    
    def __init__(self):
        super().__init__()
    
    def get_name(self) -> str:
        return "SARIFReporter"
    
    def get_extension(self) -> str:
        return "sarif"
    
    def generate_report(self, context: ScanContext, output_path: Optional[Path] = None) -> Path:
        """
        Generate SARIF report.
        """
        logger.info("Generating SARIF report...")
        
        # Prepare SARIF data
        sarif_data = self._prepare_sarif_data(context)
        
        # Determine output path
        output_file = self._ensure_output_dir(output_path)
        
        # Write SARIF file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sarif_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"SARIF report saved to: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to generate SARIF report: {e}")
            raise
    
    def _prepare_sarif_data(self, context: ScanContext) -> Dict[str, Any]:
        """
        Prepare SARIF data structure.
        Follows SARIF v2.1.0 specification.
        """
        # Generate run GUID
        run_guid = str(uuid.uuid4())
        
        # Convert findings to SARIF results
        results = []
        for finding in context.findings:
            result = self._finding_to_sarif_result(finding)
            if result:
                results.append(result)
        
        # SARIF schema
        sarif = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Security Scanner",
                            "version": "1.0.0",
                            "informationUri": "https://github.com/yourusername/security-scanner",
                            "rules": self._get_sarif_rules(context.findings),
                        }
                    },
                    "automationDetails": {
                        "id": f"security-scanner/{run_guid}",
                    },
                    "results": results,
                    "columnKind": "utf16CodeUnits",
                }
            ]
        }
        
        return sarif
    
    def _finding_to_sarif_result(self, finding) -> Optional[Dict[str, Any]]:
        """Convert finding to SARIF result."""
        try:
            # Map severity to SARIF level
            severity_map = {
                Severity.CRITICAL: "error",
                Severity.HIGH: "error",
                Severity.MEDIUM: "warning",
                Severity.LOW: "note",
                Severity.INFO: "note",
            }
            
            level = severity_map.get(finding.severity, "note")
            
            # Create result
            result = {
                "ruleId": finding.rule_id,
                "message": {
                    "text": finding.description
                },
                "level": level,
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": finding.location.file_path,
                                "uriBaseId": "%SRCROOT%"
                            },
                            "region": {
                                "startLine": finding.location.line_start,
                                "startColumn": finding.location.column_start or 1,
                                "endLine": finding.location.line_end or finding.location.line_start,
                                "endColumn": finding.location.column_end or 1,
                            }
                        }
                    }
                ],
                "properties": {
                    "security-severity": self._severity_to_cvss(finding.severity),
                    "tags": finding.tags,
                    "confidence": finding.confidence,
                }
            }
            
            # Add code snippet if available
            if finding.location.code_snippet:
                snippet = {
                    "text": finding.location.code_snippet[:500]  # Limit length
                }
                result["locations"][0]["physicalLocation"]["region"]["snippet"] = snippet
            
            # Add context if available
            if finding.context_before or finding.context_after:
                result["partialFingerprints"] = {
                    "contextHash": self._hash_context(finding.context_before, finding.context_after)
                }
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to convert finding to SARIF: {e}")
            return None
    
    def _get_sarif_rules(self, findings: List) -> List[Dict[str, Any]]:
        """Extract unique rules from findings for SARIF."""
        rules = {}
        
        for finding in findings:
            rule_id = finding.rule_id
            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "name": finding.title,
                    "shortDescription": {
                        "text": finding.title
                    },
                    "fullDescription": {
                        "text": finding.description
                    },
                    "help": {
                        "text": finding.recommendation,
                        "markdown": finding.recommendation
                    },
                    "properties": {
                        "category": finding.category.value,
                        "tags": finding.tags,
                    }
                }
        
        return list(rules.values())
    
    def _severity_to_cvss(self, severity: Severity) -> str:
        """Convert severity to CVSS score string."""
        cvss_scores = {
            Severity.CRITICAL: "9.0",
            Severity.HIGH: "7.0",
            Severity.MEDIUM: "4.0",
            Severity.LOW: "2.0",
            Severity.INFO: "0.0",
        }
        return cvss_scores.get(severity, "0.0")
    
    def _hash_context(self, context_before: Optional[str], context_after: Optional[str]) -> str:
        """Create hash from context for fingerprinting."""
        import hashlib
        context_str = f"{context_before or ''}|{context_after or ''}"
        return hashlib.md5(context_str.encode()).hexdigest()[:16]
