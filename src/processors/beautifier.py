"""
JavaScript beautifier - formats minified JavaScript for better analysis.
"""

import re
import logging
from typing import Optional, List, Tuple, Dict, Any

from models.scan_context import ScanContext
from processors.base_processor import BaseProcessor


logger = logging.getLogger(__name__)


class JavaScriptBeautifier(BaseProcessor):
    """
    Beautifies minified JavaScript code for easier analysis.
    Basic formatting without external dependencies.
    """
    
    def __init__(self):
        super().__init__()
        
        # Keywords that should have spaces after
        self.keywords = [
            'var', 'let', 'const', 'function', 'return', 'if', 'else',
            'for', 'while', 'do', 'switch', 'case', 'break', 'continue',
            'try', 'catch', 'finally', 'throw', 'new', 'delete', 'typeof',
            'instanceof', 'void', 'in', 'of', 'async', 'await', 'yield',
            'class', 'extends', 'super', 'import', 'export', 'default',
            'static', 'get', 'set'
        ]
        
        # Operators that need spaces
        self.operators = [
            '=', '==', '===', '!=', '!==', '>', '<', '>=', '<=',
            '+', '-', '*', '/', '%', '**', '+=', '-=', '*=', '/=', '%=',
            '&&', '||', '!', '&', '|', '^', '~', '<<', '>>', '>>>',
            '&=', '|=', '^=', '<<=', '>>=', '>>>=', '?', ':', '=>'
        ]
        
        # Punctuation that should have spaces after in some contexts
        self.punctuation = [',', ';']
        
        # Brackets and braces
        self.brackets = ['(', ')', '[', ']', '{', '}']
    
    def get_name(self) -> str:
        return "JavaScriptBeautifier"
    
    def process(self, content: str, context: ScanContext) -> str:
        """
        Beautify JavaScript code.
        
        Args:
            content: JavaScript code to beautify
            context: Scan context
            
        Returns:
            Beautified code
        """
        if not self.should_process(content):
            return content
        
        logger.debug(f"Beautifying JavaScript (length: {len(content)})")
        
        # Check if it's actually JavaScript
        file_path = getattr(context, "current_file", None)
        file_path_str = str(file_path) if file_path else None
        if self._detect_language(content, file_path=file_path_str) != 'javascript':
            return content
        
        # Check if it's minified (skip if not)
        if not self._is_minified(content):
            logger.debug("Code doesn't appear minified, skipping beautification")
            return content
        
        # Step 1: Basic tokenization
        tokens = self._tokenize(content)
        
        # Step 2: Format tokens with proper indentation
        formatted = self._format_tokens(tokens)
        
        logger.debug(f"Beautified from {len(content)} to {len(formatted)} chars")
        return formatted
    
    def _tokenize(self, content: str) -> List[Tuple[str, str]]:
        """
        Tokenize JavaScript code.
        
        Returns:
            List of (token_type, token_value) tuples
        """
        tokens = []
        i = 0
        length = len(content)
        
        while i < length:
            char = content[i]
            
            # Skip whitespace
            if char.isspace():
                i += 1
                continue
            
            # Check for comments
            if char == '/' and i + 1 < length:
                next_char = content[i + 1]
                
                # Single-line comment
                if next_char == '/':
                    end = content.find('\n', i)
                    if end == -1:
                        end = length
                    comment = content[i:end]
                    tokens.append(('COMMENT', comment))
                    i = end
                    continue
                
                # Multi-line comment
                elif next_char == '*':
                    end = content.find('*/', i)
                    if end == -1:
                        end = length
                    else:
                        end += 2
                    comment = content[i:end]
                    tokens.append(('COMMENT', comment))
                    i = end
                    continue
            
            # Check for strings
            if char in ('"', "'", '`'):
                string_char = char
                j = i + 1
                while j < length:
                    if content[j] == '\\':
                        j += 2  # Skip escaped character
                        continue
                    if content[j] == string_char:
                        j += 1
                        break
                    j += 1
                string = content[i:j]
                tokens.append(('STRING', string))
                i = j
                continue
            
            # Check for regex literals
            if char == '/' and i > 0:
                # Check if previous token could be part of expression
                prev_char = content[i-1] if i > 0 else ''
                if prev_char in ('(', ',', '=', ':', '[', '?', '!', '&', '|', '^', '~', '+', '-', '*', '/', '%', '<', '>', ';', '{', '}'):
                    j = i + 1
                    in_char_class = False
                    while j < length:
                        if content[j] == '\\':
                            j += 2
                            continue
                        if content[j] == '[':
                            in_char_class = True
                        elif content[j] == ']':
                            in_char_class = False
                        elif content[j] == '/' and not in_char_class:
                            j += 1
                            # Check for regex flags
                            while j < length and content[j].isalpha():
                                j += 1
                            break
                        j += 1
                    regex = content[i:j]
                    tokens.append(('REGEX', regex))
                    i = j
                    continue
            
            # Check for numbers
            if char.isdigit() or (char == '.' and i + 1 < length and content[i+1].isdigit()):
                j = i
                while j < length and (content[j].isdigit() or content[j] in '.eE+-'):
                    j += 1
                number = content[i:j]
                tokens.append(('NUMBER', number))
                i = j
                continue
            
            # Check for identifiers and keywords
            if char.isalpha() or char == '_' or char == '$':
                j = i
                while j < length and (content[j].isalnum() or content[j] in '_$'):
                    j += 1
                identifier = content[i:j]
                
                # Check if it's a keyword
                if identifier in self.keywords:
                    tokens.append(('KEYWORD', identifier))
                else:
                    tokens.append(('IDENTIFIER', identifier))
                i = j
                continue
            
            # Check for operators
            operator_found = False
            for operator in sorted(self.operators, key=len, reverse=True):
                if content.startswith(operator, i):
                    tokens.append(('OPERATOR', operator))
                    i += len(operator)
                    operator_found = True
                    break
            
            if operator_found:
                continue
            
            # Check for punctuation
            if char in self.punctuation:
                tokens.append(('PUNCTUATION', char))
                i += 1
                continue
            
            # Check for brackets
            if char in self.brackets:
                tokens.append(('BRACKET', char))
                i += 1
                continue
            
            # Unknown character
            tokens.append(('UNKNOWN', char))
            i += 1
        
        return tokens
    
    def _format_tokens(self, tokens: List[Tuple[str, str]]) -> str:
        """
        Format tokens with proper indentation and spacing.
        """
        lines = []
        current_line = []
        indent_level = 0
        i = 0
        
        while i < len(tokens):
            token_type, token_value = tokens[i]
            
            # Handle indentation for braces
            if token_value == '}':
                indent_level = max(0, indent_level - 1)
            
            # Start new line for certain tokens
            if self._should_start_new_line(token_type, token_value, tokens, i):
                if current_line:
                    lines.append('    ' * indent_level + ' '.join(current_line))
                    current_line = []
            
            # Add token to current line
            if token_type not in ('COMMENT',):
                current_line.append(token_value)
            
            # Handle comments on their own line
            if token_type == 'COMMENT':
                if current_line:
                    lines.append('    ' * indent_level + ' '.join(current_line))
                    current_line = []
                lines.append('    ' * indent_level + token_value)
            
            # Handle indentation after certain tokens
            if token_value == '{':
                indent_level += 1
                if current_line:
                    lines.append('    ' * (indent_level - 1) + ' '.join(current_line))
                    current_line = []
            
            i += 1
        
        # Add any remaining tokens
        if current_line:
            lines.append('    ' * indent_level + ' '.join(current_line))
        
        return '\n'.join(lines)
    
    def _should_start_new_line(self, token_type: str, token_value: str, 
                               tokens: List[Tuple[str, str]], index: int) -> bool:
        """Determine if we should start a new line."""
        if not tokens:
            return False
        
        # Semicolons end statements
        if token_value == ';':
            return True
        
        # Keywords that typically start blocks
        if token_value in ('function', 'if', 'else', 'for', 'while', 'do', 'switch', 
                          'try', 'catch', 'finally', 'class'):
            # Check if this is actually the start of a block
            if index + 1 < len(tokens) and tokens[index + 1][1] == '{':
                return True
        
        # Return statements
        if token_value == 'return' and index > 0:
            prev_type, prev_value = tokens[index - 1]
            if prev_value == ';' or prev_value == '}':
                return True
        
        return False
    
    def should_process(self, content: str, file_path: Optional[str] = None) -> bool:
        """Only process JavaScript files that appear minified."""
        if not self.enabled or not content.strip():
            return False
        
        # Check file extension if provided
        if file_path:
            if not file_path.lower().endswith(('.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs')):
                return False
        
        # Check if it's JavaScript
        if self._detect_language(content) != 'javascript':
            return False
        
        # Check if it's minified
        return self._is_minified(content)
