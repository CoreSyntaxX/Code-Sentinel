#!/usr/bin/env python3
"""
Test the data models.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.finding import Finding, Severity, Category, Location
from src.models.scan_context import ScanContext, ScanSettings, TargetType, ScanMode
from src.models.rule import Rule, RuleType, RuleLanguage


def test_finding_model():
    """Test Finding model creation."""
    print("Testing Finding model...")
    
    # Create a location
    location = Location(
        file_path="/app/src/index.js",
        line_start=42,
        line_end=42,
        code_snippet="document.innerHTML = userInput;"
    )
    
    # Create a finding
    finding = Finding(
        title="Unsafe DOM Manipulation",
        severity=Severity.HIGH,
        category=Category.DOM_XSS,
        location=location,
        description="User input is directly assigned to innerHTML without sanitization.",
        recommendation="Use textContent instead or sanitize with DOMPurify.",
        rule_id="JS-DOM-XSS-001",
        confidence=0.9,
        vulnerable_code="document.innerHTML = userInput;",
        detector_name="DOMSinkDetector",
        tags=["dom-xss", "javascript", "client-side"],
    )
    
    print(f"Finding created: {finding}")
    print(f"Unique ID: {finding.unique_id}")
    print(f"To dict: {finding.to_dict()}")
    print("✓ Finding model test passed\n")
    return finding


def test_scan_context():
    """Test ScanContext model."""
    print("Testing ScanContext model...")
    
    settings = ScanSettings(
        target="/home/user/project",
        target_type=TargetType.LOCAL_DIRECTORY,
        mode=ScanMode.NORMAL,
        max_file_size_mb=5,
        verbose=True,
    )
    
    context = ScanContext(settings=settings)
    
    # Add a finding
    location = Location(file_path="test.js", line_start=10)
    finding = Finding(
        title="Test Finding",
        severity=Severity.MEDIUM,
        category=Category.OTHER,
        location=location,
        description="Test description",
        recommendation="Test fix",
        rule_id="TEST-001",
    )
    
    context.add_finding(finding)
    
    print(f"Context settings: {settings}")
    print(f"Total findings: {len(context.findings)}")
    print(f"Summary: {context.get_summary()}")
    print("✓ ScanContext test passed\n")
    return context


def test_rule_model():
    """Test Rule model."""
    print("Testing Rule model...")
    
    rule = Rule(
        id="JS-DOM-XSS-001",
        name="Unsafe innerHTML Assignment",
        rule_type=RuleType.REGEX,
        languages=[RuleLanguage.JAVASCRIPT, RuleLanguage.HTML],
        severity=Severity.HIGH,
        category=Category.DOM_XSS,
        pattern=r"\.innerHTML\s*=\s*[^;]+",
        description="Detects direct assignment to innerHTML property.",
        remediation="Use textContent or proper sanitization.",
        references=["https://owasp.org/www-community/attacks/DOM_Based_XSS"],
        cwe_ids=["CWE-79"],
        owasp_top_10=["A7:2017-Cross-Site Scripting (XSS)"],
    )
    
    # Test matching
    test_code = """
    function updateContent() {
        document.innerHTML = userData;
        element.innerHTML = "<div>" + unsanitized + "</div>";
        safeElement.textContent = "safe";
    }
    """
    
    matches = rule.match(test_code, "test.js")
    
    print(f"Rule ID: {rule.id}")
    print(f"Rule name: {rule.name}")
    print(f"Matches found: {len(matches)}")
    for match in matches:
        print(f"  - Line {match['line_start']}: {match['matched_text'][:50]}...")
    
    print("✓ Rule model test passed\n")
    return rule


def test_integration():
    """Test models working together."""
    print("Testing model integration...")
    
    # Create a rule
    rule = Rule(
        id="JS-SECRET-001",
        name="Potential API Key Leak",
        rule_type=RuleType.REGEX,
        languages=[RuleLanguage.JAVASCRIPT],
        severity=Severity.CRITICAL,
        category=Category.API_KEY_EXPOSURE,
        pattern=r"(api[_-]?key|secret|token)\s*[:=]\s*['\"]([a-zA-Z0-9_-]{20,})['\"]",
        description="Potential hardcoded API key or secret.",
        remediation="Store secrets in environment variables or secure vault.",
    )
    
    # Create scan context
    settings = ScanSettings(
        target="test_project",
        target_type=TargetType.LOCAL_DIRECTORY,
    )
    context = ScanContext(settings=settings)
    
    # Simulate finding detection
    test_file = """
    const config = {
        api_key: "sk_live_1234567890abcdefghijklmn",
        secret: "my_super_secret_token_here"
    };
    """
    
    matches = rule.match(test_file, "config.js")
    for match in matches:
        location = Location(
            file_path=match["file_path"],
            line_start=match["line_start"],
            line_end=match["line_end"],
            code_snippet=match["line_content"],
        )
        
        finding = Finding(
            title="Hardcoded API Key Detected",
            severity=rule.severity,
            category=rule.category,
            location=location,
            description=rule.description,
            recommendation=rule.remediation,
            rule_id=rule.id,
            confidence=0.8,
            vulnerable_code=match["matched_text"],
            detector_name="SecretDetector",
            tags=["api-key", "secret-leak", "hardcoded"],
        )
        
        context.add_finding(finding)
    
    print(f"Total findings in context: {len(context.findings)}")
    for i, finding in enumerate(context.findings, 1):
        print(f"{i}. {finding}")
    
    print("\n✓ Integration test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Security Scanner Data Models")
    print("=" * 60)
    
    try:
        finding = test_finding_model()
        context = test_scan_context()
        rule = test_rule_model()
        test_integration()
        
        print("=" * 60)
        print("All model tests passed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
