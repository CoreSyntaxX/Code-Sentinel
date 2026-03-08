"""
Basic code deobfuscator for simple obfuscation techniques.
"""

import re
import logging
import base64
from typing import Optional, Dict, Any, List, Tuple

from models.scan_context import ScanContext
from processors.base_processor import BaseProcessor


logger = logging.getLogger(__name__)


class CodeDeobfuscator(BaseProcessor):
    """
    Basic deobfuscator for common obfuscation techniques.
    Handles simple encoding like base64, hex, char codes, etc.
    """
    
    def __init__(self):
        super().__init__()
        
        # Obfuscation patterns to detect
        self.obfuscation_patterns = [
            # Base64 encoded strings
            (r'atob\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)', self._decode_base64),
            (r'base64_decode\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)', self._decode_base64),
            
            # Hex encoded strings
            (r'["\']([0-9a-fA-F]{2,})["\']\.replace\s*\(/\.\./g', self._decode_hex),
            (r'\\x[0-9a-fA-F]{2}', self._decode_hex_escape),
            
            # Char code arrays
            (r'String\.fromCharCode\s*\((?:0x)?[0-9a-fA-F]+(?:\s*,\s*(?:0x)?[0-9a-fA-F]+)*\)', 
             self._decode_char_codes),
            
            # Eval with encoded strings
            (r'eval\s*\(\s*(?:atob|unescape|decodeURIComponent?)\s*\([^)]+\)\s*\)',
             self._decode_eval_wrapper),
            
            # Obfuscated variable names
            (r'\b_0x[0-9a-fA-F]{4,6}\b', self._flag_obfuscated_var),
            
            # Packer/JSFuck style
            (r'\[\[\].+\]', self._flag_packed_code),
        ]
        
        # Simple string manipulation patterns
        self.string_manipulation_patterns = [
            (r'["\'][^"\']+["\']\s*\.\s*(split|reverse|join|replace|slice|substr|substring)\s*\([^)]*\)',
             self._simplify_string_ops),
            (r'unescape\s*\(\s*["\'][^"\']+["\']\s*\)', self._decode_unescape),
            (r'decodeURIComponent\s*\(\s*["\'][^"\']+["\']\s*\)', self._decode_uri),
        ]
    
    def get_name(self) -> str:
        return "CodeDeobfuscator"
    
    def process(self, content: str, context: ScanContext) -> str:
        """
        Attempt to deobfuscate code.
        
        Args:
            content: Code content to deobfuscate
            context: Scan context
            
        Returns:
            Partially deobfuscated code
        """
        if not self.should_process(content):
            return content
        
        logger.debug(f"Attempting deobfuscation (length: {len(content)})")
        
        # Check if code appears obfuscated
        if not self._is_obfuscated(content):
            logger.debug("Code doesn't appear obfuscated, skipping")
            return content
        
        # Apply deobfuscation passes
        deobfuscated = content
        
        # Pass 1: Simple string decoding
        deobfuscated = self._apply_patterns(deobfuscated, self.string_manipulation_patterns)
        
        # Pass 2: Common obfuscation techniques
        deobfuscated = self._apply_patterns(deobfuscated, self.obfuscation_patterns)
        
        # Pass 3: Clean up
        deobfuscated = self._cleanup_deobfuscated(deobfuscated)
        
        # Check if we made any changes
        if deobfuscated != content:
            logger.info(f"Deobfuscated code (reduced by {len(content) - len(deobfuscated)} chars)")
            
            # Store original in context for reference
            if 'deobfuscation' not in context.stats:
                context.stats['deobfuscation'] = {}
            
            context.stats['deobfuscation']['original_length'] = len(content)
            context.stats['deobfuscation']['deobfuscated_length'] = len(deobfuscated)
            context.stats['deobfuscation']['reduction'] = len(content) - len(deobfuscated)
        
        return deobfuscated
    
    def _is_obfuscated(self, content: str) -> bool:
        """Check if code appears to be obfuscated."""
        if len(content) < 100:
            return False
        
        # Check for common obfuscation indicators
        indicators = [
            # High frequency of certain patterns
            (r'eval\s*\(', 3),  # Multiple eval calls
            (r'atob\s*\(', 2),  # Multiple base64 decodes
            (r'unescape\s*\(', 2),  # Multiple unescape calls
            (r'String\.fromCharCode', 3),  # Multiple char code arrays
            (r'_0x[0-9a-fA-F]{4}', 5),  # Many obfuscated variable names
            (r'\\x[0-9a-fA-F]{2}', 10),  # Many hex escapes
        ]
        
        indicator_count = 0
        for pattern, threshold in indicators:
            matches = re.findall(pattern, content)
            if len(matches) >= threshold:
                indicator_count += 1
        
        # Also check entropy (obfuscated code often has high entropy)
        entropy = self._calculate_entropy(content[:1000])
        if entropy > 4.5:  # Very high entropy
            indicator_count += 1
        
        return indicator_count >= 2
    
    def _calculate_entropy(self, string: str) -> float:
        """Calculate Shannon entropy."""
        import math
        if not string:
            return 0
        
        freq = {}
        for char in string:
            freq[char] = freq.get(char, 0) + 1
        
        entropy = 0
        length = len(string)
        for count in freq.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _apply_patterns(self, content: str, patterns: List[Tuple[str, callable]]) -> str:
        """Apply deobfuscation patterns to content."""
        result = content
        
        for pattern, handler in patterns:
            # Find all matches
            matches = list(re.finditer(pattern, result, re.DOTALL | re.IGNORECASE))
            
            # Process matches from end to beginning
            for match in reversed(matches):
                original = match.group()
                try:
                    decoded = handler(original)
                    if decoded != original:
                        # Replace in result
                        start, end = match.span()
                        result = result[:start] + decoded + result[end:]
                except Exception as e:
                    logger.debug(f"Failed to decode pattern: {e}")
                    continue
        
        return result
    
    def _decode_base64(self, match: str) -> str:
        """Decode base64 encoded string."""
        # Extract the base64 string
        b64_match = re.search(r'["\']([A-Za-z0-9+/=]+)["\']', match)
        if not b64_match:
            return match
        
        b64_string = b64_match.group(1)
        try:
            decoded = base64.b64decode(b64_string).decode('utf-8', errors='ignore')
            return f'"{decoded}"'  # Return as string literal
        except Exception:
            return match
    
    def _decode_hex(self, match: str) -> str:
        """Decode hex encoded string."""
        hex_match = re.search(r'["\']([0-9a-fA-F]+)["\']', match)
        if not hex_match:
            return match
        
        hex_string = hex_match.group(1)
        try:
            # Convert hex pairs to characters
            decoded = bytes.fromhex(hex_string).decode('utf-8', errors='ignore')
            return f'"{decoded}"'
        except Exception:
            return match
    
    def _decode_hex_escape(self, match: str) -> str:
        """Decode hex escape sequences like \x41."""
        # This is already decoded by Python, but we can flag it
        return match  # Just return as-is for now
    
    def _decode_char_codes(self, match: str) -> str:
        """Decode String.fromCharCode calls."""
        # Extract numbers
        numbers = re.findall(r'(?:0x)?([0-9a-fA-F]+)', match)
        if not numbers:
            return match
        
        try:
            chars = []
            for num in numbers:
                if num.startswith('0x'):
                    # Hex number
                    char_code = int(num, 16)
                else:
                    # Decimal number
                    char_code = int(num)
                
                if 0 <= char_code <= 0x10FFFF:
                    chars.append(chr(char_code))
            
            decoded = ''.join(chars)
            return f'"{decoded}"'
        except Exception:
            return match
    
    def _decode_eval_wrapper(self, match: str) -> str:
        """Flag eval wrappers."""
        return f"/* EVAL_WRAPPER: {match} */"
    
    def _flag_obfuscated_var(self, match: str) -> str:
        """Flag obfuscated variable names."""
        return f"/* OBFUSCATED_VAR: {match} */"
    
    def _flag_packed_code(self, match: str) -> str:
        """Flag packed/JSFuck style code."""
        return f"/* PACKED_CODE: {match[:50]}... */"
    
    def _simplify_string_ops(self, match: str) -> str:
        """Attempt to simplify string operations."""
        # For now, just flag them
        return f"/* STRING_OP: {match} */"
    
    def _decode_unescape(self, match: str) -> str:
        """Decode unescape calls."""
        import urllib.parse
        
        str_match = re.search(r'["\']([^"\']+)["\']', match)
        if not str_match:
            return match
        
        encoded = str_match.group(1)
        try:
            decoded = urllib.parse.unquote(encoded)
            return f'"{decoded}"'
        except Exception:
            return match
    
    def _decode_uri(self, match: str) -> str:
        """Decode decodeURIComponent calls."""
        import urllib.parse
        
        str_match = re.search(r'["\']([^"\']+)["\']', match)
        if not str_match:
            return match
        
        encoded = str_match.group(1)
        try:
            decoded = urllib.parse.unquote(encoded)
            return f'"{decoded}"'
        except Exception:
            return match
    
    def _cleanup_deobfuscated(self, content: str) -> str:
        """Clean up deobfuscated code."""
        # Remove multiple comments in a row
        content = re.sub(r'/\*.*?\*/\s*/\*.*?\*/', '/* ... */', content, flags=re.DOTALL)
        
        # Remove excessive whitespace
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def should_process(self, content: str, file_path: Optional[str] = None) -> bool:
        """Only process in deep mode and if content appears obfuscated."""
        if not self.enabled or not content.strip():
            return False
        
        # Only run in deep mode (deobfuscation can be slow)
        # We would need access to context.settings.mode
        # For now, always check but skip quickly if not obfuscated
        return True
