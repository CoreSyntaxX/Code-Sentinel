"""
Detector specifically for JWT (JSON Web Tokens) and related issues.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
import logging
import base64
import json

from models.finding import Finding, Severity, Category
from models.scan_context import ScanContext
from detectors.base_detector import BaseDetector


logger = logging.getLogger(__name__)


class JWTDetector(BaseDetector):
    """
    Detector for JWT tokens and related security issues.
    """
    
    def __init__(self):
        super().__init__()
        self.confidence = 0.9
        
        # JWT patterns (RFC 7519)
        self.jwt_patterns = [
            # Standard JWT format: header.payload.signature
            (r'eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
             "JWT Token", Severity.HIGH, Category.JWT_EXPOSURE),
            
            # JWT in authorization headers
            (r'Authorization:\s*(?:Bearer|JWT)\s+eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
             "JWT in Authorization Header", Severity.HIGH, Category.JWT_EXPOSURE),
            
            # JWT in cookies
            (r'Set-Cookie:.*eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
             "JWT in Cookie", Severity.HIGH, Category.JWT_EXPOSURE),
            
            # JWT variable assignments
            (r'(?:var|let|const|\.)\s*\w*[Tt]oken\s*=\s*["\']eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*["\']',
             "JWT Token Assignment", Severity.HIGH, Category.JWT_EXPOSURE),
        ]
        
        # JWT secret/configuration patterns
        self.jwt_config_patterns = [
            # JWT secret keys
            (r'(?i)jwt[_-]?(secret|key)\s*[:=]\s*["\'][^\'"]{10,}["\']',
             "JWT Secret Key", Severity.CRITICAL, Category.JWT_EXPOSURE),
            
            # Weak JWT algorithms
            (r'(?i)(algorithm|alg)\s*[:=]\s*["\']?(none)["\']?',
             "Weak JWT Algorithm", Severity.HIGH, Category.WEAK_CRYPTO),
            
            # No signature verification
            (r'(?i)verify\s*[:=]\s*["\']?false["\']?',
             "JWT Verification Disabled", Severity.CRITICAL, Category.INSECURE_CONFIG),
        ]
    
    def get_name(self) -> str:
        return "JWTDetector"
    
    def detect(self, content: str, file_path: Path, context: ScanContext) -> List[Finding]:
        """
        Detect JWT tokens and related security issues.
        """
        findings = []
        
        logger.debug(f"JWT detector analyzing {file_path}")
        
        # Pre-process content
        processed_content = self.pre_process_content(content)
        
        # 1. Find JWT tokens
        jwt_findings = self._find_pattern_matches(
            processed_content,
            self.jwt_patterns,
            file_path,
        )
        
        # Analyze found JWTs
        for finding in jwt_findings:
            # Extract and analyze the JWT
            jwt_analysis = self._analyze_jwt(finding)
            if jwt_analysis:
                findings.extend(jwt_analysis)
            else:
                findings.append(finding)
        
        # 2. Check for JWT configuration issues
        config_findings = self._find_pattern_matches(
            processed_content,
            self.jwt_config_patterns,
            file_path,
        )
        findings.extend(config_findings)
        
        # 3. Check for JWT in environment/config files
        env_findings = self._check_jwt_in_configs(processed_content, file_path)
        findings.extend(env_findings)
        
        # Post-process findings
        findings = self.post_process_findings(findings, context)
        
        logger.debug(f"JWT detector found {len(findings)} issues in {file_path}")
        return findings
    
    def _analyze_jwt(self, finding: Finding) -> Optional[List[Finding]]:
        """
        Analyze a JWT token found in a finding.
        Returns enhanced findings with JWT analysis.
        """
        code_snippet = finding.location.code_snippet or ""
        
        # Extract JWT from code snippet
        jwt_match = re.search(r'eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', code_snippet)
        if not jwt_match:
            return [finding]
        
        jwt_token = jwt_match.group()
        
        try:
            # Decode JWT parts
            parts = jwt_token.split('.')
            if len(parts) != 3:
                return [finding]
            
            # Decode header
            header_json = self._decode_jwt_part(parts[0])
            if header_json:
                header = json.loads(header_json)
            else:
                return [finding]
            
            # Decode payload
            payload_json = self._decode_jwt_part(parts[1])
            if payload_json:
                payload = json.loads(payload_json)
            else:
                return [finding]
            
            # Create enhanced findings based on JWT analysis
            enhanced_findings = []
            
            # Base finding with JWT info
            enhanced_finding = finding
            enhanced_finding.description += f"\n\nJWT Analysis:\n"
            enhanced_finding.description += f"- Algorithm: {header.get('alg', 'unknown')}\n"
            enhanced_finding.description += f"- Type: {header.get('typ', 'JWT')}\n"
            
            if 'exp' in payload:
                enhanced_finding.description += f"- Expires: {payload['exp']}\n"
            if 'sub' in payload:
                enhanced_finding.description += f"- Subject: {payload['sub']}\n"
            
            enhanced_findings.append(enhanced_finding)
            
            # Check for specific JWT issues
            if header.get('alg', '').upper() == 'NONE':
                none_finding = self._create_finding(
                    title="JWT with 'none' Algorithm",
                    severity=Severity.CRITICAL,
                    category=Category.WEAK_CRYPTO,
                    file_path=Path(finding.location.file_path),
                    line_start=finding.location.line_start,
                    code_snippet=code_snippet,
                    description="JWT uses 'none' algorithm which provides no signature verification.",
                    recommendation="Use a strong algorithm like RS256 and properly verify signatures.",
                    rule_id="JWT-NONE-ALGORITHM",
                    confidence=1.0,
                )
                enhanced_findings.append(none_finding)
            
            if payload.get('exp', 0) == 0:
                no_expiry_finding = self._create_finding(
                    title="JWT Without Expiration",
                    severity=Severity.MEDIUM,
                    category=Category.INSECURE_CONFIG,
                    file_path=Path(finding.location.file_path),
                    line_start=finding.location.line_start,
                    code_snippet=code_snippet,
                    description="JWT has no expiration (exp claim is 0 or missing).",
                    recommendation="Always set reasonable expiration times for JWTs.",
                    rule_id="JWT-NO-EXPIRATION",
                    confidence=0.8,
                )
                enhanced_findings.append(no_expiry_finding)
            
            return enhanced_findings
            
        except Exception as e:
            logger.debug(f"Failed to analyze JWT: {e}")
            return [finding]
    
    def _decode_jwt_part(self, part: str) -> Optional[str]:
        """Decode a JWT part (base64url)."""
        try:
            # Add padding if needed
            padding = 4 - len(part) % 4
            if padding != 4:
                part += '=' * padding
            
            # Decode
            decoded = base64.urlsafe_b64decode(part)
            return decoded.decode('utf-8')
        except Exception:
            return None
    
    def _check_jwt_in_configs(self, content: str, file_path: Path) -> List[Finding]:
        """Check for JWT-related configurations."""
        findings = []
        
        # Environment files
        if file_path.name.lower() in ['.env', '.env.example', '.env.local']:
            env_patterns = [
                (r'JWT_SECRET=.*', "JWT Secret in Environment", Severity.CRITICAL),
                (r'JWT_KEY=.*', "JWT Key in Environment", Severity.CRITICAL),
                (r'JWT_ALGORITHM=.*', "JWT Algorithm in Environment", Severity.LOW),
            ]
            
            for pattern, title, severity in env_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_start = content[:match.start()].count('\n') + 1
                    
                    finding = self._create_finding(
                        title=title,
                        severity=severity,
                        category=Category.JWT_EXPOSURE,
                        file_path=file_path,
                        line_start=line_start,
                        code_snippet=match.group(),
                        description=f"{title} found in environment file.",
                        recommendation="Store JWT secrets in secure secret management systems.",
                        rule_id="JWT-ENV-CONFIG",
                    )
                    findings.append(finding)
        
        # Configuration files
        if file_path.suffix.lower() in ['.json', '.yaml', '.yml', '.config', '.conf']:
            config_patterns = [
                (r'(?i)"jwt_secret"\s*:\s*"[^"]+"', "JWT Secret in Config", Severity.CRITICAL),
                (r'(?i)jwt:\s*[^:]*secret:\s*[^\n]+', "JWT Secret in YAML", Severity.CRITICAL),
            ]
            
            for pattern, title, severity in config_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_start = content[:match.start()].count('\n') + 1
                    
                    finding = self._create_finding(
                        title=title,
                        severity=severity,
                        category=Category.JWT_EXPOSURE,
                        file_path=file_path,
                        line_start=line_start,
                        code_snippet=match.group(),
                        description=f"{title} found in configuration file.",
                        recommendation="Move JWT secrets to environment variables or secure storage.",
                        rule_id="JWT-CONFIG-FILE",
                    )
                    findings.append(finding)
        
        return findings
    
    def pre_process_content(self, content: str) -> str:
        """Pre-process content for JWT detection."""
        # Keep content as-is for JWT detection
        return content
    
    def post_process_findings(self, findings: List[Finding], context: ScanContext) -> List[Finding]:
        """Filter false positives and adjust findings."""
        filtered_findings = []
        
        for finding in findings:
            # Skip test JWTs
            if self._is_test_jwt(finding):
                logger.debug(f"Filtered test JWT: {finding.title}")
                continue
            
            filtered_findings.append(finding)
        
        return filtered_findings
    
    def _is_test_jwt(self, finding: Finding) -> bool:
        """Check if JWT is a test/example token."""
        code_snippet = finding.location.code_snippet or ""
        
        test_indicators = [
            r'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9\..*',  # Common test header
            r'example',
            r'test',
            r'dummy',
            r'mock',
            r'changeme',
            r'your-jwt-token',
            r'YOUR_TOKEN_HERE',
        ]
        
        for indicator in test_indicators:
            if re.search(indicator, code_snippet, re.IGNORECASE):
                return True
        
        return False
