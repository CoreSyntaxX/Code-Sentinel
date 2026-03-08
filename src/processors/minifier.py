"""
Minified code detector and handler.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple

from models.scan_context import ScanContext
from processors.base_processor import BaseProcessor


logger = logging.getLogger(__name__)


class MinifiedCodeDetector(BaseProcessor):
    """
    Detects minified code and attempts to handle it.
    Can be used to skip analysis or trigger beautification.
    """
    
    def __init__(self):
        super().__init__()
        
        # Minification detection thresholds
        self.config = {
            'max_line_length': 500,  # Characters
            'min_whitespace_ratio': 0.1,  # 10%
            'min_comment_ratio': 0.01,  # 1%
            'avg_line_length_threshold': 200,
        }
        
        # Patterns that indicate minification
        self.minification_patterns = [
            # No spaces between operators
            (r'\w\s*[=+\-*/%&|^<>!]\s*\w', 0.5),
            
            # Multiple statements on one line
            (r'[;{][^;\n{}]*;[^;\n{}]*[;}]\s*', 0.7),
            
            # No spaces after commas in function calls
            (r'\([^)]*,[^ )][^)]*\)', 0.6),
            
            # Very long variable names compressed
            (r'\b[a-z][a-z0-9]{0,2}\b\s*=', 0.4),
        ]
        
        # Known minifier signatures
        self.minifier_signatures = {
            'uglifyjs': r'/\*[^*]*UglifyJS',
            'terser': r'/\*[^*]*Terser',
            'closure': r'/\*[^*]*Closure',
            'webpack': r'/\*[^*]*Webpack',
            'babel': r'/\*[^*]*Babel',
            'rollup': r'/\*[^*]*Rollup',
        }
    
    def get_name(self) -> str:
        return "MinifiedCodeDetector"
    
    def process(self, content: str, context: ScanContext) -> str:
        """
        Detect minified code and add metadata to context.
        
        Args:
            content: Code content to check
            context: Scan context
            
        Returns:
            Original content (this processor doesn't modify content)
        """
        if not self.should_process(content):
            return content
        
        logger.debug(f"Checking for minified code (length: {len(content)})")
        
        # Analyze the code
        analysis = self._analyze_minification(content)
        
        # Store analysis in context
        if 'minified' not in context.stats:
            context.stats['minified'] = {}
        
        file_key = 'current_file'  # Would need actual file path
        context.stats['minified'][file_key] = analysis
        
        # Log findings
        if analysis['is_minified']:
            confidence = analysis['confidence']
            logger.info(f"Detected minified code with {confidence:.0%} confidence")
            
            # Add warning to context if highly confident
            if confidence > 0.8:
                from models.finding import Finding, Severity, Category, Location
                
                finding = Finding(
                    title="Minified Code Detected",
                    severity=Severity.LOW,
                    category=Category.INFORMATION_DISCLOSURE,
                    location=Location(file_path=file_key, line_start=1),
                    description=f"Code appears to be minified (confidence: {confidence:.0%}). Minified code can hide security issues.",
                    recommendation="Consider analyzing the original source code if available.",
                    rule_id="MINIFIED-CODE",
                    confidence=confidence,
                    detector_name=self.name,
                )
                
                # Note: We would need file path to add to context properly
                # context.add_finding(finding)
        
        return content
    
    def _analyze_minification(self, content: str) -> Dict[str, Any]:
        """
        Analyze code to determine if it's minified.
        
        Returns:
            Dictionary with analysis results
        """
        if not content:
            return {'is_minified': False, 'confidence': 0.0}
        
        # Basic metrics
        lines = content.split('\n')
        total_lines = len(lines)
        total_chars = len(content)
        
        if total_lines == 0:
            return {'is_minified': False, 'confidence': 0.0}
        
        # Calculate line length statistics
        line_lengths = [len(line) for line in lines]
        avg_line_length = sum(line_lengths) / total_lines
        max_line_length = max(line_lengths)
        
        # Count whitespace
        whitespace_chars = sum(1 for c in content if c.isspace())
        whitespace_ratio = whitespace_chars / total_chars if total_chars > 0 else 0
        
        # Count comments
        comment_patterns = [
            (r'//.*$', re.MULTILINE),
            (r'#.*$', re.MULTILINE),
            (r'/\*.*?\*/', re.DOTALL),
            (r'<!--.*?-->', re.DOTALL),
        ]
        
        comment_chars = 0
        for pattern, flags in comment_patterns:
            for match in re.finditer(pattern, content, flags=flags):
                comment_chars += len(match.group())
        
        comment_ratio = comment_chars / total_chars if total_chars > 0 else 0
        
        # Check for minifier signatures
        minifier_found = None
        for minifier, pattern in self.minifier_signatures.items():
            if re.search(pattern, content, re.IGNORECASE):
                minifier_found = minifier
                break
        
        # Check minification patterns
        pattern_score = 0.0
        pattern_matches = 0
        
        for pattern, weight in self.minification_patterns:
            matches = re.findall(pattern, content)
            if matches:
                pattern_matches += len(matches)
                pattern_score += weight * len(matches)
        
        # Normalize pattern score
        if pattern_matches > 0:
            pattern_score = min(1.0, pattern_score / 10)
        
        # Calculate confidence score
        confidence = 0.0
        
        # Line length factor
        if max_line_length > self.config['max_line_length']:
            line_factor = 0.3
        elif avg_line_length > self.config['avg_line_length_threshold']:
            line_factor = 0.2
        else:
            line_factor = 0.0
        
        # Whitespace factor
        if whitespace_ratio < self.config['min_whitespace_ratio']:
            whitespace_factor = 0.3
        else:
            whitespace_factor = 0.0
        
        # Comment factor
        if comment_ratio < self.config['min_comment_ratio']:
            comment_factor = 0.2
        else:
            comment_factor = 0.0
        
        # Minifier signature factor
        if minifier_found:
            signature_factor = 0.3
        else:
            signature_factor = 0.0
        
        # Total confidence
        confidence = line_factor + whitespace_factor + comment_factor + signature_factor + pattern_score
        confidence = min(1.0, confidence)
        
        # Determine if minified
        is_minified = confidence > 0.5
        
        return {
            'is_minified': is_minified,
            'confidence': confidence,
            'metrics': {
                'total_lines': total_lines,
                'total_chars': total_chars,
                'avg_line_length': avg_line_length,
                'max_line_length': max_line_length,
                'whitespace_ratio': whitespace_ratio,
                'comment_ratio': comment_ratio,
                'pattern_matches': pattern_matches,
            },
            'minifier': minifier_found,
            'factors': {
                'line_factor': line_factor,
                'whitespace_factor': whitespace_factor,
                'comment_factor': comment_factor,
                'signature_factor': signature_factor,
                'pattern_score': pattern_score,
            }
        }
    
    def should_process(self, content: str, file_path: Optional[str] = None) -> bool:
        """Process all non-empty content."""
        return self.enabled and bool(content.strip())
