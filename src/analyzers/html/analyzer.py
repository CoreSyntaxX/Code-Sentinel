
"""
HTML security analyzer.
Detects XSS vulnerabilities, insecure attributes, and other HTML security issues.
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


class HTMLAnalyzer(BaseAnalyzer):
    """
    Analyzer for HTML files.
    Detects XSS vulnerabilities, insecure attributes, and other HTML security issues.
    """
    
    def __init__(self):
        super().__init__()
        
        # XSS patterns in HTML
        self.xss_patterns = [
            # Inline event handlers with user input patterns
            (r'on\w+\s*=\s*["\'][^"\']*\{\{.*\}\}[^"\']*["\']', Severity.HIGH),  # Template injection
            (r'on\w+\s*=\s*["\'][^"\']*<%.*%>[^"\']*["\']', Severity.HIGH),  # PHP/ERB injection
            
            # JavaScript: URLs with user input
            (r'href\s*=\s*["\']javascript:[^"\']*[+\s\.]\$?[a-zA-Z_][\w]*[^"\']*["\']', Severity.HIGH),
            
            # Unquoted attributes (can lead to XSS)
            (r'<\w+[^>]*\s\w+\s*=\s*[^"\'\s>][^>]*>', Severity.LOW),
        ]
        
        # Insecure attribute patterns
        self.insecure_attributes = [
            # autocomplete not disabled on password fields
            (r'<input[^>]*type\s*=\s*["\']?password["\']?[^>]*autocomplete\s*=\s*["\']?on["\']?[^>]*>', Severity.LOW),
            (r'<input[^>]*type\s*=\s*["\']?password["\']?[^>]*(?<!autocomplete\s*=\s*["\']?off["\']?)[^>]*>', Severity.LOW),
            
            # Cross-Origin Resource Sharing (CORS) misconfigurations
            (r'<meta[^>]*http-equiv\s*=\s*["\']Access-Control-Allow-Origin["\'][^>]*content\s*=\s*["\']\*["\'][^>]*>', Severity.MEDIUM),
            
            # Insecure iframe sandbox
            (r'<iframe[^>]*sandbox\s*=\s*["\'][^"\']*allow-scripts[^"\']*["\'][^>]*>', Severity.MEDIUM),
        ]
        
        # Content Security Policy (CSP) issues
        self.csp_patterns = [
            # Unsafe inline scripts allowed
            (r'<meta[^>]*http-equiv\s*=\s*["\']Content-Security-Policy["\'][^>]*content\s*=\s*["\'][^"\']*unsafe-inline[^"\']*["\'][^>]*>', Severity.MEDIUM),
            (r'<meta[^>]*http-equiv\s*=\s*["\']Content-Security-Policy["\'][^>]*content\s*=\s*["\'][^"\']*unsafe-eval[^"\']*["\'][^>]*>', Severity.MEDIUM),
            
            # Wildcard sources
            (r'<meta[^>]*http-equiv\s*=\s*["\']Content-Security-Policy["\'][^>]*content\s*=\s*["\'][^"\']*\*[^"\']*["\'][^>]*>', Severity.LOW),
        ]
        
        # Information disclosure patterns
        self.info_disclosure_patterns = [
            # Comments containing sensitive information
            (r'<!--\s*(TODO|FIXME|HACK|XXX).*?(password|key|secret|token).*?-->', Severity.MEDIUM),
            (r'<!--\s*[^>]*@author[^>]*-->', Severity.LOW),  # Author information
            (r'<!--\s*[^>]*Version:.*?-->', Severity.LOW),   # Version information
            
            # Hidden form fields with sensitive names
            (r'<input[^>]*type\s*=\s*["\']hidden["\'][^>]*name\s*=\s*["\'][^"\']*(pass|key|secret|token)[^"\']*["\'][^>]*>', Severity.MEDIUM),
            
            # Debug information in attributes
            (r'<\w+[^>]*debug\s*=\s*["\']true["\'][^>]*>', Severity.LOW),
            (r'<\w+[^>]*test\s*=\s*["\']true["\'][^>]*>', Severity.LOW),
        ]
        
        # Template engine injection patterns
        self.template_patterns = [
            # AngularJS injection
            (r'{{.*?}}', Severity.LOW),  # Basic Angular/Handlebars
            
            # PHP in HTML
            (r'<\?php.*?\?>', Severity.HIGH),
            (r'<\?=.*?\?>', Severity.HIGH),
            
            # JSP/JSF expressions
            (r'\${.*?}', Severity.MEDIUM),
            (r'#\{.*?\}', Severity.MEDIUM),
            
            # ASP.NET
            (r'<%.*?%>', Severity.HIGH),
            (r'<%=\s*.*?\s*%>', Severity.HIGH),
        ]
        
        # Script tags analysis
        self.script_patterns = [
            # Inline scripts with potential XSS
            (r'<script[^>]*>[^<]*(\$_GET|\$_POST|\$_REQUEST)[^<]*</script>', Severity.HIGH),
            (r'<script[^>]*>[^<]*location\.(hash|search)[^<]*</script>', Severity.HIGH),
            (r'<script[^>]*>[^<]*document\.(URL|referrer|cookie)[^<]*</script>', Severity.HIGH),
            
            # Script tags with external sources (check for integrity)
            (r'<script[^>]*src\s*=\s*["\'][^"\']*["\'][^>]*(?<!integrity\s*=\s*["\'][^"\']*["\'])[^>]*>', Severity.LOW),
            
            # Script tags without nonce or hash
            (r'<script[^>]*>[^<]*</script>', Severity.LOW),  # Inline script
        ]
    
    def _initialize_supported_formats(self):
        """Initialize supported file extensions and languages for HTML."""
        self.supported_extensions = {'.html', '.htm', '.xhtml', '.jsp', '.asp', '.aspx', '.php'}
        self.supported_languages = {RuleLanguage.HTML}
    
    def get_name(self) -> str:
        return "HTMLAnalyzer"
    
    def analyze(self, file_path: Path, content: str, context: ScanContext) -> List[Finding]:
        """
        Analyze HTML file for security vulnerabilities.
        """
        findings = []
        
        logger.debug(f"Analyzing HTML file: {file_path}")
        
        # Pre-process content
        processed_content = self.pre_process_content(content)
        
        # 1. Check for XSS vulnerabilities
        findings.extend(self._analyze_xss(file_path, processed_content))
        
        # 2. Check for insecure attributes
        findings.extend(self._analyze_insecure_attributes(file_path, processed_content))
        
        # 3. Check for CSP issues
        findings.extend(self._analyze_csp(file_path, processed_content))
        
        # 4. Check for information disclosure
        findings.extend(self._analyze_info_disclosure(file_path, processed_content))
        
        # 5. Check for template injection
        findings.extend(self._analyze_template_injection(file_path, processed_content))
        
        # 6. Check for script tag issues
        findings.extend(self._analyze_script_tags(file_path, processed_content))
        
        # 7. Check for form security issues
        findings.extend(self._analyze_forms(file_path, processed_content))
        
        # 8. Check for iframe security
        findings.extend(self._analyze_iframes(file_path, processed_content))
        
        # Post-process findings
        findings = self.post_process_findings(findings, context)
        
        logger.debug(f"Found {len(findings)} issues in {file_path}")
        return findings
    
    def _analyze_xss(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for XSS vulnerabilities in HTML."""
        findings = []
        
        for pattern, severity in self.xss_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.REFLECTED_XSS,
                severity=severity,
                title="Potential HTML XSS Vulnerability",
                description="HTML attribute or event handler may allow XSS.",
                recommendation="Sanitize user input and use proper escaping for HTML attributes.",
                rule_id="HTML-XSS",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_insecure_attributes(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for insecure HTML attributes."""
        findings = []
        
        for pattern, severity in self.insecure_attributes:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.INSECURE_CONFIG,
                severity=severity,
                title="Insecure HTML Attribute",
                description="HTML attribute may cause security issues.",
                recommendation="Review and secure the identified attribute.",
                rule_id="HTML-INSECURE-ATTR",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_csp(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze Content Security Policy issues."""
        findings = []
        
        for pattern, severity in self.csp_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.INSECURE_CONFIG,
                severity=severity,
                title="Weak Content Security Policy",
                description="CSP allows unsafe practices that can lead to XSS.",
                recommendation="Implement a strict CSP without 'unsafe-inline' or 'unsafe-eval'.",
                rule_id="HTML-WEAK-CSP",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_info_disclosure(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for information disclosure in HTML."""
        findings = []
        
        for pattern, severity in self.info_disclosure_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.INFORMATION_DISCLOSURE,
                severity=severity,
                title="Information Disclosure in HTML",
                description="HTML contains sensitive information in comments or attributes.",
                recommendation="Remove sensitive information from client-side code.",
                rule_id="HTML-INFO-DISCLOSURE",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_template_injection(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for template injection vulnerabilities."""
        findings = []
        
        for pattern, severity in self.template_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.DOM_XSS,
                severity=severity,
                title="Template Engine Code in HTML",
                description="Server-side code in HTML may indicate template injection risk.",
                recommendation="Ensure proper context-aware escaping for template variables.",
                rule_id="HTML-TEMPLATE-INJECTION",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_script_tags(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze script tags for security issues."""
        findings = []
        
        for pattern, severity in self.script_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.DOM_XSS,
                severity=severity,
                title="Insecure Script Tag",
                description="Script tag may have security issues.",
                recommendation="Use Subresource Integrity (SRI) for external scripts and CSP for inline scripts.",
                rule_id="HTML-INSECURE-SCRIPT",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_forms(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze HTML forms for security issues."""
        findings = []
        
        # Find all form tags
        form_pattern = r'<form[^>]*>.*?</form>'
        
        for match in re.finditer(form_pattern, content, re.IGNORECASE | re.DOTALL):
            form_content = match.group()
            form_start_line = content[:match.start()].count('\n') + 1
            
            # Check for forms without CSRF protection
            if 'method="post"' in form_content.lower():
                if not re.search(r'name\s*=\s*["\'][^"\']*(csrf|token)["\']', form_content, re.IGNORECASE):
                    # Create finding for missing CSRF token
                    location = Location(
                        file_path=str(file_path),
                        line_start=form_start_line,
                        code_snippet=form_content[:200],
                    )
                    
                    finding = Finding(
                        title="Missing CSRF Protection in Form",
                        severity=Severity.MEDIUM,
                        category=Category.INSECURE_CONFIG,
                        location=location,
                        description="POST form missing CSRF token protection.",
                        recommendation="Add CSRF tokens to all state-changing forms.",
                        rule_id="HTML-MISSING-CSRF",
                        confidence=0.8,
                        detector_name=self.name,
                    )
                    
                    findings.append(finding)
            
            # Check for forms with action pointing to external domains
            action_match = re.search(r'action\s*=\s*["\']([^"\']*)["\']', form_content, re.IGNORECASE)
            if action_match:
                action_url = action_match.group(1)
                if action_url.startswith('http://'):
                    # HTTP instead of HTTPS
                    location = Location(
                        file_path=str(file_path),
                        line_start=form_start_line,
                        code_snippet=form_content[:200],
                    )
                    
                    finding = Finding(
                        title="Form Action Uses HTTP Instead of HTTPS",
                        severity=Severity.MEDIUM,
                        category=Category.INSECURE_CONFIG,
                        location=location,
                        description="Form submits data over insecure HTTP connection.",
                        recommendation="Use HTTPS for all form submissions.",
                        rule_id="HTML-FORM-INSECURE-PROTOCOL",
                        confidence=0.9,
                        detector_name=self.name,
                    )
                    
                    findings.append(finding)
        
        return findings
    
    def _analyze_iframes(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze iframe tags for security issues."""
        findings = []
        
        # Find all iframe tags
        iframe_pattern = r'<iframe[^>]*>'
        
        for match in re.finditer(iframe_pattern, content, re.IGNORECASE):
            iframe_content = match.group()
            line_start = content[:match.start()].count('\n') + 1
            
            # Check for missing sandbox attribute
            if 'sandbox' not in iframe_content.lower():
                location = Location(
                    file_path=str(file_path),
                    line_start=line_start,
                    code_snippet=iframe_content,
                )
                
                finding = Finding(
                    title="Iframe Missing Sandbox Attribute",
                    severity=Severity.MEDIUM,
                    category=Category.INSECURE_CONFIG,
                    location=location,
                    description="Iframe without sandbox attribute can be security risk.",
                    recommendation="Add sandbox attribute to iframes to restrict capabilities.",
                    rule_id="HTML-IFRAME-NO-SANDBOX",
                    confidence=0.7,
                    detector_name=self.name,
                )
                
                findings.append(finding)
            
            # Check for iframes with external sources
            src_match = re.search(r'src\s*=\s*["\']([^"\']*)["\']', iframe_content, re.IGNORECASE)
            if src_match:
                src_url = src_match.group(1)
                if src_url.startswith('http://'):
                    # HTTP instead of HTTPS
                    location = Location(
                        file_path=str(file_path),
                        line_start=line_start,
                        code_snippet=iframe_content,
                    )
                    
                    finding = Finding(
                        title="Iframe Uses HTTP Instead of HTTPS",
                        severity=Severity.MEDIUM,
                        category=Category.INSECURE_CONFIG,
                        location=location,
                        description="Iframe loads content over insecure HTTP connection.",
                        recommendation="Use HTTPS for all iframe sources.",
                        rule_id="HTML-IFRAME-INSECURE-PROTOCOL",
                        confidence=0.9,
                        detector_name=self.name,
                    )
                    
                    findings.append(finding)
        
        return findings
    
    def pre_process_content(self, content: str) -> str:
        """Pre-process HTML content for analysis."""
        # Remove CDATA sections (they can contain scripts)
        content = re.sub(r'<!\[CDATA\[.*?\]\]>', '', content, flags=re.DOTALL)
        
        # Normalize whitespace in tags for better regex matching
        content = re.sub(r'<\s*', '<', content)
        content = re.sub(r'\s*>', '>', content)
        
        # Convert to lowercase for case-insensitive matching
        # But keep original for line reporting
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """Post-process findings to reduce false positives."""
        filtered_findings = []
        
        for finding in findings:
            # Check for false positives
            if self._is_false_positive(finding):
                logger.debug(f"Filtered false positive: {finding.title}")
                continue
            
            filtered_findings.append(finding)
        
        return filtered_findings
    
    def _is_false_positive(self, finding: Finding) -> bool:
        """Check if a finding is likely a false positive."""
        code_snippet = finding.location.code_snippet or ""
        
        # Common false positives
        false_positives = [
            # Template patterns in comments
            r'<!--.*{{.*}}.*-->',
            r'<!--.*<%.*%>.*-->',
            
            # Common JavaScript libraries/frameworks
            r'src=["\'].*(jquery|react|vue|angular)\.min\.js["\']',
            
            # Common development patterns
            r'<script>console\.log\(.*\)</script>',
            r'onclick=["\']return false["\']',
            
            # Test/debug code
            r'data-test',
            r'debug="true"',
        ]
        
        for pattern in false_positives:
            if re.search(pattern, code_snippet, re.IGNORECASE):
                return True
        
        return False