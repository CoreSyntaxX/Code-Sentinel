"""
Detector that finds high-entropy strings which might be secrets.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
import logging
import math

from models.finding import Finding, Severity, Category
from models.scan_context import ScanContext
from detectors.base_detector import BaseDetector


logger = logging.getLogger(__name__)


class EntropyDetector(BaseDetector):
    """
    Detector that finds high-entropy strings which might be secrets.
    Uses Shannon entropy to identify random-looking strings.
    """
    
    def __init__(self):
        super().__init__()
        self.confidence = 0.6  # Lower confidence for entropy-based detection
        
        # Minimum entropy threshold (bits per character)
        self.min_entropy = 3.5
        
        # Minimum string length to check
        self.min_length = 10
        
        # Maximum string length to check (to avoid performance issues)
        self.max_length = 100
        
        # Patterns to skip (common high-entropy but non-secret strings)
        self.skip_patterns = [
            r'^[0-9]+$',  # All numbers
            r'^[a-f0-9]{32}$',  # MD5
            r'^[a-f0-9]{40}$',  # SHA-1
            r'^[a-f0-9]{64}$',  # SHA-256
            r'^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$',  # UUID
            r'^[a-zA-Z0-9+/]+={0,2}$',  # Base64 (but not too long)
        ]
        
        # Context keywords that indicate a secret
        self.secret_context_keywords = {
            'key', 'secret', 'token', 'password', 'passwd', 'pwd',
            'credential', 'auth', 'authentication', 'private',
            'client_secret', 'api_key', 'access_key', 'secret_key',
            'jwt', 'bearer', 'oauth', 'encryption', 'crypt',
            'salt', 'iv', 'nonce', 'signature'
        }
        
        # Assignment patterns that indicate a secret
        self.secret_assignment_patterns = [
            r'(?i)(key|secret|token|password)\s*[:=]',
            r'(?i)set\s+(key|secret|token|password)',
            r'(?i)assign\s+(key|secret|token|password)',
            r'(?i)store\s+(key|secret|token|password)',
        ]
    
    def get_name(self) -> str:
        return "EntropyDetector"
    
    def detect(self, content: str, file_path: Path, context: ScanContext) -> List[Finding]:
        """
        Detect high-entropy strings that might be secrets.
        """
        findings = []
        
        # Skip in fast mode (entropy detection can be slow)
        if context.settings.mode.value == "fast":
            return findings
        
        logger.debug(f"Entropy detector analyzing {file_path}")
        
        # Pre-process content
        processed_content = self.pre_process_content(content)
        
        # Find all potential strings in the content
        potential_strings = self._extract_potential_strings(processed_content)
        
        for string_value, start_pos, context_str in potential_strings:
            # Skip if string doesn't meet basic criteria
            if not self._should_check_string(string_value):
                continue
            
            # Calculate entropy
            entropy = self._calculate_entropy(string_value)
            
            # Skip if entropy is too low
            if entropy < self.min_entropy:
                continue
            
            # Check if string appears to be a secret based on context
            if self._has_secret_context(context_str, string_value):
                line_start = processed_content[:start_pos].count('\n') + 1
                
                # Get the line
                lines = processed_content.split('\n')
                if line_start <= len(lines):
                    line_content = lines[line_start - 1]
                else:
                    line_content = ""
                
                # Get more context
                context_start = max(0, line_start - 3)
                context_end = min(len(lines), line_start + 2)
                context_before = '\n'.join(lines[context_start:line_start - 1])
                context_after = '\n'.join(lines[line_start:context_end])
                
                finding = self._create_finding(
                    title=f"High-Entropy String (Possible Secret)",
                    severity=Severity.MEDIUM,
                    category=Category.SECRET_LEAK,
                    file_path=file_path,
                    line_start=line_start,
                    code_snippet=line_content[:200],
                    description=f"High-entropy string found (entropy: {entropy:.2f}, length: {len(string_value)}). "
                               f"This may be a secret key or token.",
                    recommendation="Review if this string contains sensitive information. "
                                 "If it's a secret, store it in a secure location like environment variables.",
                    rule_id="ENTROPY-HIGH-STRING",
                    confidence=self._calculate_confidence(entropy, context_str),
                    context_before=context_before,
                    context_after=context_after,
                )
                
                findings.append(finding)
        
        # Post-process findings
        findings = self.post_process_findings(findings, context)
        
        logger.debug(f"Entropy detector found {len(findings)} issues in {file_path}")
        return findings
    
    def _extract_potential_strings(self, content: str) -> List[Tuple[str, int, str]]:
        """
        Extract potential strings from content along with their positions and context.
        """
        strings = []
        
        # Regex patterns to find strings (including various quote types)
        string_patterns = [
            (r'["\']([^"\'\`\\]*(?:\\.[^"\'\`\\]*)*)["\']', 1),  # Single/double quotes
            (r'`([^`\\]*(?:\\.[^`\\]*)*)`', 1),  # Backticks
            (r'/([^/\\]*(?:\\.[^/\\]*)*)/', 1),  # Regex literals (JavaScript)
        ]
        
        for pattern, group_idx in string_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                string_value = match.group(group_idx)
                start_pos = match.start()
                
                # Get context (50 chars before and after)
                context_start = max(0, start_pos - 50)
                context_end = min(len(content), start_pos + 50)
                context_str = content[context_start:context_end]
                
                strings.append((string_value, start_pos, context_str))
        
        return strings
    
    def _should_check_string(self, string: str) -> bool:
        """Check if a string should be analyzed for entropy."""
        # Check length
        if len(string) < self.min_length or len(string) > self.max_length:
            return False
        
        # Check against skip patterns
        for pattern in self.skip_patterns:
            if re.match(pattern, string, re.IGNORECASE):
                return False
        
        # Check if string contains mostly alphanumeric characters
        # (secrets are usually alphanumeric with symbols)
        alnum_ratio = sum(1 for c in string if c.isalnum()) / len(string)
        if alnum_ratio > 0.95:  # Almost all alphanumeric
            return False
        
        return True
    
    def _has_secret_context(self, context: str, string_value: str) -> bool:
        """Check if context indicates the string might be a secret."""
        context_lower = context.lower()
        
        # Check for secret-related keywords in context
        for keyword in self.secret_context_keywords:
            if keyword in context_lower:
                return True
        
        # Check for assignment patterns
        for pattern in self.secret_assignment_patterns:
            if re.search(pattern, context_lower):
                return True
        
        # Check if string looks like common secret patterns
        if self._looks_like_secret_pattern(string_value):
            return True
        
        return False
    
    def _looks_like_secret_pattern(self, string: str) -> bool:
        """Check if string matches common secret patterns."""
        # Has both uppercase and lowercase letters
        has_upper = any(c.isupper() for c in string)
        has_lower = any(c.islower() for c in string)
        
        # Has numbers
        has_digit = any(c.isdigit() for c in string)
        
        # Has special characters
        has_special = any(not c.isalnum() for c in string)
        
        # Common secret patterns:
        # 1. Mixed case with numbers and/or symbols
        # 2. Base64-like (alphanumeric with + / =)
        # 3. Hex-like but longer than typical hashes
        
        # Pattern 1: Mixed case with other characters
        if has_upper and has_lower and (has_digit or has_special):
            return True
        
        # Pattern 2: Base64-like (ends with = or ==)
        if string.endswith('=') or string.endswith('=='):
            if all(c.isalnum() or c in '+/=' for c in string):
                return True
        
        # Pattern 3: Long hex string (but not standard hash length)
        if re.match(r'^[a-f0-9]+$', string, re.IGNORECASE):
            if 40 < len(string) < 100:  # Not standard hash length
                return True
        
        return False
    
    def _calculate_confidence(self, entropy: float, context: str) -> float:
        """Calculate confidence based on entropy and context."""
        confidence = 0.5  # Base confidence
        
        # Adjust based on entropy
        if entropy > 4.0:
            confidence += 0.2
        if entropy > 4.5:
            confidence += 0.2
        
        # Adjust based on context
        context_lower = context.lower()
        context_indicators = 0
        
        for keyword in self.secret_context_keywords:
            if keyword in context_lower:
                context_indicators += 1
        
        confidence += min(context_indicators * 0.1, 0.3)
        
        return min(confidence, 1.0)
    
    def pre_process_content(self, content: str) -> str:
        """Pre-process content for entropy detection."""
        # Remove comments (but keep string content)
        # We'll remove comments but carefully to not break strings
        
        # Remove single-line comments
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Find string quotes in the line
            in_string = False
            string_char = None
            cleaned_line = []
            
            i = 0
            while i < len(line):
                char = line[i]
                
                if char in ['"', "'", '`'] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif string_char == char:
                        in_string = False
                        string_char = None
                    cleaned_line.append(char)
                
                elif not in_string and char == '/' and i + 1 < len(line) and line[i+1] == '/':
                    # Start of single-line comment
                    break
                else:
                    cleaned_line.append(char)
                
                i += 1
            
            cleaned_lines.append(''.join(cleaned_line))
        
        return '\n'.join(cleaned_lines)
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """Filter false positives and adjust findings."""
        filtered_findings = []
        
        for finding in findings:
            # Check if it's likely a false positive
            if self._is_false_positive(finding):
                logger.debug(f"Filtered entropy false positive: {finding.title}")
                continue
            
            filtered_findings.append(finding)
        
        return filtered_findings
    
    def _is_false_positive(self, finding: Finding) -> bool:
        """Check if entropy finding is a false positive."""
        code_snippet = finding.location.code_snippet or ""
        
        # Common false positives
        false_positives = [
            # URLs
            r'https?://[^\s]+',
            
            # Email addresses
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',
            
            # File paths
            r'/[^\s]+',
            r'[A-Za-z]:\\[^\s]+',
            
            # Version strings
            r'v?\d+\.\d+(\.\d+)?',
            
            # Test/mock data
            r'test[^\s]*',
            r'mock[^\s]*',
            r'example[^\s]*',
            r'dummy[^\s]*',
            r'fake[^\s]*',
            
            # Common variable names
            r'[A-Za-z_][A-Za-z0-9_]*',  # Simple variable names
        ]
        
        for pattern in false_positives:
            if re.search(pattern, code_snippet, re.IGNORECASE):
                return True
        
        return False
