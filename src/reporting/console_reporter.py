"""
Console reporter - CLI output with colors and formatting.
"""

import sys
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from models.scan_context import ScanContext
from models.finding import Severity
from reporting.base_reporter import BaseReporter


logger = logging.getLogger(__name__)


class ConsoleReporter(BaseReporter):
    """
    Console reporter for terminal output.
    Uses colors and formatting for readability.
    """
    
    def __init__(self):
        super().__init__()
        # ANSI color codes
        self.colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'orange': '\033[38;5;208m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'gray': '\033[90m',
            'bold': '\033[1m',
            'underline': '\033[4m',
            'reset': '\033[0m',
        }
        
        # Check if terminal supports colors
        self.supports_color = self._check_color_support()
    
    def get_name(self) -> str:
        return "ConsoleReporter"
    
    def get_extension(self) -> str:
        return "txt"  # Not really used for console
    
    def generate_report(self, context: ScanContext, output_path: Optional[Path] = None) -> Path:
        """
        Print report to console.
        """
        logger.info("Generating console report...")
        
        # Prepare data
        report_data = self._prepare_report_data(context)
        
        # Print to console
        self._print_report(report_data, context)
        
        # For console, we don't save a file, but return a dummy path
        return Path("/dev/stdout")
    
    def _check_color_support(self) -> bool:
        """Check if terminal supports colors."""
        try:
            import sys
            return sys.stdout.isatty()
        except:
            return False
    
    def _colorize(self, text: str, color: str) -> str:
        """Add color to text if supported."""
        if self.supports_color and color in self.colors:
            return f"{self.colors[color]}{text}{self.colors['reset']}"
        return text
    
    def _print_report(self, report_data: Dict[str, Any], context: ScanContext):
        """Print formatted report to console."""
        print("\n" + "=" * 70)
        print(self._colorize(" SECURITY SCAN REPORT ", "bold"))
        print("=" * 70)
        
        # Summary
        print("\n" + self._colorize("📊 SUMMARY", "bold"))
        print("-" * 40)
        
        risk_score = report_data['metadata']['risk_score']
        risk_color = "red" if risk_score >= 75 else "orange" if risk_score >= 50 else "yellow" if risk_score >= 25 else "green"
        
        print(f"Risk Score: {self._colorize(f'{risk_score:.1f}/100', risk_color)}")
        print(f"Target: {report_data['metadata']['scan_target']}")
        print(f"Mode: {report_data['metadata']['scan_mode'].upper()}")
        print(f"Duration: {self._format_duration(report_data['metadata']['duration_seconds'])}")
        print()
        
        # Severity breakdown
        print(self._colorize("Findings by Severity:", "bold"))
        for severity, count in [
            ("CRITICAL", report_data['summary']['critical_count']),
            ("HIGH", report_data['summary']['high_count']),
            ("MEDIUM", report_data['summary']['medium_count']),
            ("LOW", report_data['summary']['low_count']),
            ("INFO", report_data['summary']['info_count']),
        ]:
            if count > 0:
                severity_color = self._get_severity_color_name(severity)
                severity_icon = self._get_severity_icon(severity)
                print(f"  {severity_icon} {severity:10} {self._colorize(str(count).rjust(3), severity_color)}")
        
        print(f"\n  Total: {report_data['summary']['total_findings']} findings in {report_data['summary']['files_with_findings']} files")
        print(f"  Files scanned: {report_data['summary']['total_files_scanned']}")

        # Sensitive paths
        if report_data.get("sensitive_paths"):
            print("\n" + self._colorize("Sensitive Paths:", "bold"))
            for item in report_data["sensitive_paths"]:
                location = f"{item['file_path']}:{item.get('line_start', '')}".rstrip(':')
                print(f"  • {item['path']}  [{location}]")
        
        # Top categories
        category_counts = {}
        for finding in report_data['all_findings']:
            category = finding['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        if category_counts:
            print("\n" + self._colorize("Top Categories:", "bold"))
            sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            for category, count in sorted_categories:
                print(f"  • {category}: {count}")
        
        # Critical/High findings
        critical_high = [
            f for f in report_data['all_findings'] 
            if f['severity'] in ['CRITICAL', 'HIGH']
        ]
        
        if critical_high:
            print("\n" + self._colorize("🔴 CRITICAL & HIGH FINDINGS", "bold"))
            print("-" * 50)
            
            for i, finding in enumerate(critical_high, 1):
                self._print_finding(finding, i, compact=True)
        
        # All findings (if not too many)
        other_findings = [
            f for f in report_data['all_findings'] 
            if f['severity'] not in ['CRITICAL', 'HIGH']
        ]
        
        if other_findings:
            show_all = len(other_findings) <= 20  # Only show all if <= 20
            if show_all:
                print("\n" + self._colorize("📋 ALL FINDINGS", "bold"))
                print("-" * 50)
                
                for i, finding in enumerate(other_findings, 1):
                    self._print_finding(finding, i + len(critical_high), compact=True)
            else:
                print(f"\n{self._colorize('📋 Additional findings:', 'bold')} {len(other_findings)} more (MEDIUM, LOW, INFO)")
                print(f"  Use --format json/html for full details")
        
        # Files with most findings
        if report_data['findings_by_file']:
            print("\n" + self._colorize("📁 FILES WITH MOST FINDINGS", "bold"))
            print("-" * 50)
            
            file_counts = []
            for file_path, findings in report_data['findings_by_file'].items():
                # Count severities
                crit_high = len([f for f in findings if f['severity'] in ['CRITICAL', 'HIGH']])
                total = len(findings)
                file_counts.append((file_path, total, crit_high))
            
            # Sort by critical/high count, then total
            file_counts.sort(key=lambda x: (-x[2], -x[1]))
            
            for i, (file_path, total, crit_high) in enumerate(file_counts[:5]):
                if i == 0 and crit_high > 0:
                    color = "red"
                elif total > 0:
                    color = "yellow"
                else:
                    color = "white"
                
                # Truncate long paths
                display_path = file_path
                if len(display_path) > 50:
                    display_path = "..." + display_path[-47:]
                
                print(f"  {self._colorize(str(total).rjust(3), color)} findings ({crit_high} crit/high) in {display_path}")
        
        print("\n" + "=" * 70)
        print(self._colorize(" Scan complete! ", "bold"))
        print("=" * 70)
        
        # Recommendations
        if critical_high:
            print(f"\n{self._colorize('🚨 ACTION REQUIRED:', 'red')} Found {len(critical_high)} critical/high severity issues!")
            print("  Address these immediately to prevent security breaches.")
        elif report_data['summary']['total_findings'] > 0:
            print(f"\n{self._colorize('⚠️  REVIEW RECOMMENDED:', 'yellow')} Found {report_data['summary']['total_findings']} security issues.")
            print("  Review and address based on your security policy.")
        else:
            print(f"\n{self._colorize('✅ SUCCESS:', 'green')} No security issues found!")
            print("  Good job maintaining secure code practices.")
    
    def _print_finding(self, finding: Dict[str, Any], index: int, compact: bool = True):
        """Print a single finding to console."""
        severity_color = self._get_severity_color_name(finding['severity'])
        severity_icon = self._get_severity_icon(finding['severity'])
        
        if compact:
            # Compact format
            confidence = int(finding['confidence'] * 100)
            location = f"{finding['file_path']}:{finding['line_start']}"
            
            # Truncate long paths
            if len(location) > 40:
                location = "..." + location[-37:]
            
            print(f"{index:3}. {severity_icon} {self._colorize(finding['severity'][:1], severity_color)} "
                  f"{self._colorize(finding['title'][:50], 'bold')}")
            print(f"     {self._colorize(location, 'cyan')} "
                  f"[{finding['category']}] "
                  f"(Confidence: {confidence}%)")
        else:
            # Detailed format
            print(f"\n{self._colorize('─' * 60, 'gray')}")
            print(f"{self._colorize(f'#{index} {finding['title']}', 'bold')}")
            print(f"Severity:  {self._colorize(finding['severity'], severity_color)}")
            print(f"Category:  {finding['category']}")
            print(f"Confidence: {int(finding['confidence'] * 100)}%")
            print(f"Location:  {self._colorize(finding['file_path'] + ':' + str(finding['line_start']), 'cyan')}")
            print(f"Rule:      {finding.get('rule_id', 'N/A')}")
            print(f"\n{self._colorize('Description:', 'bold')}")
            print(f"  {finding['description']}")
            
            if finding.get('code_snippet'):
                print(f"\n{self._colorize('Code:', 'bold')}")
                lines = finding['code_snippet'].split('\n')
                for line in lines[:5]:  # First 5 lines
                    print(f"  {line}")
                if len(lines) > 5:
                    print(f"  ... ({len(lines) - 5} more lines)")
            
            print(f"\n{self._colorize('Recommendation:', 'bold')}")
            print(f"  {finding['recommendation']}")
    
    def _get_severity_color_name(self, severity: str) -> str:
        """Get color name for severity."""
        colors = {
            'CRITICAL': 'red',
            'HIGH': 'orange',
            'MEDIUM': 'yellow',
            'LOW': 'green',
            'INFO': 'blue',
        }
        return colors.get(severity, 'white')
    
    def _get_severity_icon(self, severity: str) -> str:
        """Get icon for severity."""
        icons = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢',
            'INFO': '🔵',
        }
        return icons.get(severity, '⚪')
