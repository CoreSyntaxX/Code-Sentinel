"""
PHP security analyzer.
Detects SQL injection, command injection, file inclusion, and other PHP vulnerabilities.
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from models.finding import Finding, Severity, Category
from models.scan_context import ScanContext
from models.rule import RuleLanguage
from analyzers.base_analyzer import BaseAnalyzer


logger = logging.getLogger(__name__)


class PHPAnalyzer(BaseAnalyzer):
    """
    Analyzer for PHP files.
    Detects SQL injection, command injection, file inclusion, XSS, and other vulnerabilities.
    """
    
    def __init__(self):
        super().__init__()
        
        # SQL injection patterns
        self.sql_injection_patterns = [
            # Direct user input in SQL
            (r'\$_GET\[[^\]]+\]', Severity.HIGH),
            (r'\$_POST\[[^\]]+\]', Severity.HIGH),
            (r'\$_REQUEST\[[^\]]+\]', Severity.HIGH),
            (r'\$_COOKIE\[[^\]]+\]', Severity.MEDIUM),
            (r'\$_SESSION\[[^\]]+\]', Severity.MEDIUM),
            
            # Common SQL functions with concatenation
            (r'mysql_query\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'mysqli_query\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'pg_query\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'PDO\:\:query\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            
            # SQL string building
            (r'\$sql\s*\.=', Severity.HIGH),
            (r'["\']\s*\.\s*\$', Severity.MEDIUM),
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            # Shell execution with user input
            (r'shell_exec\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'exec\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'system\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'passthru\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'popen\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'proc_open\s*\([^)]*\.\s*\$', Severity.CRITICAL),
            (r'`.*\$.*`', Severity.CRITICAL),  # Backticks with variables
            
            # Dangerous functions even without obvious input
            (r'eval\s*\(', Severity.CRITICAL),
            (r'assert\s*\(', Severity.HIGH),
            (r'create_function\s*\(', Severity.HIGH),
        ]
        
        # File inclusion patterns
        self.file_inclusion_patterns = [
            # Include/require with variables
            (r'(include|require)(_once)?\s*\([^)]*\.\s*\$', Severity.HIGH),
            (r'(include|require)(_once)?\s*\$', Severity.HIGH),
            
            # File operations with user input
            (r'file_get_contents\s*\([^)]*\.\s*\$', Severity.HIGH),
            (r'fopen\s*\([^)]*\.\s*\$', Severity.HIGH),
            (r'readfile\s*\([^)]*\.\s*\$', Severity.HIGH),
            (r'file\s*\([^)]*\.\s*\$', Severity.HIGH),
            
            # File upload handling
            (r'\$_FILES\[', Severity.MEDIUM),
        ]
        
        # XSS patterns in PHP
        self.xss_patterns = [
            # Echo/print with user input without escaping
            (r'echo\s+[^;]*\.\s*(\$_GET|\$_POST|\$_REQUEST)', Severity.HIGH),
            (r'print\s+[^;]*\.\s*(\$_GET|\$_POST|\$_REQUEST)', Severity.HIGH),
            (r'printf\s*\([^)]*\.\s*(\$_GET|\$_POST|\$_REQUEST)', Severity.HIGH),
            
            # Direct output of user input
            (r'<\?php\s+echo\s+\$_GET\[', Severity.HIGH),
            (r'<\?=\s*\$_GET\[', Severity.HIGH),  # Short tag
        ]
        
        # Insecure configuration patterns
        self.configuration_patterns = [
            # Error display enabled
            (r'ini_set\s*\(\s*["\']display_errors["\'][^)]*1', Severity.MEDIUM),
            (r'display_errors\s*=\s*1', Severity.MEDIUM),
            (r'error_reporting\s*\(\s*E_ALL\s*\)', Severity.LOW),
            
            # Magic quotes (deprecated)
            (r'magic_quotes_gpc\s*=', Severity.LOW),
            
            # Register globals (very dangerous)
            (r'register_globals\s*=\s*1', Severity.CRITICAL),
        ]
        
        # Weak cryptography patterns
        self.crypto_patterns = [
            # Weak hash functions
            (r'md5\s*\(', Severity.MEDIUM),
            (r'sha1\s*\(', Severity.MEDIUM),
            (r'crypt\s*\([^)]*["\']DES["\']', Severity.HIGH),
            
            # Weak random functions
            (r'rand\s*\(', Severity.LOW),
            (r'mt_rand\s*\(', Severity.LOW),
            
            # Hardcoded encryption keys
            (r'openssl_encrypt\s*\([^)]*["\'][A-Za-z0-9+/=]{20,}["\']', Severity.HIGH),
        ]
        
        # Secure functions (reduce severity if used)
        self.secure_functions = [
            'mysqli_real_escape_string',
            'PDO::quote',
            'htmlspecialchars',
            'htmlentities',
            'addslashes',
            'filter_var',
            'escapeshellarg',
            'escapeshellcmd',
            'basename',
            'realpath',
        ]
    
    def _initialize_supported_formats(self):
        """Initialize supported file extensions and languages for PHP."""
        self.supported_extensions = {'.php', '.php3', '.php4', '.php5', '.php7', '.phtml'}
        self.supported_languages = {RuleLanguage.PHP}
    
    def get_name(self) -> str:
        return "PHPAnalyzer"
    
    def analyze(self, file_path: Path, content: str, context: ScanContext) -> List[Finding]:
        """
        Analyze PHP file for security vulnerabilities.
        """
        findings = []
        
        # Skip if not PHP file or empty
        if not content.strip().startswith('<?php') and '<?=' not in content:
            # Might be a template file, check extension
            if file_path.suffix.lower() not in self.supported_extensions:
                return findings
        
        logger.debug(f"Analyzing PHP file: {file_path}")
        
        # Pre-process content
        processed_content = self.pre_process_content(content)
        
        # 1. Check for SQL injection vulnerabilities
        findings.extend(self._analyze_sql_injection(file_path, processed_content))
        
        # 2. Check for command injection vulnerabilities
        findings.extend(self._analyze_command_injection(file_path, processed_content))
        
        # 3. Check for file inclusion vulnerabilities
        findings.extend(self._analyze_file_inclusion(file_path, processed_content))
        
        # 4. Check for XSS vulnerabilities
        findings.extend(self._analyze_xss(file_path, processed_content))
        
        # 5. Check for insecure configuration
        findings.extend(self._analyze_configuration(file_path, processed_content))
        
        # 6. Check for weak cryptography
        findings.extend(self._analyze_cryptography(file_path, processed_content))
        
        # 7. Check for hardcoded credentials
        findings.extend(self._analyze_hardcoded_credentials(file_path, processed_content))
        
        # Post-process findings
        findings = self.post_process_findings(findings, context)
        
        logger.debug(f"Found {len(findings)} issues in {file_path}")
        return findings
    
    def _analyze_sql_injection(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for SQL injection vulnerabilities."""
        findings = []
        
        for pattern, severity in self.sql_injection_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.SQL_INJECTION,
                severity=severity,
                title="Potential SQL Injection",
                description="User input used directly in SQL query without proper sanitization.",
                recommendation="Use prepared statements (PDO or MySQLi) with parameterized queries.",
                rule_id="PHP-SQL-INJECTION",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_command_injection(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for command injection vulnerabilities."""
        findings = []
        
        for pattern, severity in self.command_injection_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.COMMAND_INJECTION,
                severity=severity,
                title="Potential Command Injection",
                description="User input used in shell commands without proper escaping.",
                recommendation="Use escapeshellarg() or escapeshellcmd() on user input before shell execution.",
                rule_id="PHP-COMMAND-INJECTION",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_file_inclusion(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for file inclusion vulnerabilities."""
        findings = []
        
        for pattern, severity in self.file_inclusion_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.PATH_TRAVERSAL,
                severity=severity,
                title="Potential File Inclusion",
                description="User input used in file operations without validation.",
                recommendation="Validate and sanitize file paths. Use basename() and realpath() for security.",
                rule_id="PHP-FILE-INCLUSION",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_xss(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for XSS vulnerabilities."""
        findings = []
        
        for pattern, severity in self.xss_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.REFLECTED_XSS,
                severity=severity,
                title="Potential Cross-Site Scripting (XSS)",
                description="User input echoed to output without proper escaping.",
                recommendation="Use htmlspecialchars() or htmlentities() when outputting user input.",
                rule_id="PHP-XSS",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_configuration(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for insecure PHP configuration."""
        findings = []
        
        for pattern, severity in self.configuration_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.INSECURE_CONFIG,
                severity=severity,
                title="Insecure PHP Configuration",
                description="Insecure PHP settings that can leak information or enable attacks.",
                recommendation="Disable error display in production. Use secure default settings.",
                rule_id="PHP-INSECURE-CONFIG",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_cryptography(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for weak cryptography usage."""
        findings = []
        
        for pattern, severity in self.crypto_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.WEAK_CRYPTO,
                severity=severity,
                title="Weak Cryptography",
                description="Weak cryptographic functions or hardcoded keys detected.",
                recommendation="Use strong hash functions (SHA-256, bcrypt) and proper random generators (random_int()).",
                rule_id="PHP-WEAK-CRYPTO",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_hardcoded_credentials(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for hardcoded credentials in PHP."""
        findings = []
        
        # Database connection strings
        db_patterns = [
            (r'\$db_(pass(word)?|pwd)\s*=\s*["\'][^"\']+["\']', Severity.CRITICAL),
            (r'\$password\s*=\s*["\'][^"\']+["\']', Severity.HIGH),
            (r'mysql_connect\s*\([^)]*["\'][^"\']+["\'][^)]*["\'][^"\']+["\']', Severity.CRITICAL),
            (r'mysqli_connect\s*\([^)]*["\'][^"\']+["\'][^)]*["\'][^"\']+["\']', Severity.CRITICAL),
            (r'PDO\s*\([^)]*["\'][^"\']+["\'][^)]*["\'][^"\']+["\']', Severity.CRITICAL),
        ]
        
        for pattern, severity in db_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.HARDCODED_CREDENTIAL,
                severity=severity,
                title="Hardcoded Database Credentials",
                description="Database credentials hardcoded in source code.",
                recommendation="Store credentials in environment variables or configuration files outside web root.",
                rule_id="PHP-HARDCODED-CREDS",
            )
            findings.extend(pattern_findings)
        
        # API keys and secrets
        api_patterns = [
            (r'\$api_key\s*=\s*["\'][^"\']{20,}["\']', Severity.CRITICAL),
            (r'\$secret\s*=\s*["\'][^"\']{10,}["\']', Severity.HIGH),
            (r'define\s*\(\s*["\']API_KEY["\'][^)]*["\'][^"\']{20,}["\']', Severity.CRITICAL),
        ]
        
        for pattern, severity in api_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.API_KEY_EXPOSURE,
                severity=severity,
                title="Hardcoded API Key",
                description="API key or secret hardcoded in source code.",
                recommendation="Store API keys in environment variables or secure secret management service.",
                rule_id="PHP-HARDCODED-API-KEY",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def pre_process_content(self, content: str) -> str:
        """Pre-process PHP content for analysis."""
        # Remove PHP tags but keep content
        content = re.sub(r'<\?(php|=)?', '', content)
        content = re.sub(r'\?>', '', content)
        
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """Post-process findings to reduce false positives."""
        filtered_findings = []
        
        for finding in findings:
            # Skip if secure function is used nearby
            if self._has_secure_function_nearby(finding, context):
                logger.debug(f"Filtered finding with secure function: {finding.title}")
                continue
            
            # Adjust severity for certain patterns
            finding.severity = self._adjust_severity(finding)
            
            filtered_findings.append(finding)
        
        return filtered_findings
    
    def _has_secure_function_nearby(self, finding: Finding, context: ScanContext) -> bool:
        """Check if a secure function is used near the finding."""
        # This would require analyzing the actual file content around the finding
        # For now, return False
        return False
    
    def _adjust_severity(self, finding: Finding) -> Severity:
        """Adjust severity based on context."""
        # Default to original severity
        return finding.severity
