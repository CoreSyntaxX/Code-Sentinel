"""
JavaScript security analyzer.
Detects DOM XSS, unsafe functions, and other JS vulnerabilities.
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from models.finding import Finding, Severity, Category
from models.scan_context import ScanContext
from models.rule import RuleLanguage
from analyzers.base_analyzer import BaseAnalyzer
from .dom_sink_detector import DOMSinkDetector
from .ast_parser import JSASTParser


logger = logging.getLogger(__name__)


class JavaScriptAnalyzer(BaseAnalyzer):
    """
    Analyzer for JavaScript files.
    Detects DOM-based XSS, unsafe functions, and other JS security issues.
    """
    
    def __init__(self):
        super().__init__()
        self.dom_sink_detector = DOMSinkDetector()
        self.ast_parser = JSASTParser()
        self._is_ast_available = self._check_ast_availability()
        
        # DOM XSS sink patterns (direct assignments)
        self.dom_sinks = {
            'innerHTML': {
                'patterns': [
                    r'\.innerHTML\s*=',
                    r'innerHTML\s*=\s*',
                    r'setAttribute\([^)]*["\']innerHTML["\'][^)]*\)',
                ],
                'severity': Severity.HIGH,
                'description': 'Direct assignment to innerHTML can lead to DOM XSS',
                'remediation': 'Use textContent instead or sanitize with DOMPurify',
            },
            'outerHTML': {
                'patterns': [
                    r'\.outerHTML\s*=',
                    r'outerHTML\s*=\s*',
                ],
                'severity': Severity.HIGH,
                'description': 'Direct assignment to outerHTML can lead to DOM XSS',
                'remediation': 'Use textContent or createElement/appendChild',
            },
            'document.write': {
                'patterns': [
                    r'document\.write\s*\(',
                    r'document\.writeln\s*\(',
                ],
                'severity': Severity.HIGH,
                'description': 'document.write() with user input can cause XSS',
                'remediation': 'Avoid document.write() with dynamic content',
            },
        }
        
        # Dangerous JavaScript functions
        self.dangerous_functions = {
            'eval': {
                'patterns': [r'eval\s*\('],
                'severity': Severity.CRITICAL,
                'description': 'eval() executes arbitrary code and is dangerous',
                'remediation': 'Avoid eval(), use JSON.parse() or Function() with caution',
            },
            'Function constructor': {
                'patterns': [r'new\s+Function\s*\('],
                'severity': Severity.HIGH,
                'description': 'Function constructor can execute arbitrary code',
                'remediation': 'Avoid dynamic code generation with Function()',
            },
            'setTimeout/setInterval with string': {
                'patterns': [
                    r'setTimeout\s*\(\s*["\'][^"\']+["\']',
                    r'setInterval\s*\(\s*["\'][^"\']+["\']',
                ],
                'severity': Severity.MEDIUM,
                'description': 'setTimeout/setInterval with string executes code as eval',
                'remediation': 'Pass function reference instead of string',
            },
            'execScript': {
                'patterns': [r'execScript\s*\('],
                'severity': Severity.CRITICAL,
                'description': 'execScript() is similar to eval() and dangerous',
                'remediation': 'Avoid execScript()',
            },
        }
        
        # jQuery-specific vulnerabilities
        self.jquery_sinks = {
            'html()': {
                'patterns': [r'\.html\s*\('],
                'severity': Severity.HIGH,
                'description': 'jQuery .html() with user input can cause XSS',
                'remediation': 'Use .text() for text content or sanitize input',
            },
            'append/prepend': {
                'patterns': [
                    r'\.append\s*\(',
                    r'\.prepend\s*\(',
                    r'\.before\s*\(',
                    r'\.after\s*\(',
                ],
                'severity': Severity.MEDIUM,
                'description': 'jDOM manipulation with user input can cause XSS',
                'remediation': 'Sanitize user input before DOM manipulation',
            },
        }
    
    def _initialize_supported_formats(self):
        """Initialize supported file extensions and languages for JavaScript."""
        self.supported_extensions = {
            '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'
        }
        self.supported_languages = {
            RuleLanguage.JAVASCRIPT
        }
    
    def get_name(self) -> str:
        return "JavaScriptAnalyzer"
    
    def _check_ast_availability(self) -> bool:
        """Check if AST parsing is available."""
        try:
            import esprima
            return True
        except ImportError:
            logger.warning("esprima not installed. AST analysis will be disabled.")
            return False
    
    def analyze(self, file_path: Path, content: str, context: ScanContext) -> List[Finding]:
        """
        Analyze JavaScript file for security vulnerabilities.
        """
        findings = []
        
        # Skip if file is empty or too small
        if len(content.strip()) < 10:
            return findings
        
        logger.debug(f"Analyzing JavaScript file: {file_path}")
        
        # Pre-process content
        processed_content = self.pre_process_content(content)
        
        # 1. Check for DOM XSS sinks
        findings.extend(self._analyze_dom_xss(file_path, processed_content, context))
        
        # 2. Check for dangerous functions
        findings.extend(self._analyze_dangerous_functions(file_path, processed_content))
        
        # 3. Check for jQuery vulnerabilities
        findings.extend(self._analyze_jquery_vulnerabilities(file_path, processed_content))
        
        # 4. Check for prototype pollution
        findings.extend(self._analyze_prototype_pollution(file_path, processed_content))
        
        # 5. Check for unsafe object assignments
        findings.extend(self._analyze_unsafe_assignments(file_path, processed_content))
        
        # 6. Check for client-side secrets
        findings.extend(self._analyze_client_secrets(file_path, processed_content))
        
        # 7. AST-based analysis (if available)
        if self._is_ast_available and context.settings.mode.value != "fast":
            try:
                ast_findings = self._analyze_with_ast(file_path, processed_content, context)
                findings.extend(ast_findings)
            except Exception as e:
                logger.warning(f"AST analysis failed for {file_path}: {e}")
        
        # Post-process findings
        findings = self.post_process_findings(findings, context)
        
        logger.debug(f"Found {len(findings)} issues in {file_path}")
        return findings
    
    def _analyze_dom_xss(self, file_path: Path, content: str, context: ScanContext) -> List[Finding]:
        """Analyze for DOM-based XSS vulnerabilities."""
        findings = []
        
        for sink_name, sink_info in self.dom_sinks.items():
            for pattern in sink_info['patterns']:
                pattern_findings = self._find_pattern_in_content(
                    pattern=pattern,
                    content=content,
                    file_path=file_path,
                    category=Category.DOM_XSS,
                    severity=sink_info['severity'],
                    title=f"Unsafe {sink_name} Usage",
                    description=sink_info['description'],
                    recommendation=sink_info['remediation'],
                    rule_id=f"JS-DOM-XSS-{sink_name.upper()}",
                )
                findings.extend(pattern_findings)
        
        # Use DOM sink detector for more advanced analysis
        dom_findings = self.dom_sink_detector.detect(content, file_path, context)
        findings.extend(dom_findings)
        
        return findings
    
    def _analyze_dangerous_functions(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for dangerous JavaScript function usage."""
        findings = []
        
        for func_name, func_info in self.dangerous_functions.items():
            for pattern in func_info['patterns']:
                pattern_findings = self._find_pattern_in_content(
                    pattern=pattern,
                    content=content,
                    file_path=file_path,
                    category=Category.DOM_XSS,
                    severity=func_info['severity'],
                    title=f"Dangerous Function: {func_name}",
                    description=func_info['description'],
                    recommendation=func_info['remediation'],
                    rule_id=f"JS-DANGEROUS-{func_name.upper().replace(' ', '_')}",
                )
                findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_jquery_vulnerabilities(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for jQuery-specific vulnerabilities."""
        findings = []
        
        # Check if jQuery is used
        jquery_patterns = [
            r'\$\(',                    # $(
            r'jQuery\(',                # jQuery(
            r'require\(["\']jquery["\']',  # require('jquery')
            r'import.*from.*["\']jquery["\']',  # import from 'jquery'
        ]
        
        uses_jquery = any(re.search(pattern, content, re.IGNORECASE) 
                         for pattern in jquery_patterns)
        
        if not uses_jquery:
            return findings
        
        logger.debug(f"jQuery detected in {file_path}")
        
        # Check for jQuery vulnerabilities
        for sink_name, sink_info in self.jquery_sinks.items():
            for pattern in sink_info['patterns']:
                pattern_findings = self._find_pattern_in_content(
                    pattern=pattern,
                    content=content,
                    file_path=file_path,
                    category=Category.DOM_XSS,
                    severity=sink_info['severity'],
                    title=f"jQuery {sink_name} with User Input",
                    description=sink_info['description'],
                    recommendation=sink_info['remediation'],
                    rule_id=f"JS-JQUERY-{sink_name.upper().replace('()', '')}",
                )
                findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_prototype_pollution(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for prototype pollution vulnerabilities."""
        findings = []
        
        # Common prototype pollution patterns
        pollution_patterns = [
            # Direct __proto__ assignment
            (r'__proto__\s*[:=]', Severity.CRITICAL),
            # constructor.prototype assignment
            (r'constructor\.prototype\s*[:=]', Severity.CRITICAL),
            # Explicit prototype mutation APIs
            (r'Object\.setPrototypeOf\s*\(', Severity.HIGH),
        ]
        
        for pattern, severity in pollution_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.DOM_XSS,  # Could be a new category
                severity=severity,
                title="Potential Prototype Pollution",
                description="Prototype pollution can lead to security vulnerabilities like remote code execution.",
                recommendation="Avoid merging user-controlled objects or use libraries with prototype pollution protection.",
                rule_id="JS-PROTOTYPE-POLLUTION",
            )
            # Only keep lines that indicate external/user-controlled data flow.
            for finding in pattern_findings:
                snippet = (finding.location.code_snippet or "").lower()
                if any(token in snippet for token in ["user", "input", "req.", "params", "query", "body"]):
                    findings.append(finding)
        
        return findings
    
    def _analyze_unsafe_assignments(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for unsafe assignments to global objects."""
        findings = []
        
        # Unsafe global assignments
        global_assignments = [
            (r'window\.location\s*=', Severity.MEDIUM, "Unsafe window.location assignment"),
            (r'window\.location\.href\s*=', Severity.MEDIUM, "Unsafe location.href assignment"),
            (r'document\.location\s*=', Severity.MEDIUM, "Unsafe document.location assignment"),
            (r'document\.domain\s*=', Severity.MEDIUM, "Unsafe document.domain assignment"),
            (r'document\.cookie\s*=', Severity.MEDIUM, "Unsafe document.cookie assignment"),
        ]
        
        for pattern, severity, title in global_assignments:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.DOM_XSS,
                severity=severity,
                title=title,
                description=f"{title} can be exploited by attackers.",
                recommendation="Validate and sanitize user input before assignment.",
                rule_id="JS-UNSAFE-ASSIGNMENT",
            )
            for finding in pattern_findings:
                snippet = (finding.location.code_snippet or "").lower()
                if any(token in snippet for token in ["user", "input", "req.", "params", "query", "search", "hash"]):
                    findings.append(finding)
        
        return findings
    
    def _analyze_client_secrets(self, file_path: Path, content: str) -> List[Finding]:
        """Analyze for client-side secrets and credentials."""
        findings = []
        
        # Common client-side secret patterns
        secret_patterns = [
            # API keys in JavaScript
            (r'(?i)(api[_-]?key|access[_-]?token)\s*[:=]\s*[\'"][^\'"]{20,}[\'"]', 
             Severity.CRITICAL, "Client-side API Key Exposure"),
            
            # OAuth client secrets (should never be in client-side code)
            (r'(?i)(client[_-]?secret)\s*[:=]\s*[\'"][^\'"]{10,}[\'"]', 
             Severity.CRITICAL, "OAuth Client Secret in Client Code"),
            
            # Database credentials in client code
            (r'(?i)(db[_-]?(pass|password|pwd)|database[_-]?(pass|password))\s*[:=]\s*[\'"][^\'"]+[\'"]', 
             Severity.CRITICAL, "Database Credentials in Client Code"),
            
            # Encryption keys in client code
            (r'(?i)(encryption[_-]?key|secret[_-]?key)\s*[:=]\s*[\'"][^\'"]{10,}[\'"]', 
             Severity.HIGH, "Encryption Key in Client Code"),
        ]
        
        for pattern, severity, title in secret_patterns:
            pattern_findings = self._find_pattern_in_content(
                pattern=pattern,
                content=content,
                file_path=file_path,
                category=Category.API_KEY_EXPOSURE,
                severity=severity,
                title=title,
                description="Sensitive credentials should never be exposed in client-side code.",
                recommendation="Move secrets to server-side environment variables or use secure authentication methods.",
                rule_id="JS-CLIENT-SECRET",
            )
            findings.extend(pattern_findings)
        
        return findings
    
    def _analyze_with_ast(self, file_path: Path, content: str, context: ScanContext) -> List[Finding]:
        """Use AST parsing for deeper analysis."""
        try:
            return self.ast_parser.analyze(content, file_path, context)
        except Exception as e:
            logger.warning(f"AST parsing failed for {file_path}: {e}")
            return []
    
    def pre_process_content(self, content: str) -> str:
        """Pre-process JavaScript content for analysis."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments (simple approach)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remove template literal placeholders to simplify patterns
        content = re.sub(r'\${[^}]*}', '', content)
        
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """Post-process findings to reduce false positives."""
        filtered_findings = []
        
        for finding in findings:
            # Skip certain common false positives
            if self._is_false_positive(finding):
                logger.debug(f"Filtered false positive: {finding.title} at line {finding.location.line_start}")
                continue
            
            # Adjust confidence based on context
            finding.confidence = self._adjust_confidence(finding)
            
            filtered_findings.append(finding)
        
        return filtered_findings
    
    def _is_false_positive(self, finding: Finding) -> bool:
        """Check if a finding is likely a false positive."""
        code_snippet = finding.location.code_snippet or ""
        
        # Common false positive patterns
        false_positive_patterns = [
            # innerHTML with hardcoded safe values
            r'innerHTML\s*=\s*["\']<[^>]+>["\']',  # Simple HTML tags
            r'innerHTML\s*=\s*["\'][^"\']*[^a-zA-Z0-9][^"\']*["\']',  # No user input indicators
            
            # eval with JSON.parse (common pattern)
            r'eval\s*\(\s*JSON\.parse',
            
            # Safe uses of dangerous functions in comments or strings
            r'["\'].*eval.*["\']',  # String containing "eval"
            r'//.*eval',  # Comment about eval
            
            # Test/mock code
            r'(test|mock|example|demo).*\.innerHTML',
            r'//.*test.*innerHTML',
        ]
        
        for pattern in false_positive_patterns:
            if re.search(pattern, code_snippet, re.IGNORECASE):
                return True
        
        return False
    
    def _adjust_confidence(self, finding: Finding) -> float:
        """Adjust confidence based on context and heuristics."""
        confidence = finding.confidence
        
        # Reduce confidence for common patterns that might be safe
        code_snippet = finding.location.code_snippet or ""
        
        # Increase confidence for clear vulnerabilities
        if "userInput" in code_snippet or "req.body" in code_snippet:
            confidence = min(confidence + 0.2, 1.0)
        
        # Reduce confidence for likely safe patterns
        if re.search(r'innerHTML\s*=\s*["\'][^"\']*text only[^"\']*["\']', code_snippet, re.IGNORECASE):
            confidence = max(confidence - 0.3, 0.3)
        
        return confidence
