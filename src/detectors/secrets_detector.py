"""
Detector for secrets, API keys, and other sensitive data.
Uses regex patterns and entropy analysis.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
import re
import logging
import math

from models.finding import Finding, Severity, Category
from models.scan_context import ScanContext
from detectors.base_detector import BaseDetector


logger = logging.getLogger(__name__)


class SecretsDetector(BaseDetector):
    """
    Detector for secrets, API keys, tokens, and other sensitive information.
    """
    
    def __init__(self):
        super().__init__()
        self.confidence = 0.8
        
        # Service-specific secret patterns
        self.service_patterns = [
            # Stripe
            (r'(?i)sk_(live|test)_[a-z0-9]{24}', 
             "Stripe Secret Key", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            (r'(?i)pk_(live|test)_[a-z0-9]{24}', 
             "Stripe Publishable Key", Severity.MEDIUM, Category.API_KEY_EXPOSURE),
            
            # AWS
            (r'(?i)(aws|amazon).{0,30}(access|api).{0,10}[:=]\s*["\']?AKIA[0-9A-Z]{16}["\']?', 
             "AWS Access Key ID", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            (r'(?i)(aws|amazon).{0,30}(secret|access).{0,10}[:=]\s*["\']?[A-Za-z0-9/+=]{40}["\']?', 
             "AWS Secret Access Key", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            
            # Google
            (r'AIza[0-9A-Za-z\-_]{35}', 
             "Google API Key", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            (r'ya29\.[0-9A-Za-z\-_]+', 
             "Google OAuth Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # GitHub
            (r'ghp_[0-9a-zA-Z]{36}', 
             "GitHub Personal Access Token", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            (r'github_pat_[0-9a-zA-Z_]{82}', 
             "GitHub Fine-grained Token", Severity.CRITICAL, Category.API_KEY_EXPOSURE),
            
            # Slack
            (r'xox[baprs]-[0-9a-zA-Z]{10,48}', 
             "Slack API Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            (r'xoxe-1-[0-9a-zA-Z]{147}', 
             "Slack Legacy Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # Facebook
            (r'EAACEdEose0cBA[0-9A-Za-z]+', 
             "Facebook Access Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # Twitter
            (r'[tT][wW][iI][tT][tT][eE][rR].*[1-9][0-9]+-[0-9a-zA-Z]{40}', 
             "Twitter API Key", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # Heroku
            (r'[hH][eE][rR][oO][kK][uU].*[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}', 
             "Heroku API Key", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # Mailgun
            (r'key-[0-9a-f]{32}', 
             "Mailgun API Key", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # Twilio
            (r'SK[0-9a-fA-F]{32}', 
             "Twilio API Key", Severity.HIGH, Category.API_KEY_EXPOSURE),
            (r'AC[0-9a-fA-F]{32}', 
             "Twilio Account SID", Severity.MEDIUM, Category.API_KEY_EXPOSURE),
            
            # Square
            (r'sq0atp-[0-9A-Za-z\-_]{22}', 
             "Square Access Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            (r'sq0csp-[0-9A-Za-z\-_]{43}', 
             "Square OAuth Secret", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # PayPal
            (r'access_token\$production\$[0-9a-z]{16}\$[0-9a-f]{32}', 
             "PayPal Access Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # SendGrid
            (r'SG\.[0-9A-Za-z\-_]{22}\.[0-9A-Za-z\-_]{43}', 
             "SendGrid API Key", Severity.HIGH, Category.API_KEY_EXPOSURE),
        ]
        
        # Generic secret patterns
        self.generic_patterns = [
            # API keys (generic)
            (r'(?i)(api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*["\'][^\'"]{20,}["\']', 
             "Generic API Key", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # Bearer tokens
            (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 
             "Bearer Token", Severity.HIGH, Category.API_KEY_EXPOSURE),
            
            # Basic auth (base64 encoded)
            (r'Basic\s+[A-Za-z0-9+/]+=*', 
             "Basic Authentication", Severity.MEDIUM, Category.API_KEY_EXPOSURE),
            
            # Private keys
            (r'-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----[A-Za-z0-9+/=\s\n]+-----END[ A-Z0-9_-]*PRIVATE KEY-----', 
             "Private Key", Severity.CRITICAL, Category.SECRET_LEAK),
            
            # Certificates
            (r'-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\s\n]+-----END CERTIFICATE-----', 
             "SSL Certificate", Severity.MEDIUM, Category.SECRET_LEAK),
            
            # Passwords in connection strings
            (r'(?i)password=[^&\s"\']+', 
             "Password in Connection String", Severity.HIGH, Category.HARDCODED_CREDENTIAL),
        ]
        
        # Common false positive patterns
        self.false_positive_patterns = [
            # Example/test keys
            (r'(?i)example[_-]?key', "Example Key"),
            (r'(?i)test[_-]?key', "Test Key"),
            (r'(?i)dummy[_-]?key', "Dummy Key"),
            (r'(?i)placeholder', "Placeholder"),
            
            # Mock data
            (r'sk_test_[a-z0-9]{24}', "Stripe Test Key"),
            (r'pk_test_[a-z0-9]{24}', "Stripe Test Publishable Key"),
            
            # Configuration examples
            (r'YOUR[_-].*[_-]HERE', "Your Key Here"),
            (r'ADD[_-].*[_-]HERE', "Add Key Here"),
            (r'REPLACE[_-].*', "Replace Key"),
            
            # Comments
            (r'//.*key', "Comment about key"),
            (r'#.*key', "Comment about key"),
            (r'<!--.*key.*-->', "HTML Comment about key"),
        ]
        
        # Keywords that indicate a secret (for entropy detection)
        self.secret_keywords = {
            'key', 'secret', 'token', 'password', 'passwd', 'pwd',
            'credential', 'auth', 'authentication', 'private',
            'client_secret', 'api_key', 'access_key', 'secret_key'
        }
    
    def get_name(self) -> str:
        return "SecretsDetector"
    
    def detect(self, content: str, file_path: Path, context: ScanContext) -> List[Finding]:
        """
        Detect secrets in content using patterns and entropy analysis.
        """
        findings = []
        
        # Skip binary files or very large files
        if self._is_binary_content(content):
            return findings
        
        logger.debug(f"Secrets detector analyzing {file_path}")
        
        # Pre-process content
        processed_content = self.pre_process_content(content)
        
        # 1. Check for service-specific secrets
        service_findings = self._find_pattern_matches(
            processed_content,
            self.service_patterns,
            file_path,
        )
        findings.extend(service_findings)
        
        # 2. Check for generic secrets
        generic_findings = self._find_pattern_matches(
            processed_content,
            self.generic_patterns,
            file_path,
        )
        findings.extend(generic_findings)
        
        # 3. Entropy-based detection for high-entropy strings
        if context.settings.mode.value != "fast":
            entropy_findings = self._detect_by_entropy(processed_content, file_path)
            findings.extend(entropy_findings)
        
        # 4. Check for secrets in comments
        comment_findings = self._detect_secrets_in_comments(processed_content, file_path)
        findings.extend(comment_findings)
        
        # Post-process to remove false positives
        findings = self.post_process_findings(findings, context)
        
        logger.debug(f"Secrets detector found {len(findings)} issues in {file_path}")
        return findings
    
    def _is_binary_content(self, content: str) -> bool:
        """Check if content appears to be binary."""
        # Check for null bytes
        if '\x00' in content[:1024]:
            return True
        
        # Check for high ratio of non-printable characters
        sample = content[:4096] if len(content) > 4096 else content
        printable = sum(1 for c in sample if 32 <= ord(c) <= 126 or c in '\n\r\t')
        if len(sample) > 0 and printable / len(sample) < 0.7:
            return True
        
        return False
    
    def _detect_by_entropy(self, content: str, file_path: Path) -> List[Finding]:
        """
        Detect secrets by finding high-entropy strings.
        """
        findings = []
        
        # Find all strings in the content
        # This regex matches quoted strings (single, double, backtick)
        string_pattern = r'["\'`]([^"\'\`\\]*(?:\\.[^"\'\`\\]*)*)["\'`]'
        
        for match in re.finditer(string_pattern, content):
            string_value = match.group(1)
            
            # Skip short strings
            if len(string_value) < 10:
                continue
            
            # Check if string looks like a secret
            if self._looks_like_secret(string_value):
                # Calculate entropy
                entropy = self._calculate_entropy(string_value)
                
                # Skip low entropy strings
                if entropy < 3.5:
                    continue
                
                # Check surrounding context for secret indicators
                context_start = max(0, match.start() - 50)
                context_end = min(len(content), match.end() + 50)
                context = content[context_start:context_end]
                
                if self._has_secret_context(context):
                    line_start = content[:match.start()].count('\n') + 1
                    
                    # Get the line
                    lines = content.split('\n')
                    if line_start <= len(lines):
                        line_content = lines[line_start - 1]
                    else:
                        line_content = ""
                    
                    finding = self._create_finding(
                        title="High-Entropy String (Possible Secret)",
                        severity=Severity.MEDIUM,
                        category=Category.SECRET_LEAK,
                        file_path=file_path,
                        line_start=line_start,
                        code_snippet=line_content[:200],
                        description=f"High-entropy string found (entropy: {entropy:.2f}). This may be a secret.",
                        recommendation="Review if this string contains sensitive information and secure it if necessary.",
                        rule_id="SECRET-ENTROPY",
                        confidence=0.6,  # Lower confidence for entropy-based detection
                    )
                    
                    findings.append(finding)
        
        return findings
    
    def _looks_like_secret(self, string: str) -> bool:
        """Check if a string looks like it could be a secret."""
        # Skip common non-secret patterns
        if re.match(r'^[0-9]+$', string):  # Just numbers
            return False
        if re.match(r'^[a-f0-9]{32}$', string, re.IGNORECASE):  # MD5 hash
            return False
        if re.match(r'^[a-f0-9]{40}$', string, re.IGNORECASE):  # SHA-1 hash
            return False
        if re.match(r'^[a-f0-9]{64}$', string, re.IGNORECASE):  # SHA-256 hash
            return False
        
        # Check for common secret patterns
        if re.search(r'[A-Z]', string) and re.search(r'[a-z]', string) and re.search(r'[0-9]', string):
            return True
        
        return False
    
    def _has_secret_context(self, context: str) -> bool:
        """Check if context contains words indicating a secret."""
        context_lower = context.lower()
        
        # Check for secret-related keywords
        for keyword in self.secret_keywords:
            if keyword in context_lower:
                return True
        
        # Check for assignment patterns
        if re.search(r'(?i)(key|secret|token|password)\s*[:=]', context):
            return True
        
        return False
    
    def _detect_secrets_in_comments(self, content: str, file_path: Path) -> List[Finding]:
        """Detect secrets that are commented out but still visible."""
        findings = []
        
        # Extract comments
        comment_patterns = [
            (r'//(.*)$', "Single-line comment"),  # C/Java/JavaScript style
            (r'#(.*)$', "Hash comment"),  # Python/Shell style
            (r'<!--(.*?)-->', "HTML comment"),  # HTML style
            (r'/\*(.*?)\*/', "Multi-line comment"),  # C/Java/JavaScript style
        ]
        
        for pattern, comment_type in comment_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                comment_text = match.group(1)
                
                # Check if comment contains potential secrets
                secret_findings = self._check_comment_for_secrets(
                    comment_text, comment_type, match, content, file_path
                )
                findings.extend(secret_findings)
        
        return findings
    
    def _check_comment_for_secrets(
        self, 
        comment_text: str, 
        comment_type: str, 
        match: re.Match,
        content: str,
        file_path: Path
    ) -> List[Finding]:
        """Check a comment for potential secrets."""
        findings = []
        
        # Check for service patterns in comments
        for pattern, title, severity, category in self.service_patterns:
            if re.search(pattern, comment_text, re.IGNORECASE):
                line_start = content[:match.start()].count('\n') + 1
                
                # Get the line
                lines = content.split('\n')
                if line_start <= len(lines):
                    line_content = lines[line_start - 1]
                else:
                    line_content = ""
                
                finding = self._create_finding(
                    title=f"Secret in {comment_type}: {title}",
                    severity=severity,
                    category=category,
                    file_path=file_path,
                    line_start=line_start,
                    code_snippet=line_content[:200],
                    description=f"Potential {title.lower()} found in a comment.",
                    recommendation="Remove sensitive information from comments.",
                    rule_id="SECRET-IN-COMMENT",
                    confidence=0.9,
                )
                
                findings.append(finding)
        
        return findings
    
    def pre_process_content(self, content: str) -> str:
        """Pre-process content for secret detection."""
        # For secret detection, we want to keep comments
        # (since secrets can be in comments)
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """Filter false positives and adjust findings."""
        filtered_findings = []
        
        for finding in findings:
            # Skip if it's a known false positive
            if self._is_false_positive(finding):
                logger.debug(f"Filtered false positive secret: {finding.title}")
                continue
            
            # Check if it's a test/staging key
            if self._is_test_key(finding):
                # Downgrade severity for test keys
                if finding.severity == Severity.CRITICAL:
                    finding.severity = Severity.LOW
                    finding.confidence = 0.3
                    finding.description += " (Appears to be a test/staging key)"
                elif finding.severity == Severity.HIGH:
                    finding.severity = Severity.LOW
                    finding.confidence = 0.3
            
            filtered_findings.append(finding)
        
        return filtered_findings
    
    def _is_false_positive(self, finding: Finding) -> bool:
        """Check if finding is a false positive."""
        code_snippet = finding.location.code_snippet or ""
        title = finding.title
        
        # Check against false positive patterns
        for pattern, affected_title in self.false_positive_patterns:
            if affected_title in title or affected_title == "Any":
                if re.search(pattern, code_snippet, re.IGNORECASE):
                    return True
        
        return False
    
    def _is_test_key(self, finding: Finding) -> bool:
        """Check if a key appears to be a test/staging key."""
        code_snippet = finding.location.code_snippet or ""
        
        test_indicators = [
            r'_test_',
            r'_staging_',
            r'_dev_',
            r'_development_',
            r'_sandbox_',
            r'\btest\b',
            r'\bstaging\b',
            r'\bdev\b',
            r'\bsandbox\b',
            r'example\.com',
            r'test@',
            r'mock',
            r'dummy',
            r'fake',
            r'sample',
        ]
        
        for indicator in test_indicators:
            if re.search(indicator, code_snippet, re.IGNORECASE):
                return True
        
        return False
