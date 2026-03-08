"""
Rule engine for loading, managing, and executing detection rules.
"""

import yaml
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from dataclasses import dataclass, field
import re

from models.rule import Rule, RuleType, RuleLanguage
from models.finding import Finding, Location, Severity, Category


logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Manages security detection rules.
    """
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.rule_groups: Dict[str, List[Rule]] = {
            "javascript": [],
            "php": [],
            "html": [],
            "secrets": [],
            "generic": [],
        }
    
    def load_rules_from_directory(self, rules_dir: Path):
        """
        Load rules from YAML/JSON files in a directory.
        
        Args:
            rules_dir: Directory containing rule files
        """
        if not rules_dir.exists():
            logger.warning(f"Rules directory not found: {rules_dir}")
            return
        
        logger.info(f"Loading rules from {rules_dir}")
        
        # Load YAML files
        for rule_file in rules_dir.glob("**/*.yaml"):
            self._load_rule_file(rule_file)
        
        for rule_file in rules_dir.glob("**/*.yml"):
            self._load_rule_file(rule_file)
        
        # Load JSON files
        for rule_file in rules_dir.glob("**/*.json"):
            self._load_rule_file(rule_file)
        
        logger.info(f"Loaded {len(self.rules)} rules")
        
        # Organize rules into groups
        self._organize_rules()
    
    def _load_rule_file(self, rule_file: Path):
        """Load rules from a single file."""
        try:
            with open(rule_file, 'r', encoding='utf-8') as f:
                if rule_file.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # Handle both single rule and list of rules
            if isinstance(data, dict):
                rules_data = [data]
            elif isinstance(data, list):
                rules_data = data
            else:
                logger.warning(f"Invalid rule format in {rule_file}")
                return
            
            for rule_data in rules_data:
                self._create_rule_from_dict(rule_data, rule_file)
                
        except Exception as e:
            logger.error(f"Failed to load rule file {rule_file}: {e}")
    
    def _create_rule_from_dict(self, rule_dict: Dict[str, Any], source_file: Path):
        """Create a Rule object from dictionary data."""
        try:
            # Extract basic fields
            rule_id = rule_dict.get("id")
            if not rule_id:
                logger.warning(f"Rule missing ID in {source_file}")
                return
            
            # Check if rule already exists
            if rule_id in self.rules:
                logger.debug(f"Rule {rule_id} already loaded, skipping")
                return
            
            # Parse enum fields
            rule_type = RuleType(rule_dict.get("type", "regex"))
            
            languages = []
            for lang_str in rule_dict.get("languages", []):
                try:
                    languages.append(RuleLanguage(lang_str))
                except ValueError:
                    logger.warning(f"Unknown language {lang_str} in rule {rule_id}")
            
            severity = Severity(rule_dict.get("severity", "medium").upper())
            category = Category(rule_dict.get("category", "OTHER"))
            
            # Create rule
            rule = Rule(
                id=rule_id,
                name=rule_dict.get("name", ""),
                rule_type=rule_type,
                languages=languages,
                severity=severity,
                category=category,
                pattern=rule_dict.get("pattern"),
                requires_context=rule_dict.get("requires_context", False),
                context_before=rule_dict.get("context_before"),
                context_after=rule_dict.get("context_after"),
                validator_regex=rule_dict.get("validator_regex"),
                min_confidence=rule_dict.get("min_confidence", 0.7),
                description=rule_dict.get("description", ""),
                remediation=rule_dict.get("remediation", ""),
                references=rule_dict.get("references", []),
                cwe_ids=rule_dict.get("cwe_ids", []),
                owasp_top_10=rule_dict.get("owasp_top_10", []),
                enabled=rule_dict.get("enabled", True),
                priority=rule_dict.get("priority", 1),
            )
            
            # Store rule
            self.rules[rule_id] = rule
            logger.debug(f"Loaded rule: {rule_id}")
            
        except Exception as e:
            logger.error(f"Failed to create rule from {source_file}: {e}")
    
    def _organize_rules(self):
        """Organize rules into language groups for faster access."""
        for rule in self.rules.values():
            for lang in rule.languages:
                if lang.value in self.rule_groups:
                    self.rule_groups[lang.value].append(rule)
    
    def get_rules_for_language(self, language: RuleLanguage) -> List[Rule]:
        """Get rules applicable to a specific language."""
        return self.rule_groups.get(language.value, [])
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)
    
    def enable_rule(self, rule_id: str):
        """Enable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
    
    def disable_rule(self, rule_id: str):
        """Disable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
    
    def execute_rule_on_content(self, rule_id: str, content: str, 
                                file_path: Path) -> List[Finding]:
        """
        Execute a specific rule on content and return findings.
        
        Args:
            rule_id: ID of the rule to execute
            content: Content to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            List of findings
        """
        rule = self.get_rule(rule_id)
        if not rule or not rule.enabled:
            return []
        
        findings = []
        matches = rule.match(content, str(file_path))
        
        for match in matches:
            # Create location
            location = Location(
                file_path=str(file_path),
                line_start=match["line_start"],
                line_end=match["line_end"],
                code_snippet=match["line_content"],
            )
            
            # Create finding
            finding = Finding(
                title=rule.name,
                severity=rule.severity,
                category=rule.category,
                location=location,
                description=rule.description,
                recommendation=rule.remediation,
                rule_id=rule.id,
                confidence=rule.min_confidence,
                vulnerable_code=match["matched_text"],
                context_before=match.get("context_before"),
                context_after=match.get("context_after"),
                tags=[lang.value for lang in rule.languages],
            )
            
            findings.append(finding)
        
        return findings
    
    def execute_all_rules(self, content: str, file_path: Path, 
                          languages: List[RuleLanguage]) -> List[Finding]:
        """
        Execute all applicable rules on content.
        
        Args:
            content: Content to analyze
            file_path: Path to the file
            languages: Languages to consider
            
        Returns:
            List of all findings
        """
        all_findings = []
        
        # Get applicable rules
        applicable_rules = []
        for language in languages:
            applicable_rules.extend(self.get_rules_for_language(language))
        
        # Remove duplicates (rules might apply to multiple languages)
        seen_rule_ids = set()
        unique_rules = []
        for rule in applicable_rules:
            if rule.id not in seen_rule_ids:
                seen_rule_ids.add(rule.id)
                unique_rules.append(rule)
        
        # Sort by priority (higher priority first)
        unique_rules.sort(key=lambda r: r.priority, reverse=True)
        
        # Execute rules
        for rule in unique_rules:
            if rule.enabled:
                findings = self.execute_rule_on_content(rule.id, content, file_path)
                all_findings.extend(findings)
        
        return all_findings
