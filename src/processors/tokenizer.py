"""
Tokenizer for code analysis.
Breaks code into tokens for structural analysis.
"""

import re
import logging
from typing import List, Tuple, Dict, Any, Optional

from models.scan_context import ScanContext
from processors.base_processor import BaseProcessor


logger = logging.getLogger(__name__)


class CodeTokenizer(BaseProcessor):
    """
    Tokenizes code for structural analysis.
    Useful for building AST-like representations without full parsing.
    """
    
    def __init__(self):
        super().__init__()
        
        # Token patterns (regex, token_type)
        self.token_patterns = [
            # Whitespace (we'll skip but track)
            (r'\s+', 'WHITESPACE'),
            
            # Comments
            (r'//.*', 'COMMENT'),
            (r'#.*', 'COMMENT'),
            (r'/\*.*?\*/', 'COMMENT'),
            (r'<!--.*?-->', 'COMMENT'),
            
            # Strings
            (r'"(?:[^"\\]|\\.)*"', 'STRING'),
            (r"'(?:[^'\\]|\\.)*'", 'STRING'),
            (r'`(?:[^`\\]|\\.)*`', 'TEMPLATE_STRING'),
            
            # Numbers
            (r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b', 'NUMBER'),
            (r'\b0x[0-9a-fA-F]+\b', 'HEX_NUMBER'),
            (r'\b0[0-7]+\b', 'OCTAL_NUMBER'),
            
            # Keywords (JavaScript/PHP/Python common)
            (r'\b(function|class|interface|enum|namespace|import|export|require|module)\b', 'KEYWORD_DECL'),
            (r'\b(var|let|const|public|private|protected|static|final|abstract)\b', 'KEYWORD_MOD'),
            (r'\b(if|else|for|while|do|switch|case|default|break|continue|return|throw|try|catch|finally)\b', 'KEYWORD_CTRL'),
            (r'\b(new|delete|typeof|instanceof|in|of|void|yield|await|async)\b', 'KEYWORD_OP'),
            (r'\b(true|false|null|undefined|NaN|Infinity)\b', 'LITERAL'),
            
            # PHP-specific
            (r'\b(echo|print|die|exit|isset|empty|unset|include|include_once|require|require_once)\b', 'PHP_KEYWORD'),
            
            # HTML tags
            (r'</?[a-zA-Z][^>]*>', 'HTML_TAG'),
            
            # Identifiers
            (r'\b[a-zA-Z_$][a-zA-Z0-9_$]*\b', 'IDENTIFIER'),
            
            # Operators
            (r'[=!<>]=?=?', 'OPERATOR_COMP'),
            (r'[+\-*/%&|^]=?', 'OPERATOR_MATH'),
            (r'&&|\|\||!', 'OPERATOR_LOGICAL'),
            (r'\+\+|--', 'OPERATOR_INC'),
            (r'\.\.\.', 'OPERATOR_SPREAD'),
            (r'\.', 'OPERATOR_DOT'),
            (r'\?\.', 'OPERATOR_OPTIONAL'),
            
            # Punctuation
            (r'[;,.:]', 'PUNCTUATION'),
            
            # Brackets
            (r'[()\[\]{}]', 'BRACKET'),
            
            # Everything else
            (r'.', 'UNKNOWN'),
        ]
        
        # Compiled patterns
        self.compiled_patterns = [(re.compile(pattern), token_type) 
                                  for pattern, token_type in self.token_patterns]
    
    def get_name(self) -> str:
        return "CodeTokenizer"
    
    def process(self, content: str, context: ScanContext) -> str:
        """
        Tokenize code and store tokens in context.
        
        Args:
            content: Code content to tokenize
            context: Scan context
            
        Returns:
            Original content (tokens stored in context cache)
        """
        if not self.should_process(content):
            return content
        
        logger.debug(f"Tokenizing code (length: {len(content)})")
        
        # Tokenize the content
        tokens = self._tokenize(content)
        
        # Store tokens in context cache for other analyzers
        # Use a hash of content as cache key
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        if 'tokens' not in context.ast_cache:
            context.ast_cache['tokens'] = {}
        
        context.ast_cache['tokens'][content_hash] = tokens
        
        # Also store token statistics
        token_stats = self._analyze_tokens(tokens)
        context.stats['token_stats'] = token_stats
        
        logger.debug(f"Generated {len(tokens)} tokens")
        return content
    
    def _tokenize(self, content: str) -> List[Tuple[str, str, Tuple[int, int]]]:
        """
        Tokenize content into (token_type, token_value, position) tuples.
        
        Returns:
            List of tokens with positions
        """
        tokens = []
        position = 0
        length = len(content)
        
        while position < length:
            # Try each pattern
            matched = False
            for pattern, token_type in self.compiled_patterns:
                match = pattern.match(content, position)
                if match:
                    value = match.group()
                    start = position
                    end = position + len(value)
                    
                    # Skip whitespace tokens
                    if token_type != 'WHITESPACE':
                        tokens.append((token_type, value, (start, end)))
                    
                    position = end
                    matched = True
                    break
            
            if not matched:
                # Should not happen since last pattern matches any character
                position += 1
        
        return tokens
    
    def _analyze_tokens(self, tokens: List[Tuple[str, str, Tuple[int, int]]]) -> Dict[str, Any]:
        """Analyze tokens for statistics."""
        if not tokens:
            return {}
        
        # Count tokens by type
        type_counts = {}
        for token_type, _, _ in tokens:
            type_counts[token_type] = type_counts.get(token_type, 0) + 1
        
        # Find common identifiers
        identifiers = [value for token_type, value, _ in tokens 
                      if token_type == 'IDENTIFIER']
        
        # Count identifier frequency
        identifier_counts = {}
        for ident in identifiers:
            identifier_counts[ident] = identifier_counts.get(ident, 0) + 1
        
        # Get top identifiers
        top_identifiers = sorted(identifier_counts.items(), 
                                key=lambda x: x[1], reverse=True)[:10]
        
        # Find potential sensitive patterns
        sensitive_patterns = []
        for i in range(len(tokens) - 2):
            token_type1, value1, _ = tokens[i]
            token_type2, value2, _ = tokens[i + 1]
            token_type3, value3, _ = tokens[i + 2]
            
            # Check for password assignments
            if (token_type1 == 'IDENTIFIER' and 'password' in value1.lower() and
                token_type2 == 'OPERATOR_COMP' and value2 == '=' and
                token_type3 == 'STRING'):
                sensitive_patterns.append({
                    'type': 'password_assignment',
                    'position': tokens[i][2][0],
                    'context': f"{value1} = {value3}"
                })
        
        return {
            'total_tokens': len(tokens),
            'type_counts': type_counts,
            'top_identifiers': top_identifiers,
            'sensitive_patterns': sensitive_patterns,
        }
    
    def get_tokens_for_content(self, context: ScanContext, content: str) -> Optional[List[Tuple[str, str, Tuple[int, int]]]]:
        """
        Get tokens for content from cache.
        
        Args:
            context: Scan context with cache
            content: Content to look up
            
        Returns:
            Cached tokens or None
        """
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        if ('tokens' in context.ast_cache and 
            content_hash in context.ast_cache['tokens']):
            return context.ast_cache['tokens'][content_hash]
        
        return None
    
    def should_process(self, content: str, file_path: Optional[str] = None) -> bool:
        """Process non-empty content in normal/deep mode."""
        if not self.enabled or not content.strip():
            return False
        
        # Skip very large files
        if len(content) > 1000000:  # 1MB
            logger.debug("Skipping tokenization for large file")
            return False
        
        return True
