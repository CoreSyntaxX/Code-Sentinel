"""
Processors package for code transformation and normalization.
"""

from .base_processor import BaseProcessor
from .normalizer import CodeNormalizer
from .beautifier import JavaScriptBeautifier
from .minifier import MinifiedCodeDetector
from .tokenizer import CodeTokenizer
from .deobfuscator import CodeDeobfuscator

__all__ = [
    'BaseProcessor',
    'CodeNormalizer',
    'JavaScriptBeautifier',
    'MinifiedCodeDetector',
    'CodeTokenizer',
    'CodeDeobfuscator',
]