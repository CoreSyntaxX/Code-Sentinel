"""
AST-based JavaScript parser for deeper code analysis.
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from models.finding import Finding, Severity, Category, Location
from models.scan_context import ScanContext


logger = logging.getLogger(__name__)


class JSASTParser:
    """
    AST-based parser for JavaScript analysis.
    Provides more accurate analysis than regex patterns.
    """
    
    def __init__(self):
        self._esprima_available = False
        self._initialize_parser()
    
    def _initialize_parser(self):
        """Initialize the AST parser if available."""
        try:
            import esprima
            self._esprima_available = True
            self.esprima = esprima
            logger.debug("Esprima parser initialized")
        except ImportError:
            logger.warning("Esprima not installed. AST parsing disabled.")
            self._esprima_available = False
    
    def analyze(self, content: str, file_path: Path, context: ScanContext) -> List[Finding]:
        """
        Analyze JavaScript using AST parsing.
        
        Args:
            content: JavaScript content
            file_path: Path to the file
            context: Scan context
            
        Returns:
            List of findings from AST analysis
        """
        findings = []
        
        if not self._esprima_available:
            return findings
        
        try:
            import esprima
            
            # Parse JavaScript to AST
            ast = esprima.parseScript(content, {
                'range': True,
                'loc': True,
                'comment': True
            })
            
            # Analyze AST for vulnerabilities
            findings.extend(self._analyze_ast_nodes(ast, file_path))
            
        except Exception as e:
            logger.warning(f"AST parsing failed for {file_path}: {e}")
        
        return findings
    
    def _analyze_ast_nodes(self, ast, file_path: Path) -> List[Finding]:
        """Traverse AST nodes and analyze for vulnerabilities."""
        findings = []
        
        # Use a stack or recursive traversal
        # For simplicity, we'll use a recursive approach
        nodes_to_visit = [ast]
        
        while nodes_to_visit:
            node = nodes_to_visit.pop()
            
            # Skip if node is None
            if node is None:
                continue
            
            # Check node type and analyze
            if hasattr(node, 'type'):
                node_findings = self._analyze_node(node, file_path)
                findings.extend(node_findings)
            
            # Add child nodes to visit
            for key, value in node.__dict__.items():
                if key.startswith('_') or key in ['type', 'loc', 'range']:
                    continue
                
                if isinstance(value, list):
                    nodes_to_visit.extend(value)
                elif hasattr(value, '__dict__'):  # It's an object with attributes
                    nodes_to_visit.append(value)
        
        return findings
    
    def _analyze_node(self, node, file_path: Path) -> List[Finding]:
        """Analyze a single AST node for vulnerabilities."""
        findings = []
        
        try:
            if node.type == 'AssignmentExpression':
                findings.extend(self._analyze_assignment(node, file_path))
            
            elif node.type == 'CallExpression':
                findings.extend(self._analyze_call(node, file_path))
            
            elif node.type == 'MemberExpression':
                findings.extend(self._analyze_member_expression(node, file_path))
        
        except Exception as e:
            logger.debug(f"Error analyzing node: {e}")
        
        return findings
    
    def _analyze_assignment(self, node, file_path: Path) -> List[Finding]:
        """Analyze assignment expressions."""
        findings = []
        
        try:
            # Check for innerHTML assignments
            if (hasattr(node.left, 'property') and 
                hasattr(node.left.property, 'name') and
                node.left.property.name == 'innerHTML'):
                
                # Get line number from location
                line = node.loc.start.line if hasattr(node, 'loc') and node.loc else 1
                
                # Create finding
                location = Location(
                    file_path=str(file_path),
                    line_start=line,
                    code_snippet=self._get_node_source(node, 100),
                )
                
                finding = Finding(
                    title="Unsafe innerHTML Assignment (AST)",
                    severity=Severity.HIGH,
                    category=Category.DOM_XSS,
                    location=location,
                    description="AST analysis detected direct assignment to innerHTML property.",
                    recommendation="Use textContent or sanitize with DOMPurify.",
                    rule_id="JS-AST-INNERHTML",
                    confidence=0.9,
                    detector_name="JSASTParser",
                    tags=["ast-analysis", "dom-xss", "javascript"],
                )
                
                findings.append(finding)
        
        except Exception as e:
            logger.debug(f"Error analyzing assignment: {e}")
        
        return findings
    
    def _analyze_call(self, node, file_path: Path) -> List[Finding]:
        """Analyze function call expressions."""
        findings = []
        
        try:
            # Check for eval() calls
            if (hasattr(node.callee, 'name') and 
                node.callee.name == 'eval'):
                
                line = node.loc.start.line if hasattr(node, 'loc') and node.loc else 1
                
                location = Location(
                    file_path=str(file_path),
                    line_start=line,
                    code_snippet=self._get_node_source(node, 100),
                )
                
                finding = Finding(
                    title="eval() Function Call (AST)",
                    severity=Severity.CRITICAL,
                    category=Category.DOM_XSS,
                    location=location,
                    description="AST analysis detected eval() function call.",
                    recommendation="Avoid eval(), use JSON.parse() or Function() with extreme caution.",
                    rule_id="JS-AST-EVAL",
                    confidence=0.95,
                    detector_name="JSASTParser",
                    tags=["ast-analysis", "eval", "javascript"],
                )
                
                findings.append(finding)
        
        except Exception as e:
            logger.debug(f"Error analyzing call: {e}")
        
        return findings
    
    def _analyze_member_expression(self, node, file_path: Path) -> List[Finding]:
        """Analyze member expressions (object.property)."""
        findings = []
        
        try:
            # Check for document.write
            if (hasattr(node, 'object') and hasattr(node.object, 'name') and
                node.object.name == 'document' and
                hasattr(node, 'property') and hasattr(node.property, 'name') and
                node.property.name == 'write'):
                
                line = node.loc.start.line if hasattr(node, 'loc') and node.loc else 1
                
                location = Location(
                    file_path=str(file_path),
                    line_start=line,
                    code_snippet=self._get_node_source(node, 100),
                )
                
                finding = Finding(
                    title="document.write() Usage (AST)",
                    severity=Severity.HIGH,
                    category=Category.DOM_XSS,
                    location=location,
                    description="AST analysis detected document.write() call.",
                    recommendation="Avoid document.write() with dynamic content.",
                    rule_id="JS-AST-DOCWRITE",
                    confidence=0.9,
                    detector_name="JSASTParser",
                    tags=["ast-analysis", "document.write", "javascript"],
                )
                
                findings.append(finding)
        
        except Exception as e:
            logger.debug(f"Error analyzing member expression: {e}")
        
        return findings
    
    def _get_node_source(self, node, max_length: int = 100) -> str:
        """Get source code for a node (if range is available)."""
        try:
            if hasattr(node, 'range'):
                start, end = node.range
                # We would need the original content here
                # For now, return a placeholder
                return f"AST Node: {node.type}"
        except:
            pass
        return f"AST Node: {node.type}"
