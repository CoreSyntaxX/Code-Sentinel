"""
Pattern-based detector using the rule engine.
Uses regex patterns to find various types of issues.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import re

from models.finding import Finding, Severity, Category
from models.scan_context import ScanContext
from models.rule import RuleLanguage
from detectors.base_detector import BaseDetector
from engine.rule_engine import RuleEngine


logger = logging.getLogger(__name__)


class PatternDetector(BaseDetector):
    """
    Detector that uses regex patterns to find security issues.
    Integrates with the rule engine for pattern matching.
    """
    
    def __init__(self, rule_engine: Optional[RuleEngine] = None):
        super().__init__()
        self.rule_engine = rule_engine or RuleEngine()
        
        # Common patterns (fallback if rule engine not loaded)
        self.common_patterns = [
            # Hardcoded IP addresses
            (r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', 
             "Hardcoded IP Address", Severity.LOW, Category.INFORMATION_DISCLOSURE),
            
            # Email addresses
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
             "Email Address in Code", Severity.LOW, Category.EMAIL_LEAK),
            
            # Credit card numbers (simplified pattern)
            (r'\b4[0-9]{12}(?:[0-9]{3})?\b',  # Visa
             "Potential Credit Card Number", Severity.CRITICAL, Category.INFORMATION_DISCLOSURE),
            
            # Phone numbers (international format)
            (r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b',
             "Phone Number in Code", Severity.LOW, Category.INFORMATION_DISCLOSURE),
            
            # AWS Access Key ID
            (r'(?i)(aws|amazon).{0,30}(access|api).{0,10}[:=]\s*["\']?AKIA[0-9A-Z]{16}["\']?',
             "AWS Access Key ID", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            
            # AWS Secret Access Key
            (r'(?i)(aws|amazon).{0,30}(secret|access).{0,10}[:=]\s*["\']?[A-Za-z0-9/+=]{40}["\']?',
             "AWS Secret Access Key", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            
            # Google API Key
            (r'AIza[0-9A-Za-z\-_]{35}',
             "Google API Key", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            
            # Facebook Access Token
            (r'EAACEdEose0cBA[0-9A-Za-z]+',
             "Facebook Access Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # GitHub Token
            (r'ghp_[0-9a-zA-Z]{36}',
             "GitHub Personal Access Token", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            
            # Slack Token
            (r'xox[baprs]-[0-9a-zA-Z]{10,48}',
             "Slack API Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # Private SSH Key (begins with -----BEGIN)
            (r'-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END[ A-Z0-9_-]*PRIVATE KEY-----',
             "Private SSH Key", Severity.CRITICAL, Category.SECRET_LEAK),
            
            # RSA Private Key
            (r'-----BEGIN RSA PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END RSA PRIVATE KEY-----',
             "RSA Private Key", Severity.CRITICAL, Category.SECRET_LEAK),
        ]
        
        # File-specific patterns
        self.config_file_patterns = {
            '.env': [
                (r'[A-Z_]+=.*', "Environment Variable", Severity.LOW, Category.INFORMATION_DISCLOSURE),
            ],
            'dockerfile': [
                (r'ENV\s+[A-Z_]+=.*', "Docker Environment Variable", Severity.LOW, Category.INFORMATION_DISCLOSURE),
                (r'ARG\s+[A-Z_]+=.*', "Docker Build Argument", Severity.LOW, Category.INFORMATION_DISCLOSURE),
            ],
        }
    
    def get_name(self) -> str:
        return "PatternDetector"
    
    def detect(self, content: str, file_path: Path, context: ScanContext) -> List[Finding]:
        """
        Detect patterns in content using rule engine and common patterns.
        """
        findings = []
        
        # Skip if content is empty
        if not content.strip():
            return findings
        
        logger.debug(f"Pattern detector analyzing {file_path}")
        
        # Pre-process content
        processed_content = self.pre_process_content(content)
        
        # 1. Use rule engine if available
        if self.rule_engine and self.rule_engine.rules:
            try:
                # Determine language from file extension
                language = self._get_language_from_extension(file_path)
                if language:
                    rule_findings = self.rule_engine.execute_all_rules(
                        processed_content, file_path, [language]
                    )
                    findings.extend(rule_findings)
            except Exception as e:
                logger.warning(f"Rule engine failed for {file_path}: {e}")
        
        # 2. Use common patterns
        common_findings = self._find_pattern_matches(
            processed_content,
            self.common_patterns,
            file_path,
        )
        findings.extend(common_findings)
        
        # 3. Check for file-specific patterns
        file_specific_findings = self._check_file_specific_patterns(
            processed_content, file_path
        )
        findings.extend(file_specific_findings)
        
        # 4. Check for leaked cookies
        cookie_findings = self._detect_cookies(processed_content, file_path)
        findings.extend(cookie_findings)
        
        # 5. Check for hardcoded credentials
        credential_findings = self._detect_hardcoded_credentials(processed_content, file_path)
        findings.extend(credential_findings)
        
        # Post-process to remove false positives
        findings = self.post_process_findings(findings, context)
        
        logger.debug(f"Pattern detector found {len(findings)} issues in {file_path}")
        return findings
    
    def _get_language_from_extension(self, file_path: Path) -> Optional[RuleLanguage]:
        """Map file extension to RuleLanguage."""
        extension = file_path.suffix.lower()
        
        language_map = {
            '.js': RuleLanguage.JAVASCRIPT,
            '.jsx': RuleLanguage.JAVASCRIPT,
            '.ts': RuleLanguage.JAVASCRIPT,
            '.tsx': RuleLanguage.JAVASCRIPT,
            '.php': RuleLanguage.PHP,
            '.html': RuleLanguage.HTML,
            '.htm': RuleLanguage.HTML,
            '.py': RuleLanguage.GENERIC,
            '.java': RuleLanguage.GENERIC,
            '.go': RuleLanguage.GENERIC,
            '.rb': RuleLanguage.GENERIC,
            '.cs': RuleLanguage.GENERIC,
            '.cpp': RuleLanguage.GENERIC,
            '.c': RuleLanguage.GENERIC,
            '.h': RuleLanguage.GENERIC,
        }
        
        return language_map.get(extension, RuleLanguage.GENERIC)
    
    def _check_file_specific_patterns(self, content: str, file_path: Path) -> List[Finding]:
        """Check for patterns specific to certain file types."""
        findings = []
        filename = file_path.name.lower()
        
        for pattern_name, patterns in self.config_file_patterns.items():
            if pattern_name in filename:
                file_findings = self._find_pattern_matches(
                    content, patterns, file_path
                )
                findings.extend(file_findings)
                break
        
        return findings
    
    def _detect_cookies(self, content: str, file_path: Path) -> List[Finding]:
        """Detect leaked cookies in code."""
        findings = []
        
        # Cookie patterns
        cookie_patterns = [
            # Set-Cookie headers
            (r'Set-Cookie:\s*([^=\s]+)=([^;]+)', 
             "Set-Cookie Header", Severity.MEDIUM, Category.COOKIE_LEAK),
            
            # Cookie variables in JavaScript
            (r'(?:var|let|const)\s+\w*[Cc]ookie\s*=\s*["\'][^"\']+["\']',
             "Hardcoded Cookie", Severity.MEDIUM, Category.COOKIE_LEAK),
            
            # document.cookie assignments
            (r'document\.cookie\s*=\s*["\'][^"\']+["\']',
             "Document Cookie Assignment", Severity.MEDIUM, Category.COOKIE_LEAK),
            
            # Cookie in PHP
            (r'\$_COOKIE\[["\'][^"\']+["\']\]',
             "PHP Cookie Access", Severity.LOW, Category.COOKIE_LEAK),
        ]
        
        cookie_findings = self._find_pattern_matches(
            content, cookie_patterns, file_path
        )
        findings.extend(cookie_findings)
        
        return findings
    
    def _detect_hardcoded_credentials(self, content: str, file_path: Path) -> List[Finding]:
        """Detect hardcoded credentials."""
        findings = []
        
        # Common credential variable names
        credential_patterns = [
            # Username/password patterns
            (r'(?i)(username|user|login)\s*[:=]\s*["\'][^"\']+["\']',
             "Hardcoded Username", Severity.MEDIUM, Category.HARDCODED_CREDENTIAL),
            
            (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']+["\']',
             "Hardcoded Password", Severity.HIGH, Category.HARDCODED_CREDENTIAL),
            
            # Database connection strings
            (r'(?i)(connectionString|connStr|connString)\s*[:=]\s*["\'][^"\']+["\']',
             "Database Connection String", Severity.CRITICAL, Category.HARDCODED_CREDENTIAL),
            
            (r'jdbc:[^"\']+["\']',
             "JDBC Connection String", Severity.CRITICAL, Category.HARDCODED_CREDENTIAL),
            
            # OAuth patterns
            (r'(?i)(client_id|client_secret|redirect_uri)\s*[:=]\s*["\'][^"\']+["\']',
             "OAuth Credential", Severity.HIGH, Category.API_KEY_EXPOSURE),
        ]
        
        credential_findings = self._find_pattern_matches(
            content, credential_patterns, file_path
        )
        findings.extend(credential_findings)
        
        return findings
    
    def pre_process_content(self, content: str) -> str:
        """Pre-process content for better pattern matching."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remove HTML comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """Filter false positives and adjust findings."""
        filtered_findings = []
        
        for finding in findings:
            # Skip false positives
            if self._is_false_positive(finding):
                logger.debug(f"Filtered false positive: {finding.title}")
                continue
            
            # Adjust confidence for certain patterns
            finding.confidence = self._adjust_confidence(finding)
            
            # Adjust severity for test/debug files
            finding.severity = self._adjust_severity(finding, context)
            
            filtered_findings.append(finding)
        
        return filtered_findings
    
    def _is_false_positive(self, finding: Finding) -> bool:
        """Check if finding is likely a false positive."""
        code_snippet = finding.location.code_snippet or ""
        title = finding.title
        
        # Common false positives
        false_positives = [
            # Example/test data
            (r'example\.com', "Email Address in Code"),
            (r'test@example\.com', "Email Address in Code"),
            (r'123-456-7890', "Phone Number in Code"),
            
            # Comments mentioning keys
            (r'//.*API_KEY.*', "API Key"),
            (r'#.*API_KEY.*', "API Key"),
            (r'<!--.*API_KEY.*-->', "API Key"),
            
            # Configuration examples
            (r'ENV\s+EXAMPLE=', "Environment Variable"),
            (r'ARG\s+BUILD_ARG=', "Docker Build Argument"),
            
            # Dummy/placeholder values
            (r'["\']YOUR_.*_HERE["\']', "Hardcoded Credential"),
            (r'["\']changeme["\']', "Hardcoded Credential"),
            (r'["\']password123["\']', "Hardcoded Password"),
            
            # Test/localhost IPs
            (r'127\.0\.0\.1', "Hardcoded IP Address"),
            (r'192\.168\.', "Hardcoded IP Address"),
            (r'10\.', "Hardcoded IP Address"),
            (r'172\.(1[6-9]|2[0-9]|3[0-1])\.', "Hardcoded IP Address"),
            
            # Mock/test cookies
            (r'sessionid=test', "Set-Cookie Header"),
            (r'cookie="test"', "Hardcoded Cookie"),
        ]
        
        for pattern, affected_title in false_positives:
            if affected_title == title and re.search(pattern, code_snippet, re.IGNORECASE):
                return True
        
        return False
    
    def _adjust_confidence(self, finding: Finding) -> float:
        """Adjust confidence based on context."""
        confidence = finding.confidence
        code_snippet = finding.location.code_snippet or ""
        
        # Increase confidence for certain indicators
        if re.search(r'\b(prod|production|live|real)\b', code_snippet, re.IGNORECASE):
            confidence = min(confidence + 0.2, 1.0)
        
        # Decrease confidence for test indicators
        if re.search(r'\b(test|mock|fake|example|sample|dummy)\b', code_snippet, re.IGNORECASE):
            confidence = max(confidence - 0.3, 0.1)
        
        return confidence
    
    def _adjust_severity(self, finding: Finding, context: ScanContext) -> Severity:
        """Adjust severity based on context."""
        original_severity = finding.severity
        code_snippet = finding.location.code_snippet or ""
        
        # Downgrade severity for test files
        if finding.location.file_path and any(
            test_pattern in finding.location.file_path.lower()
            for test_pattern in ['test_', '_test.', 'spec.', '.spec.', 'mock.', 'stub.']
        ):
            if original_severity == Severity.CRITICAL:
                return Severity.MEDIUM
            elif original_severity == Severity.HIGH:
                return Severity.LOW
        
        return original_severity
