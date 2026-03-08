"""
Report builder - orchestrates multiple reporters.
"""

from typing import List, Dict, Any, Optional, Type
from pathlib import Path
import logging

from models.scan_context import ScanContext
from reporting.base_reporter import BaseReporter
from reporting.json_reporter import JSONReporter
from reporting.html_reporter import HTMLReporter
from reporting.markdown_reporter import MarkdownReporter
from reporting.sarif_reporter import SARIFReporter
from reporting.console_reporter import ConsoleReporter


logger = logging.getLogger(__name__)


class ReportBuilder:
    """
    Builds reports using multiple reporters.
    Supports multiple output formats in one run.
    """
    
    def __init__(self, context: ScanContext):
        self.context = context
        self.reporters: Dict[str, BaseReporter] = {}
        self._register_default_reporters()
    
    def _register_default_reporters(self):
        """Register all available reporters."""
        self.register_reporter(JSONReporter())
        self.register_reporter(HTMLReporter())
        self.register_reporter(MarkdownReporter())
        self.register_reporter(SARIFReporter())
        self.register_reporter(ConsoleReporter())
    
    def register_reporter(self, reporter: BaseReporter):
        """Register a reporter."""
        self.reporters[reporter.get_name()] = reporter
        logger.debug(f"Registered reporter: {reporter.get_name()}")
    
    def get_reporter(self, name: str) -> Optional[BaseReporter]:
        """Get a reporter by name."""
        return self.reporters.get(name)
    
    def list_reporters(self) -> List[str]:
        """List all available reporters."""
        return list(self.reporters.keys())
    
    def generate_reports(self, formats: Optional[List[str]] = None, 
                         output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Generate reports in specified formats.
        
        Args:
            formats: List of format names (json, html, markdown, sarif, console)
                    If None, uses format from context settings
            output_dir: Custom output directory
            
        Returns:
            Dictionary mapping format to output path
        """
        if formats is None:
            formats = [self.context.settings.output_format]
        
        results = {}
        
        for format_name in formats:
            reporter = self._get_reporter_for_format(format_name)
            if not reporter:
                logger.warning(f"No reporter found for format: {format_name}")
                continue
            
            try:
                # Set output directory if specified
                if output_dir:
                    reporter.output_dir = output_dir
                elif self.context.settings.output_dir:
                    reporter.output_dir = self.context.settings.output_dir
                
                # Generate report
                output_path = reporter.generate_report(self.context)
                results[format_name] = output_path
                
                logger.info(f"Generated {format_name} report: {output_path}")
                
            except Exception as e:
                logger.error(f"Failed to generate {format_name} report: {e}")
        
        return results
    
    def _get_reporter_for_format(self, format_name: str) -> Optional[BaseReporter]:
        """Get reporter instance for format name."""
        format_map = {
            'json': 'JSONReporter',
            'html': 'HTMLReporter',
            'markdown': 'MarkdownReporter',
            'sarif': 'SARIFReporter',
            'console': 'ConsoleReporter',
        }
        
        reporter_name = format_map.get(format_name.lower())
        if reporter_name:
            return self.reporters.get(reporter_name)
        
        # Try direct lookup
        return self.reporters.get(format_name)
    
    def generate_all_reports(self, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """Generate all available reports."""
        results = {}
        
        for reporter_name, reporter in self.reporters.items():
            # Skip console for file output (it prints to terminal)
            if reporter_name == 'ConsoleReporter':
                continue
            
            try:
                if output_dir:
                    reporter.output_dir = output_dir
                
                output_path = reporter.generate_report(self.context)
                results[reporter_name] = output_path
                
            except Exception as e:
                logger.error(f"Failed to generate {reporter_name} report: {e}")
        
        # Always print console output
        console_reporter = self.reporters.get('ConsoleReporter')
        if console_reporter:
            console_reporter.generate_report(self.context)
        
        return results
    
    def generate_summary_statistics(self) -> Dict[str, Any]:
        """Generate summary statistics for quick overview."""
        report_data = self._prepare_summary_data()
        
        return {
            'risk_score': report_data['metadata']['risk_score'],
            'total_findings': report_data['summary']['total_findings'],
            'critical_count': report_data['summary']['critical_count'],
            'high_count': report_data['summary']['high_count'],
            'files_scanned': report_data['summary']['total_files_scanned'],
            'duration': report_data['metadata']['duration_seconds'],
            'generated_at': report_data['metadata']['generated_at'],
        }
    
    def _prepare_summary_data(self) -> Dict[str, Any]:
        """Prepare summary data using base reporter methods."""
        # Use JSON reporter's prepare method (it has all we need)
        temp_reporter = JSONReporter()
        return temp_reporter._prepare_report_data(self.context)
