"""
JavaScript analyzer package.
"""

from .analyzer import JavaScriptAnalyzer
from .dom_sink_detector import DOMSinkDetector
from .ast_parser import JSASTParser

__all__ = ['JavaScriptAnalyzer', 'DOMSinkDetector', 'JSASTParser']