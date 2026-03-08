"""
DOM Sink detector for JavaScript - detects data flow to dangerous sinks.
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
import logging

from models.finding import Finding, Severity, Category, Location
from models.scan_context import ScanContext


logger = logging.getLogger(__name__)


class DOMSinkDetector:
    """
    Detects data flow from sources to DOM sinks for XSS analysis.
    """
    
    def __init__(self):
        # DOM XSS sinks (where data becomes code)
        self.dom_sinks = [
            # Standard DOM sinks
            r'\.innerHTML\s*=',
            r'\.outerHTML\s*=',
            r'document\.write\(',
            r'document\.writeln\(',
            r'\.insertAdjacentHTML\(',
            r'eval\(',
            
            # jQuery sinks
            r'\$\([^)]*\)\.html\(',
            r'\$\([^)]*\)\.append\(',
            r'\$\([^)]*\)\.prepend\(',
            
            # React-like frameworks (simplified)
            r'dangerouslySetInnerHTML\s*=',
            
            # Attribute sinks
            r'setAttribute\(\s*["\'](srcdoc|innerHTML)["\']',
        ]
        
        # User input sources
        self.user_sources = [
            # URL parameters
            r'location\.href',
            r'location\.search',
            r'location\.hash',
            r'document\.URL',
            r'document\.referrer',
            r'window\.name',
            
            # Form inputs
            r'document\.forms\[',
            
            # Cookies
            r'document\.cookie',
            
            # Storage
            r'localStorage\.getItem\(',
            r'sessionStorage\.getItem\(',
            r'URLSearchParams\(',
            r'\b(req\.(query|body|params)|querystring|searchParams)\b',
        ]
        
        # Sanitization functions (reduce severity if present)
        self.sanitization_functions = [
            r'encodeURI\(',
            r'encodeURIComponent\(',
            r'escape\(',
            r'DOMPurify\.sanitize\(',
            r'\.textContent\s*=',
            r'\.innerText\s*=',
            r'\.createTextNode\(',
        ]
        
        self.compiled_sinks = [re.compile(pattern, re.IGNORECASE) for pattern in self.dom_sinks]
        self.compiled_sources = [re.compile(pattern, re.IGNORECASE) for pattern in self.user_sources]
        self.compiled_sanitizers = [re.compile(pattern, re.IGNORECASE) for pattern in self.sanitization_functions]
    
    def detect(self, content: str, file_path: Path, context: Optional[ScanContext] = None) -> List[Finding]:
        """
        Detect DOM XSS vulnerabilities with lightweight taint-flow analysis.
        
        Args:
            content: JavaScript content to analyze
            file_path: Path to the file
            
        Returns:
            List of DOM XSS findings
        """
        lines = content.split('\n')
        findings = self._detect_taint_flow(lines, file_path)

        # In deep mode, include proximity-based findings as a fallback.
        if context and context.settings.mode.value == "deep":
            vulnerabilities = self._find_potential_vulnerabilities(content, lines)
            for vuln in vulnerabilities:
                finding = self._create_finding_from_vulnerability(vuln, file_path)
                if finding:
                    findings.append(finding)

        return self._deduplicate_findings(findings)

    def _detect_taint_flow(self, lines: List[str], file_path: Path) -> List[Finding]:
        """Track tainted variables and report unsanitized flow into DOM sinks."""
        findings: List[Finding] = []
        tainted_vars: Set[str] = set()
        sanitized_vars: Set[str] = set()

        assignment_regex = re.compile(
            r'^\s*(?:const|let|var)?\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(.+?)\s*;?\s*$'
        )

        for idx, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            assignment_match = assignment_regex.match(line_stripped)
            if assignment_match:
                var_name = assignment_match.group(1)
                rhs = assignment_match.group(2)

                rhs_has_source = self._contains_source(rhs)
                rhs_has_sanitizer = self._contains_sanitizer(rhs)
                rhs_has_tainted_var = any(
                    re.search(rf'\b{re.escape(name)}\b', rhs) for name in tainted_vars
                )

                if rhs_has_sanitizer:
                    sanitized_vars.add(var_name)
                    tainted_vars.discard(var_name)
                elif rhs_has_source or rhs_has_tainted_var:
                    tainted_vars.add(var_name)
                    sanitized_vars.discard(var_name)

            if not self._contains_sink(line_stripped):
                continue

            sink_expr = self._extract_sink_expression(line_stripped)
            if not sink_expr:
                continue

            has_source = self._contains_source(sink_expr)
            has_sanitizer = self._contains_sanitizer(sink_expr)
            has_tainted_var = any(
                re.search(rf'\b{re.escape(name)}\b', sink_expr) for name in tainted_vars
            )
            has_safe_var = any(
                re.search(rf'\b{re.escape(name)}\b', sink_expr) for name in sanitized_vars
            )

            if (has_source or has_tainted_var) and not has_sanitizer and not has_safe_var:
                finding = Finding(
                    title="DOM-based Cross-Site Scripting (XSS)",
                    severity=Severity.HIGH,
                    category=Category.DOM_XSS,
                    location=Location(
                        file_path=str(file_path),
                        line_start=idx,
                        code_snippet=line_stripped[:200],
                    ),
                    description="Unsanitized user-controlled data flows into a DOM sink.",
                    recommendation="Sanitize input before sink usage. Prefer textContent over HTML sinks.",
                    rule_id="JS-DOM-XSS-TAINT",
                    confidence=0.9,
                    detector_name="DOMSinkDetector",
                    tags=["dom-xss", "taint-flow", "javascript"],
                )
                findings.append(finding)

        return findings

    def _contains_source(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.compiled_sources)

    def _contains_sanitizer(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.compiled_sanitizers)

    def _contains_sink(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.compiled_sinks)

    def _extract_sink_expression(self, line: str) -> str:
        """Extract RHS/argument expression from common sink shapes."""
        assignment_match = re.search(r'=\s*(.+)$', line)
        if assignment_match:
            return assignment_match.group(1)

        call_match = re.search(r'\((.+)\)', line)
        if call_match:
            return call_match.group(1)

        return line

    def _deduplicate_findings(self, findings: List[Finding]) -> List[Finding]:
        """Remove duplicate findings emitted from overlapping analyses."""
        unique: Dict[str, Finding] = {}
        for finding in findings:
            unique[finding.unique_id] = finding
        return list(unique.values())
    
    def _find_potential_vulnerabilities(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """
        Find potential DOM XSS vulnerabilities.
        
        Returns list of vulnerability dictionaries with:
        - sink_line: Line number of sink
        - sink_content: Content containing sink
        - source_line: Line number of source (if found)
        - source_content: Content containing source
        - has_sanitization: Whether sanitization is present
        - distance: Distance between source and sink
        """
        vulnerabilities = []
        
        # Find all DOM sinks with line numbers
        sinks = []
        for line_num, line in enumerate(lines, 1):
            for sink_pattern in self.compiled_sinks:
                if sink_pattern.search(line):
                    sinks.append({
                        'line': line_num,
                        'content': line,
                        'pattern': sink_pattern.pattern,
                    })
                    break  # Only count once per line
        
        # For each sink, look for nearby user input sources
        for sink in sinks:
            sink_line = sink['line']
            sink_content = sink['content']
            
            # Look for user input sources within N lines before the sink
            search_start = max(0, sink_line - 20)  # Look 20 lines before
            search_end = min(len(lines), sink_line + 5)  # And 5 lines after
            
            nearby_sources = []
            for check_line in range(search_start, search_end):
                line_content = lines[check_line]
                for source_pattern in self.compiled_sources:
                    if source_pattern.search(line_content):
                        nearby_sources.append({
                            'line': check_line + 1,
                            'content': line_content,
                            'pattern': source_pattern.pattern,
                        })
                        break
            
            # Check for sanitization between source and sink
            has_sanitization = False
            if nearby_sources:
                # Check lines between first source and sink
                first_source_line = min(s['line'] for s in nearby_sources)
                check_start = first_source_line
                check_end = sink_line
                
                for check_line in range(check_start, check_end):
                    if check_line <= len(lines):
                        line_content = lines[check_line - 1]
                        for sanitizer_pattern in self.compiled_sanitizers:
                            if sanitizer_pattern.search(line_content):
                                has_sanitization = True
                                break
                    if has_sanitization:
                        break
            
            if nearby_sources:
                vulnerabilities.append({
                    'sink_line': sink_line,
                    'sink_content': sink_content,
                    'sources': nearby_sources,
                    'has_sanitization': has_sanitization,
                    'distance': sink_line - nearby_sources[0]['line'],
                })
        
        return vulnerabilities
    
    def _create_finding_from_vulnerability(self, vuln: Dict[str, Any], file_path: Path) -> Optional[Finding]:
        """Create a finding from a vulnerability dictionary."""
        if vuln['has_sanitization']:
            # Sanitization present, lower severity
            severity = Severity.LOW
            confidence = 0.3
            description = "DOM sink with user input but sanitization may be present."
        else:
            # No sanitization, higher severity
            severity = Severity.HIGH
            confidence = 0.8
            description = "DOM sink with unsanitized user input."
        
        # Create location
        location = Location(
            file_path=str(file_path),
            line_start=vuln['sink_line'],
            code_snippet=vuln['sink_content'].strip()[:200],
        )
        
        # Build description with source info
        source_info = f" near lines: {', '.join(str(s['line']) for s in vuln['sources'])}"
        description += f" User input detected{source_info}."
        
        # Create finding
        finding = Finding(
            title="DOM-based Cross-Site Scripting (XSS)",
            severity=severity,
            category=Category.DOM_XSS,
            location=location,
            description=description,
            recommendation="Sanitize user input before using in DOM sinks. Use textContent instead of innerHTML for text.",
            rule_id="JS-DOM-XSS-FLOW",
            confidence=confidence,
            detector_name="DOMSinkDetector",
            tags=["dom-xss", "data-flow", "javascript"],
        )
        
        return finding
