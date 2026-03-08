"""
Rule model - defines detection rules and patterns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Pattern
from enum import Enum
import re
from models.finding import Severity, Category


class RuleType(Enum):
    """Types of detection rules."""
    REGEX = "regex"                # Regular expression pattern
    AST_PATTERN = "ast_pattern"    # AST node pattern
    STRING_MATCH = "string_match"  # Exact string match
    ENTROPY = "entropy"            # Entropy-based detection
    COMBINATION = "combination"    # Combination of rules


class RuleLanguage(Enum):
    """Supported programming languages for rules."""
    JAVASCRIPT = "javascript"
    PHP = "php"
    HTML = "html"
    PYTHON = "python"
    JAVA = "java"
    GENERIC = "generic"  # Cross-language rules


@dataclass
class Rule:
    """A detection rule for security issues."""
    # Identification
    id: str  # e.g., "JS-DOM-XSS-001"
    name: str
    
    # Rule properties
    rule_type: RuleType
    languages: List[RuleLanguage]
    severity: Severity
    category: Category
    
    # Detection logic
    pattern: Optional[str] = None  # Regex pattern, AST pattern, etc.
    compiled_pattern: Optional[Pattern] = field(init=False, default=None)
    
    # Context requirements
    requires_context: bool = False
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    
    # Validation
    validator_regex: Optional[str] = None  # To filter false positives
    min_confidence: float = 0.7
    
    # Metadata
    description: str = ""
    remediation: str = ""
    references: List[str] = field(default_factory=list)
    cwe_ids: List[str] = field(default_factory=list)
    owasp_top_10: List[str] = field(default_factory=list)
    
    # Performance
    enabled: bool = True
    priority: int = 1  # 1-10, higher = check earlier
    
    def __post_init__(self):
        """Compile regex pattern if provided."""
        if self.pattern and self.rule_type == RuleType.REGEX:
            try:
                self.compiled_pattern = re.compile(self.pattern, re.MULTILINE | re.DOTALL)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern in rule {self.id}: {e}")
    
    def match(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """
        Match the rule against content.
        Returns list of matches with location information.
        """
        matches = []
        
        if not self.enabled or not self.compiled_pattern:
            return matches
        
        for match in self.compiled_pattern.finditer(content):
            # Calculate line numbers
            line_start = content[:match.start()].count('\n') + 1
            line_end = content[:match.end()].count('\n') + 1
            
            # Extract context
            lines = content.split('\n')
            line_content = lines[line_start - 1] if line_start <= len(lines) else ""
            
            # Get surrounding context
            context_before = '\n'.join(lines[max(0, line_start - 3):line_start - 1])
            context_after = '\n'.join(lines[line_end:min(len(lines), line_end + 2)])
            
            matches.append({
                "start": match.start(),
                "end": match.end(),
                "line_start": line_start,
                "line_end": line_end,
                "matched_text": match.group(),
                "line_content": line_content,
                "context_before": context_before,
                "context_after": context_after,
                "groups": match.groups(),
                "file_path": file_path,
            })
        
        return matches
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.rule_type.value,
            "languages": [lang.value for lang in self.languages],
            "severity": self.severity.value,
            "category": self.category.value,
            "pattern": self.pattern,
            "description": self.description,
            "remediation": self.remediation,
            "references": self.references,
            "cwe_ids": self.cwe_ids,
            "owasp_top_10": self.owasp_top_10,
            "enabled": self.enabled,
            "priority": self.priority,
        }


@dataclass
class RuleSet:
    """Collection of rules organized by language/category."""
    rules: Dict[str, Rule] = field(default_factory=dict)
    
    def add_rule(self, rule: Rule):
        """Add a rule to the set."""
        self.rules[rule.id] = rule
    
    def get_rules_for_language(self, language: RuleLanguage) -> List[Rule]:
        """Get all rules applicable to a specific language."""
        return [
            rule for rule in self.rules.values()
            if language in rule.languages and rule.enabled
        ]
    
    def get_rules_by_category(self, category: Category) -> List[Rule]:
        """Get all rules for a specific category."""
        return [
            rule for rule in self.rules.values()
            if rule.category == category and rule.enabled
        ]
    
    def load_from_yaml(self, yaml_path: str):
        """Load rules from YAML file (to be implemented)."""
        # TODO: Implement YAML loading
        pass
