"""
HTML reporter - visual, interactive report.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import logging
import json
from datetime import datetime

from models.scan_context import ScanContext
from models.finding import Finding, Severity
from reporting.base_reporter import BaseReporter


logger = logging.getLogger(__name__)


class HTMLReporter(BaseReporter):
    """
    HTML reporter for visual, interactive reports.
    Includes charts, filters, and detailed views.
    """
    
    def __init__(self):
        super().__init__()
        self.output_dir = Path("./reports")
    
    def get_name(self) -> str:
        return "HTMLReporter"
    
    def get_extension(self) -> str:
        return "html"
    
    def generate_report(self, context: ScanContext, output_path: Optional[Path] = None) -> Path:
        """
        Generate HTML report with interactive features.
        """
        logger.info("Generating HTML report...")
        
        # Prepare data
        report_data = self._prepare_report_data(context)
        
        # Determine output path
        output_file = self._ensure_output_dir(output_path)
        
        # Generate HTML
        html_content = self._generate_html_content(report_data)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML report saved to: {output_file}")
            
            # Also save data JSON for the HTML to use
            json_file = output_file.with_suffix('.data.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            raise
    
    def _generate_html_content(self, report_data: Dict[str, Any]) -> str:
        """Generate full HTML content."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Scan Report - {report_data['metadata']['generated_at'][:10]}</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        :root {{
            --critical-color: #dc3545;
            --high-color: #fd7e14;
            --medium-color: #ffc107;
            --low-color: #28a745;
            --info-color: #17a2b8;
        }}
        
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        .severity-badge {{
            padding: 0.25em 0.6em;
            border-radius: 0.25rem;
            font-weight: 600;
            font-size: 0.85em;
        }}
        
        .severity-critical {{ background-color: var(--critical-color); color: white; }}
        .severity-high {{ background-color: var(--high-color); color: white; }}
        .severity-medium {{ background-color: var(--medium-color); color: #212529; }}
        .severity-low {{ background-color: var(--low-color); color: white; }}
        .severity-info {{ background-color: var(--info-color); color: white; }}
        
        .risk-score {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0;
        }}
        
        .risk-low {{ color: var(--low-color); }}
        .risk-medium {{ color: var(--medium-color); }}
        .risk-high {{ color: var(--high-color); }}
        .risk-critical {{ color: var(--critical-color); }}
        
        .finding-card {{
            transition: all 0.2s ease;
            border-left: 4px solid;
        }}
        
        .finding-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .finding-critical {{ border-left-color: var(--critical-color); }}
        .finding-high {{ border-left-color: var(--high-color); }}
        .finding-medium {{ border-left-color: var(--medium-color); }}
        .finding-low {{ border-left-color: var(--low-color); }}
        .finding-info {{ border-left-color: var(--info-color); }}
        
        .code-snippet {{
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 200px;
            overflow-y: auto;
        }}
        
        .line-number {{
            color: #999;
            margin-right: 10px;
            user-select: none;
        }}
        
        .stat-card {{
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
            margin-bottom: 1rem;
        }}
        
        .nav-tabs .nav-link.active {{
            font-weight: 600;
        }}
        
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
    <div class="container-fluid px-0">
        <!-- Header -->
        <nav class="navbar navbar-dark bg-dark mb-4">
            <div class="container">
                <span class="navbar-brand mb-0 h1">
                    <i class="fas fa-shield-alt me-2"></i>Security Scan Report
                </span>
                <span class="text-light">
                    Generated: {report_data['metadata']['generated_at'].replace('T', ' ')[:19]}
                </span>
            </div>
        </nav>
        
        <div class="container">
            <!-- Summary Cards -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="stat-card bg-white">
                        <h6 class="text-muted mb-2">Risk Score</h6>
                        <div class="risk-score {self._get_risk_class(report_data['metadata']['risk_score'])}">
                            {report_data['metadata']['risk_score']:.1f}
                        </div>
                        <small class="text-muted">0-100 (higher is worse)</small>
                    </div>
                </div>
                
                <div class="col-md-9">
                    <div class="row">
                        <div class="col-md-2 col-6">
                            <div class="stat-card bg-white text-center">
                                <div class="text-danger fw-bold fs-4">{report_data['summary']['critical_count']}</div>
                                <div class="text-muted small">Critical</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-6">
                            <div class="stat-card bg-white text-center">
                                <div class="text-warning fw-bold fs-4">{report_data['summary']['high_count']}</div>
                                <div class="text-muted small">High</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-6">
                            <div class="stat-card bg-white text-center">
                                <div class="text-warning fw-bold fs-4" style="color: var(--medium-color) !important;">{report_data['summary']['medium_count']}</div>
                                <div class="text-muted small">Medium</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-6">
                            <div class="stat-card bg-white text-center">
                                <div class="text-success fw-bold fs-4">{report_data['summary']['low_count']}</div>
                                <div class="text-muted small">Low</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-6">
                            <div class="stat-card bg-white text-center">
                                <div class="text-info fw-bold fs-4">{report_data['summary']['info_count']}</div>
                                <div class="text-muted small">Info</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-6">
                            <div class="stat-card bg-white text-center">
                                <div class="fw-bold fs-4">{report_data['summary']['total_findings']}</div>
                                <div class="text-muted small">Total</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Charts -->
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <i class="fas fa-chart-pie me-2"></i>Findings by Severity
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="severityChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <i class="fas fa-chart-bar me-2"></i>Findings by Category
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="categoryChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Scan Info -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <i class="fas fa-info-circle me-2"></i>Scan Information
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-3">
                                    <strong>Target:</strong><br>
                                    <code>{report_data['metadata']['scan_target']}</code>
                                </div>
                                <div class="col-md-3">
                                    <strong>Mode:</strong><br>
                                    {report_data['metadata']['scan_mode'].upper()}
                                </div>
                                <div class="col-md-3">
                                    <strong>Duration:</strong><br>
                                    {self._format_duration(report_data['metadata']['duration_seconds'])}
                                </div>
                                <div class="col-md-3">
                                    <strong>Files Scanned:</strong><br>
                                    {report_data['summary']['total_files_scanned']}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Findings Navigation -->
            <div class="row mb-4">
                <div class="col-12">
                    <ul class="nav nav-tabs" id="findingsTab" role="tablist">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active" id="all-tab" data-bs-toggle="tab" data-bs-target="#all" type="button" role="tab">
                                All Findings ({report_data['summary']['total_findings']})
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="critical-tab" data-bs-toggle="tab" data-bs-target="#critical" type="button" role="tab">
                                Critical ({report_data['summary']['critical_count']})
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="high-tab" data-bs-toggle="tab" data-bs-target="#high" type="button" role="tab">
                                High ({report_data['summary']['high_count']})
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="byfile-tab" data-bs-toggle="tab" data-bs-target="#byfile" type="button" role="tab">
                                By File ({report_data['summary']['files_with_findings']})
                            </button>
                        </li>
                    </ul>
                    
                    <div class="tab-content bg-white p-3 border border-top-0 rounded-bottom" id="findingsTabContent">
                        <!-- All Findings Tab -->
                        <div class="tab-pane fade show active" id="all" role="tabpanel">
                            {self._generate_findings_list(report_data['all_findings'])}
                        </div>
                        
                        <!-- Critical Findings Tab -->
                        <div class="tab-pane fade" id="critical" role="tabpanel">
                            {self._generate_findings_list(
                                [f for f in report_data['all_findings'] if f['severity'] == 'CRITICAL']
                            )}
                        </div>
                        
                        <!-- High Findings Tab -->
                        <div class="tab-pane fade" id="high" role="tabpanel">
                            {self._generate_findings_list(
                                [f for f in report_data['all_findings'] if f['severity'] == 'HIGH']
                            )}
                        </div>
                        
                        <!-- By File Tab -->
                        <div class="tab-pane fade" id="byfile" role="tabpanel">
                            {self._generate_files_view(report_data['findings_by_file'])}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Footer -->
            <footer class="text-center text-muted my-4 py-3 border-top">
                <p class="mb-1">
                    Generated by Security Scanner v{report_data['metadata']['tool_version']} • 
                    {report_data['metadata']['generated_at'].replace('T', ' ')[:19]}
                </p>
                <p class="small">
                    <i class="fas fa-exclamation-triangle text-warning me-1"></i>
                    This report contains sensitive security information. Handle with care.
                </p>
            </footer>
        </div>
    </div>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Initialize charts when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            {self._generate_charts_js(report_data)}
        }});
        
        // Toggle code snippets
        function toggleCodeSnippet(id) {{
            const snippet = document.getElementById('snippet-' + id);
            if (snippet.style.display === 'none') {{
                snippet.style.display = 'block';
            }} else {{
                snippet.style.display = 'none';
            }}
        }}
        
        // Filter findings
        function filterFindings(severity) {{
            const findings = document.querySelectorAll('.finding-card');
            findings.forEach(card => {{
                if (severity === 'all' || card.classList.contains('finding-' + severity.toLowerCase())) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    
    def _get_risk_class(self, risk_score: float) -> str:
        """Get CSS class for risk score."""
        if risk_score >= 75:
            return "risk-critical"
        elif risk_score >= 50:
            return "risk-high"
        elif risk_score >= 25:
            return "risk-medium"
        else:
            return "risk-low"
    
    def _generate_findings_list(self, findings: List[Dict[str, Any]]) -> str:
        """Generate HTML for findings list."""
        if not findings:
            return '<div class="alert alert-info">No findings in this category.</div>'
        
        html_parts = []
        for i, finding in enumerate(findings):
            html_parts.append(self._generate_finding_card(finding, i))
        
        return '\n'.join(html_parts)
    
    def _generate_finding_card(self, finding: Dict[str, Any], index: int) -> str:
        """Generate HTML for a single finding card."""
        severity_class = f"finding-{finding['severity'].lower()}"
        severity_badge_class = f"severity-{finding['severity'].lower()}"
        
        # Format confidence
        confidence_percent = int(finding['confidence'] * 100)
        confidence_color = "success" if confidence_percent >= 80 else "warning" if confidence_percent >= 50 else "danger"
        
        # Format code snippet if available
        code_snippet_html = ""
        if finding.get('code_snippet'):
            lines = finding['code_snippet'].split('\n')
            numbered_lines = []
            for j, line in enumerate(lines, 1):
                if j > 10:  # Limit to 10 lines
                    numbered_lines.append('<div class="line-number">...</div>')
                    break
                numbered_lines.append(f'<div><span class="line-number">{j}</span>{self._escape_html(line)}</div>')
            code_snippet_html = f"""
            <div class="mt-3">
                <button class="btn btn-sm btn-outline-secondary" onclick="toggleCodeSnippet({index})">
                    <i class="fas fa-code me-1"></i>Toggle Code Snippet
                </button>
                <div id="snippet-{index}" class="code-snippet mt-2" style="display: none;">
                    {' '.join(numbered_lines)}
                </div>
            </div>
            """
        
        # Format context if available
        context_html = ""
        if finding.get('context_before') or finding.get('context_after'):
            context_parts = []
            if finding.get('context_before'):
                context_parts.append(f"<strong>Before:</strong><br><pre>{self._escape_html(finding['context_before'])}</pre>")
            if finding.get('context_after'):
                context_parts.append(f"<strong>After:</strong><br><pre>{self._escape_html(finding['context_after'])}</pre>")
            context_html = f'<div class="mt-2">{ "<hr>".join(context_parts) }</div>'
        
        return f"""
        <div class="card finding-card {severity_class} mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title mb-1">{self._escape_html(finding['title'])}</h5>
                        <div class="mb-2">
                            <span class="severity-badge {severity_badge_class} me-2">{finding['severity']}</span>
                            <span class="badge bg-secondary me-2">{finding['category']}</span>
                            <span class="badge bg-{confidence_color}">Confidence: {confidence_percent}%</span>
                        </div>
                    </div>
                    <small class="text-muted">#{finding['id'][:8]}</small>
                </div>
                
                <p class="card-text">{self._escape_html(finding['description'])}</p>
                
                <div class="mb-2">
                    <strong>Location:</strong> {self._escape_html(finding['file_path'])}:{finding['line_start']}
                    {f' to {finding["line_end"]}' if finding.get('line_end') and finding['line_end'] != finding['line_start'] else ''}
                </div>
                
                <div class="mb-2">
                    <strong>Rule:</strong> <code>{finding.get('rule_id', 'N/A')}</code>
                    <span class="text-muted ms-2">Detected by: {finding.get('detector_name', 'Unknown')}</span>
                </div>
                
                {code_snippet_html}
                {context_html}
                
                <div class="mt-3">
                    <div class="alert alert-success">
                        <strong><i class="fas fa-lightbulb me-1"></i>Recommendation:</strong><br>
                        {self._escape_html(finding['recommendation'])}
                    </div>
                </div>
                
                {f'<div class="mt-2"><small class="text-muted"><i class="fas fa-tags me-1"></i>Tags: {", ".join(finding.get("tags", []))}</small></div>' if finding.get('tags') else ''}
            </div>
        </div>
        """
    
    def _generate_files_view(self, findings_by_file: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate HTML for files view."""
        if not findings_by_file:
            return '<div class="alert alert-info">No files with findings.</div>'
        
        html_parts = []
        for file_path, findings in findings_by_file.items():
            # Count severities
            severity_counts = {}
            for finding in findings:
                severity = finding['severity']
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Generate severity badges
            severity_badges = []
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    severity_badges.append(f'<span class="badge bg-{severity.lower()} me-1">{severity}: {count}</span>')
            
            html_parts.append(f"""
            <div class="card mb-3">
                <div class="card-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <i class="fas fa-file-code me-2"></i>
                            <code>{self._escape_html(file_path)}</code>
                        </div>
                        <div>
                            {''.join(severity_badges)}
                            <span class="badge bg-secondary">{len(findings)} total</span>
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    {self._generate_findings_list(findings)}
                </div>
            </div>
            """)
        
        return '\n'.join(html_parts)
    
    def _generate_charts_js(self, report_data: Dict[str, Any]) -> str:
        """Generate JavaScript for charts."""
        # Severity chart data
        severity_counts = report_data['summary']
        severity_data = {
            'CRITICAL': severity_counts['critical_count'],
            'HIGH': severity_counts['high_count'],
            'MEDIUM': severity_counts['medium_count'],
            'LOW': severity_counts['low_count'],
            'INFO': severity_counts['info_count'],
        }
        
        # Category chart data (top 10)
        category_counts = {}
        for finding in report_data['all_findings']:
            category = finding['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sort categories by count
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return f"""
        // Severity Chart
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        const severityChart = new Chart(severityCtx, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(list(severity_data.keys()))},
                datasets: [{{
                    data: {json.dumps(list(severity_data.values()))},
                    backgroundColor: [
                        '#dc3545',  // Critical
                        '#fd7e14',  // High
                        '#ffc107',  // Medium
                        '#28a745',  // Low
                        '#17a2b8',  // Info
                    ],
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                let label = context.label || '';
                                if (label) {{
                                    label += ': ';
                                }}
                                label += context.raw + ' findings';
                                return label;
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        // Category Chart
        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
        const categoryChart = new Chart(categoryCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps([c[0] for c in sorted_categories])},
                datasets: [{{
                    label: 'Findings',
                    data: {json.dumps([c[1] for c in sorted_categories])},
                    backgroundColor: '#6f42c1',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }}
            }}
        }});
        """
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
