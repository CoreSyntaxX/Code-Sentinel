#!/usr/bin/env python3
"""
Example showing how to use the models.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.finding import Finding, Severity, Category, Location
from src.models.scan_context import ScanContext, ScanSettings, TargetType, ScanMode
from src.models.rule import Rule, RuleType, RuleLanguage


def create_sample_scan():
    """Create a sample scan with findings."""
    
    # 1. Setup scan settings
    settings = ScanSettings(
        target="/var/www/myapp",
        target_type=TargetType.LOCAL_DIRECTORY,
        mode="normal",
        enable_secret_detection=True,
        enable_dom_xss_detection=True,
    )
    
    # 2. Create scan context
    context = ScanContext(settings=settings)
    
    # 3. Define some detection rules
    rules = [
        Rule(
            id="JS-DOM-XSS-001",
            name="innerHTML Sink",
            rule_type=RuleType.REGEX,
            languages=[RuleLanguage.JAVASCRIPT],
            severity=Severity.HIGH,
            category=Category.DOM_XSS,
            pattern=r"\.innerHTML\s*=",
            description="Direct assignment to innerHTML can lead to XSS.",
            remediation="Use textContent or proper sanitization.",
        ),
        Rule(
            id="SECRET-API-KEY-001",
            name="Hardcoded API Key",
            rule_type=RuleType.REGEX,
            languages=[RuleLanguage.GENERIC],
            severity=Severity.CRITICAL,
            category=Category.API_KEY_EXPOSURE,
            pattern=r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]([a-zA-Z0-9_-]{20,})['\"]",
            description="Hardcoded API key or secret found.",
            remediation="Use environment variables or secure secret storage.",
        ),
    ]
    
    # 4. Simulate finding some issues
    findings_data = [
        {
            "file": "app.js",
            "line": 42,
            "code": "element.innerHTML = userContent;",
            "rule_id": "JS-DOM-XSS-001",
            "title": "Unsafe DOM Manipulation",
        },
        {
            "file": "config.js",
            "line": 15,
            "code": 'const api_key = "sk_live_1234567890abcdef";',
            "rule_id": "SECRET-API-KEY-001",
            "title": "Hardcoded API Key",
        },
    ]
    
    # 5. Create findings and add to context
    for data in findings_data:
        location = Location(
            file_path=data["file"],
            line_start=data["line"],
            code_snippet=data["code"],
        )
        
        # Find the matching rule
        rule = next(r for r in rules if r.id == data["rule_id"])
        
        finding = Finding(
            title=data["title"],
            severity=rule.severity,
            category=rule.category,
            location=location,
            description=rule.description,
            recommendation=rule.remediation,
            rule_id=rule.id,
            vulnerable_code=data["code"],
        )
        
        context.add_finding(finding)
    
    # 6. Display results
    print("Scan Results:")
    print("-" * 50)
    
    for i, finding in enumerate(context.findings, 1):
        print(f"{i}. {finding}")
        print(f"   File: {finding.location.file_path}:{finding.location.line_start}")
        print(f"   Code: {finding.vulnerable_code}")
        print(f"   Severity: {finding.severity.value}")
        print()
    
    # 7. Show summary
    summary = context.get_summary()
    print("Scan Summary:")
    print(f"  Total Files: {summary['total_files']}")
    print(f"  Total Findings: {summary['total_findings']}")
    print(f"  By Severity: {summary['findings_by_severity']}")
    print(f"  By Category: {summary['findings_by_category']}")


if __name__ == "__main__":
    create_sample_scan()
