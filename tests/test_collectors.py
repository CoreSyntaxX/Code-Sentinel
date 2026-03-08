"""
Tests for collectors module.
"""

import unittest
import tempfile
from pathlib import Path
from src.collectors.file_collector import FileCollector
from src.collectors.orchestrator import CollectorOrchestrator


class TestFileCollector(unittest.TestCase):
    """Test FileCollector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test files
        self.js_file = self.temp_path / "test.js"
        self.js_file.write_text("console.log('test');")
        
        self.py_file = self.temp_path / "test.py"
        self.py_file.write_text("print('test')")
        
        self.txt_file = self.temp_path / "readme.txt"
        self.txt_file.write_text("readme content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_collect_with_valid_extensions(self):
        """Test collecting with valid extensions."""
        output_dir = self.temp_path / "output"
        
        collector = FileCollector(
            source_path=self.temp_path,
            output_dir=output_dir,
            extensions={'.js', '.py'},
            recursive=False,
        )
        
        result = collector.collect()
        
        self.assertEqual(result.total_files, 2)
        self.assertIn('.js', result.file_types)
        self.assertIn('.py', result.file_types)
    
    def test_organize_by_extension(self):
        """Test organizing files by extension."""
        output_dir = self.temp_path / "output"
        
        collector = FileCollector(
            source_path=self.temp_path,
            output_dir=output_dir,
            extensions={'.js', '.py'},
        )
        
        result = collector.collect()
        
        # Check that files are organized
        self.assertTrue((output_dir / 'javascript').exists())
        self.assertTrue((output_dir / 'python').exists())


class TestCollectorOrchestrator(unittest.TestCase):
    """Test CollectorOrchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test directory structure
        self.source_dir = self.temp_path / "source"
        self.source_dir.mkdir()
        
        self.js_file = self.source_dir / "app.js"
        self.js_file.write_text("// JavaScript code")
        
        self.html_file = self.source_dir / "index.html"
        self.html_file.write_text("<html></html>")
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_orchestrator_collect(self):
        """Test orchestrator collection."""
        orchestrator = CollectorOrchestrator(
            output_base_dir=self.temp_path / "collected"
        )
        
        result = orchestrator.collect_from_local_path(
            source_path=self.source_dir,
        )
        
        self.assertGreater(result.total_files, 0)
    
    def test_orchestrator_summary(self):
        """Test orchestrator summary generation."""
        orchestrator = CollectorOrchestrator(
            output_base_dir=self.temp_path / "collected"
        )
        
        orchestrator.collect_from_local_path(
            source_path=self.source_dir,
        )
        
        summary = orchestrator.get_results_summary()
        
        self.assertEqual(summary['total_sources'], 1)
        self.assertGreater(summary['total_files_collected'], 0)


if __name__ == '__main__':
    unittest.main()
