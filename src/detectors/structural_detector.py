"""
Detector for structural issues like exposed endpoints, debug code, etc.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
import re
import logging

from models.finding import Finding, Severity, Category
from models.scan_context import ScanContext
from detectors.base_detector import BaseDetector


logger = logging.getLogger(__name__)


class StructuralDetector(BaseDetector):
    """
    Detector for structural security issues:
    - Exposed debug endpoints
    - Hidden paths/files
    - Exposed admin interfaces
    - Debug/development code left in production
    - Information disclosure in error messages
    """
    
    def __init__(self):
        super().__init__()
        self.confidence = 0.8
        
        # Debug/development code patterns
        self.debug_patterns = [
            # Debug function calls
            (r'\b(print_r|var_dump|dump|debug|dd)\s*\([^)]*\)',
             "Debug Function Call", Severity.LOW, Category.INFORMATION_DISCLOSURE),
            
            # Debug flags/variables
            (r'\b(debug|DEBUG)\s*=\s*(true|1|"true"|\'true\')',
             "Debug Flag Enabled", Severity.MEDIUM, Category.INFORMATION_DISCLOSURE),
            
            # Development environment detection
            (r'\b(development|dev|staging|test)\b.*\benvironment\b',
             "Development Environment Detection", Severity.LOW, Category.INFORMATION_DISCLOSURE),
            
            # TODO/FIXME comments
            (r'(TODO|FIXME|HACK|XXX|BUG):.*',
             "TODO/FIXME Comment", Severity.INFO, Category.INFORMATION_DISCLOSURE),
        ]
        
        # Exposed endpoint patterns
        self.endpoint_patterns = [
            # Admin endpoints
            (r'/\b(admin|administrator|dashboard|control|manage|backend)\b',
             "Admin Endpoint", Severity.MEDIUM, Category.HIDDEN_PATH),
            
            # Debug/development endpoints
            (r'/\b(debug|dev|development|test|testing|staging)\b',
             "Debug Endpoint", Severity.LOW, Category.HIDDEN_PATH),
            
            # API documentation endpoints
            (r'/\b(api[_-]?docs|swagger|openapi|redoc|graphiql|graphql)\b',
             "API Documentation Endpoint", Severity.LOW, Category.HIDDEN_PATH),
            
            # Monitoring/health endpoints
            (r'/\b(health|status|metrics|monitor|ping)\b',
             "Monitoring Endpoint", Severity.LOW, Category.HIDDEN_PATH),
            
            # Common vulnerable endpoints
            (r'/\b(phpinfo|info|test|check|version)\b',
             "Information Disclosure Endpoint", Severity.MEDIUM, Category.INFORMATION_DISCLOSURE),
            
            # File upload endpoints
            (r'/\b(upload|file|image|attachment)\b.*\.(php|asp|jsp|aspx)\b',
             "File Upload Endpoint", Severity.MEDIUM, Category.HIDDEN_PATH),
        ]
        
        # Error message patterns (information disclosure)
        self.error_patterns = [
            # Stack traces
            (r'at\s+[^\s]+\.[^\s]+\s*\([^)]+\)',
             "Stack Trace", Severity.MEDIUM, Category.INFORMATION_DISCLOSURE),
            
            # Database error messages
            (r'(SQL|Database|MySQL|PostgreSQL|MongoDB).*[Ee]rror',
             "Database Error Message", Severity.MEDIUM, Category.INFORMATION_DISCLOSURE),
            
            # File system paths in errors
            (r'/[^\s]+\.(php|js|java|py|rb|go)\b.*[Ee]rror',
             "File Path in Error", Severity.LOW, Category.INFORMATION_DISCLOSURE),
        ]
        
        # Hardcoded configuration issues
        self.config_patterns = [
            # Hardcoded hosts/URLs
            (r'\b(host|server|url|endpoint)\s*=\s*["\'][^"\']+["\']',
             "Hardcoded Host/URL", Severity.LOW, Category.INSECURE_CONFIG),
            
            # Hardcoded ports
            (r'\bport\s*=\s*\d+',
             "Hardcoded Port", Severity.LOW, Category.INSECURE_CONFIG),
        ]
        
        # File-specific patterns
        self.file_specific_patterns = {
            '.gitignore': [
                (r'^\s*[^#\n].*', "Gitignore Entry", Severity.INFO, Category.HIDDEN_PATH),
            ],
            'dockerfile': [
                (r'EXPOSE\s+\d+', "Exposed Port", Severity.LOW, Category.INFORMATION_DISCLOSURE),
                (r'USER\s+(root|0)', "Running as Root", Severity.MEDIUM, Category.INSECURE_CONFIG),
            ],
            '.env': [
                (r'^\s*[A-Z_]+=.*', "Environment Variable", Severity.LOW, Category.INFORMATION_DISCLOSURE),
            ],
        }
    
    def get_name(self) -> str:
        return "StructuralDetector"
    
    def detect(self, content: str, file_path: Path, context: ScanContext) -> List[Finding]:
        """
        Detect structural security issues.
        """
        findings = []
        
        logger.debug(f"Structural detector analyzing {file_path}")
        
        # Pre-process content
        processed_content = self.pre_process_content(content)
        
        # 1. Check for debug/development code
        debug_findings = self._find_pattern_matches(
            processed_content,
            self.debug_patterns,
            file_path,
        )
        findings.extend(debug_findings)
        
        # 2. Check for exposed endpoints
        endpoint_findings = self._detect_endpoints(processed_content, file_path)
        findings.extend(endpoint_findings)
        
        # 3. Check for error information disclosure
        error_findings = self._find_pattern_matches(
            processed_content,
            self.error_patterns,
            file_path,
        )
        findings.extend(error_findings)
        
        # 4. Check for configuration issues
        config_findings = self._find_pattern_matches(
            processed_content,
            self.config_patterns,
            file_path,
        )
        findings.extend(config_findings)
        
        # 5. Check file-specific patterns
        file_specific_findings = self._check_file_specific_patterns(processed_content, file_path)
        findings.extend(file_specific_findings)
        
        # 6. Check for hardcoded sensitive configuration
        sensitive_config_findings = self._detect_sensitive_config(processed_content, file_path)
        findings.extend(sensitive_config_findings)
        
        # Post-process findings
        findings = self.post_process_findings(findings, context)
        
        logger.debug(f"Structural detector found {len(findings)} issues in {file_path}")
        return findings
    
    def _detect_endpoints(self, content: str, file_path: Path) -> List[Finding]:
        """Detect exposed endpoints in code."""
        findings = []
        
        # Look for endpoint patterns in different contexts
        endpoint_contexts = [
            # URL patterns in strings
            (r'["\'`](/[^"\'\`]+)["\'`]', "URL string"),
            
            # Route definitions (common frameworks)
            (r'\.(get|post|put|delete|patch|route)\s*\(\s*["\']([^"\']+)["\']', "Route definition"),
            (r'@(GET|POST|PUT|DELETE|PATCH|Route)\s*\(\s*["\']([^"\']+)["\']', "Annotation route"),
            (r'route\s*\([^)]*["\']([^"\']+)["\']', "Route function"),
            
            # HTML links
            (r'href\s*=\s*["\']([^"\']+)["\']', "HTML link"),
            (r'src\s*=\s*["\']([^"\']+)["\']', "HTML src"),
            (r'action\s*=\s*["\']([^"\']+)["\']', "Form action"),
        ]
        
        for pattern, context_type in endpoint_contexts:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                endpoint = match.group(1) if match.lastindex else match.group(0)
                
                # Check if endpoint matches any of our patterns
                for ep_pattern, title, severity, category in self.endpoint_patterns:
                    if re.search(ep_pattern, endpoint, re.IGNORECASE):
                        line_start = content[:match.start()].count('\n') + 1
                        
                        # Get the line
                        lines = content.split('\n')
                        if line_start <= len(lines):
                            line_content = lines[line_start - 1]
                        else:
                            line_content = ""
                        
                        finding = self._create_finding(
                            title=f"{title} in {context_type}",
                            severity=severity,
                            category=category,
                            file_path=file_path,
                            line_start=line_start,
                            code_snippet=line_content[:200],
                            description=f"Potential {title.lower()} found: {endpoint}",
                            recommendation="Review endpoint for proper access controls and remove if not needed.",
                            rule_id=f"STRUCTURAL-{title.upper().replace(' ', '-')}",
                        )
                        finding.metadata["sensitive_path"] = endpoint
                        
                        findings.append(finding)
                        break
        
        return findings
    
    def _check_file_specific_patterns(self, content: str, file_path: Path) -> List[Finding]:
        """Check for patterns specific to certain file types."""
        findings = []
        filename = file_path.name.lower()
        
        for pattern_name, patterns in self.file_specific_patterns.items():
            if pattern_name in filename or filename.endswith(pattern_name):
                file_findings = self._find_pattern_matches(
                    content, patterns, file_path
                )
                findings.extend(file_findings)
                break
        
        return findings
    
    def _detect_sensitive_config(self, content: str, file_path: Path) -> List[Finding]:
        """Detect sensitive configuration values."""
        findings = []
        
        # Sensitive configuration patterns
        sensitive_patterns = [
            # Debug mode enabled
            (r'debug\s*=\s*(true|1|yes|enabled)', 
             "Debug Mode Enabled", Severity.MEDIUM, Category.INSECURE_CONFIG),
            
            # Error display enabled
            (r'display_errors\s*=\s*(on|1|true)', 
             "Error Display Enabled", Severity.MEDIUM, Category.INFORMATION_DISCLOSURE),
            
            # Cross-Origin settings
            (r'Access-Control-Allow-Origin\s*=\s*\*', 
             "CORS Wildcard", Severity.LOW, Category.INSECURE_CONFIG),
            
            # SSL/TLS disabled
            (r'secure\s*=\s*(false|0|no)', 
             "SSL/TLS Disabled", Severity.HIGH, Category.INSECURE_CONFIG),
            
            # Session security
            (r'session\.cookie_secure\s*=\s*(false|0)', 
             "Insecure Session Cookie", Severity.MEDIUM, Category.INSECURE_CONFIG),
            
            # Clickjacking protection disabled
            (r'X-Frame-Options\s*=\s*none', 
             "Frame Options Disabled", Severity.MEDIUM, Category.INSECURE_CONFIG),
        ]
        
        config_findings = self._find_pattern_matches(
            content, sensitive_patterns, file_path
        )
        findings.extend(config_findings)
        
        return findings
    
    def pre_process_content(self, content: str) -> str:
        """Pre-process content for structural detection."""
        # Keep content as-is for structural analysis
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """Filter false positives and adjust findings."""
        filtered_findings = []
        
        for finding in findings:
            # Skip if it's a false positive
            if self._is_false_positive(finding):
                logger.debug(f"Filtered structural false positive: {finding.title}")
                continue
            
            # Adjust severity based on file type
            finding.severity = self._adjust_severity(finding)
            
            filtered_findings.append(finding)
        
        return filtered_findings
    
    def _is_false_positive(self, finding: Finding) -> bool:
        """Check if finding is a false positive."""
        code_snippet = finding.location.code_snippet or ""
        title = finding.title
        
        # Common false positives
        false_positives = [
            # Debug functions in test files
            (r'test_.*\.js', "Debug Function Call"),
            (r'_test\.', "Debug Function Call"),
            (r'spec\.', "Debug Function Call"),
            
            # TODO comments with specific safe content
            (r'TODO:.*(refactor|optimize|improve)', "TODO/FIXME Comment"),
            
            # Admin endpoints in documentation/comments
            (r'//.*admin', "Admin Endpoint"),
            (r'#.*admin', "Admin Endpoint"),
            (r'<!--.*admin.*-->', "Admin Endpoint"),
            
            # Health endpoints in monitoring code
            (r'monitor\.js', "Monitoring Endpoint"),
            (r'healthcheck\.', "Monitoring Endpoint"),
        ]
        
        file_path = finding.location.file_path
        
        for pattern, affected_title in false_positives:
            if affected_title == title:
                if pattern.startswith('/') or pattern.startswith('*'):
                    # Pattern is a regex
                    if re.search(pattern, code_snippet, re.IGNORECASE):
                        return True
                else:
                    # Pattern is a filename pattern
                    if pattern in file_path.lower():
                        return True
        
        return False
    
    def _adjust_severity(self, finding: Finding) -> Severity:
        """Adjust severity based on file type and context."""
        original_severity = finding.severity
        file_path = finding.location.file_path
        
        # Downgrade severity for test files
        if any(test_pattern in file_path.lower() 
               for test_pattern in ['test_', '_test.', 'spec.', '.spec.', 'mock.']):
            if original_severity == Severity.MEDIUM:
                return Severity.LOW
            elif original_severity == Severity.HIGH:
                return Severity.MEDIUM
        
        # Upgrade severity for production config files
        if any(config_pattern in file_path.lower()
               for config_pattern in ['.env.production', 'config.prod', 'production.']):
            if original_severity == Severity.LOW:
                return Severity.MEDIUM
            elif original_severity == Severity.MEDIUM:
                return Severity.HIGH
        
        return original_severity
