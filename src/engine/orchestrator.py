"""
Main orchestrator that coordinates the entire scanning process.
Includes file collection, processing, analysis, and reporting.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
from dataclasses import dataclass, field
import sys

from models.scan_context import ScanContext, ScanSettings
from models.finding import Finding
from engine.pipeline import ProcessingPipeline, PipelineStage
from engine.rule_engine import RuleEngine
from engine.component_registry import ComponentRegistry
from reporting.report_builder import ReportBuilder
from collectors.orchestrator import CollectorOrchestrator, CollectorType


logger = logging.getLogger(__name__)


class ScanOrchestrator:
    """
    Main orchestrator that coordinates collectors, processors, analyzers, and detectors.
    Provides unified interface for file collection and security scanning.
    """
    
    def __init__(self, settings: ScanSettings):
        self.settings = settings
        self.context = ScanContext(settings=settings)
        
        # Initialize components
        self.registry = ComponentRegistry()
        self.pipeline = ProcessingPipeline(self.context)
        self.rule_engine = RuleEngine()
        
        # Initialize collectors
        self.collector_orchestrator = CollectorOrchestrator(
            output_base_dir=Path(self.settings.output_dir) / "temp_collections"
        )
        
        # Scan state
        self.is_running = False
        self.is_cancelled = False
        
    def initialize(self):
        """Initialize the orchestrator and load components."""
        logger.info("Initializing scan orchestrator")
        
        try:
            # Load rules
            self.rule_engine.load_rules_from_directory(
                Path(__file__).parent.parent / "config" / "rules"
            )
            
            # Register built-in components
            self._register_builtin_components()
            
            # Build the processing pipeline
            self._build_pipeline()
            
            logger.info("Orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    def _register_builtin_components(self):
        """Register built-in analyzers, detectors, and processors."""
        # This will be populated as we build components
        logger.debug("Registering built-in components")
        
        # Import here to avoid circular imports
        from analyzers.javascript.analyzer import JavaScriptAnalyzer
        from detectors.pattern_detector import PatternDetector
        from detectors.secrets_detector import SecretsDetector
        from detectors.jwt_detector import JWTDetector
        from detectors.entropy_detector import EntropyDetector
        from detectors.structural_detector import StructuralDetector
        from processors.normalizer import CodeNormalizer
        from processors.beautifier import JavaScriptBeautifier
        from processors.minifier import MinifiedCodeDetector
        from processors.tokenizer import CodeTokenizer
        from processors.deobfuscator import CodeDeobfuscator
        # from analyzers.php.analyzer import PHPAnalyzer
        # from analyzers.html.analyzer import HTMLAnalyzer
        
        # Register analyzers
        self.registry.register_analyzer(JavaScriptAnalyzer())
        # self.registry.register_analyzer(PHPAnalyzer())
        # self.registry.register_analyzer(HTMLAnalyzer())
        
        # Register detectors
        self.registry.register_detector(PatternDetector(self.rule_engine))
        self.registry.register_detector(SecretsDetector())
        self.registry.register_detector(JWTDetector())
        self.registry.register_detector(EntropyDetector())
        self.registry.register_detector(StructuralDetector())
        
        # Register processors
        self.registry.register_processor(MinifiedCodeDetector())
        self.registry.register_processor(JavaScriptBeautifier())
        self.registry.register_processor(CodeDeobfuscator())
        self.registry.register_processor(CodeNormalizer())
        self.registry.register_processor(CodeTokenizer())
    
    def _build_pipeline(self):
        """Build the processing pipeline based on settings."""
        logger.debug("Building processing pipeline")
        
        # Clear existing stages
        self.pipeline.stages.clear()
        
        # Stage 1: Pre-processing
        minified_detector = self.registry.get_processor("MinifiedCodeDetector")
        if minified_detector:
            self.pipeline.add_stage(PipelineStage(
                name="process_minified_detector",
                processor=minified_detector.process,
                description="Detect minified code for context stats"
            ))
        
        beautifier = self.registry.get_processor("JavaScriptBeautifier")
        if beautifier:
            self.pipeline.add_stage(PipelineStage(
                name="process_beautify_javascript",
                processor=beautifier.process,
                description="Beautify minified JavaScript for analysis"
            ))
        
        deobfuscator = self.registry.get_processor("CodeDeobfuscator")
        if deobfuscator:
            self.pipeline.add_stage(PipelineStage(
                name="process_deobfuscate",
                processor=deobfuscator.process,
                description="Deobfuscate common encoded patterns"
            ))
        
        normalizer = self.registry.get_processor("CodeNormalizer")
        if normalizer:
            self.pipeline.add_stage(PipelineStage(
                name="process_normalize",
                processor=normalizer.process,
                description="Normalize code formatting and comments"
            ))
        
        tokenizer = self.registry.get_processor("CodeTokenizer")
        if tokenizer:
            self.pipeline.add_stage(PipelineStage(
                name="process_tokenize",
                processor=tokenizer.process,
                description="Tokenize code for structural analysis"
            ))
        
        # Stage 2: Language-specific analysis
        # Add analyzers for all supported file types
        js_analyzer = self.registry.get_analyzer("JavaScriptAnalyzer")
        if js_analyzer:
            self.pipeline.add_stage(PipelineStage(
                name="analyze_javascript",
                processor=js_analyzer.analyze,
                description="Analyze JavaScript files for security issues"
            ))
        
        # Stage 3: Cross-language detectors
        pattern_detector = self.registry.get_detector("PatternDetector")
        if pattern_detector:
            self.pipeline.add_stage(PipelineStage(
                name="detect_patterns",
                processor=pattern_detector.detect,
                description="Detect common security patterns and secrets"
            ))
        
        if self.settings.enable_secret_detection:
            secrets_detector = self.registry.get_detector("SecretsDetector")
            if secrets_detector:
                self.pipeline.add_stage(PipelineStage(
                    name="detect_secrets",
                    processor=secrets_detector.detect,
                    description="Detect exposed secrets and API keys"
                ))
            
            jwt_detector = self.registry.get_detector("JWTDetector")
            if jwt_detector:
                self.pipeline.add_stage(PipelineStage(
                    name="detect_jwt",
                    processor=jwt_detector.detect,
                    description="Detect exposed JWT tokens and weak JWT configs"
                ))
            
            entropy_detector = self.registry.get_detector("EntropyDetector")
            if entropy_detector:
                self.pipeline.add_stage(PipelineStage(
                    name="detect_entropy",
                    processor=entropy_detector.detect,
                    description="Detect high-entropy strings that might be secrets"
                ))
        
        if self.settings.enable_info_disclosure_detection:
            structural_detector = self.registry.get_detector("StructuralDetector")
            if structural_detector:
                self.pipeline.add_stage(PipelineStage(
                    name="detect_structural",
                    processor=structural_detector.detect,
                    description="Detect structural security issues and info disclosure"
                ))
        
        logger.info(f"Pipeline built with {len(self.pipeline.stages)} stages")
    
    def run_scan(self, target: Optional[str] = None) -> ScanContext:
        """
        Run a complete security scan including collection and analysis.
        
        Args:
            target: Override target from settings
            
        Returns:
            ScanContext with findings and statistics
        """
        if self.is_running:
            raise RuntimeError("Scan is already running")
        
        self.is_running = True
        self.is_cancelled = False
        self.context.start_time = time.time()
        
        logger.info(f"Starting security scan: target={target or self.settings.target}")
        
        try:
            # Step 1: Initialize
            self.initialize()
            
            # Step 2: Collect files (using appropriate collector based on settings)
            files = self._collect_files_with_orchestrator(target)
            
            # Step 3: Process files through pipeline
            self._process_files(files)
            
            # Step 4: Generate report
            self._generate_report()
            
            # Step 5: Cleanup
            self._cleanup()
            
        except KeyboardInterrupt:
            logger.info("Scan interrupted by user")
            self.is_cancelled = True
        except Exception as e:
            logger.error(f"Scan failed with error: {e}")
            raise
        finally:
            self.is_running = False
            self.context.end_time = time.time()
        
        return self.context
    
    def _collect_files_with_orchestrator(self, target: Optional[str] = None) -> List[Path]:
        """
        Collect files using the appropriate collector based on target type.
        
        Args:
            target: Override target from settings
            
        Returns:
            List of collected file paths
        """
        logger.info("Collecting files using collector orchestrator...")
        
        scan_target = target or self.settings.target
        target_type = self.settings.target_type
        
        try:
            collection_result = None
            
            # Use appropriate collector based on target type
            if target_type == "github":
                logger.info(f"Collecting from GitHub: {scan_target}")
                collection_result = self.collector_orchestrator.collect_from_github(
                    repo_url=scan_target,
                    extensions=self.settings.include_extensions,
                    branch=getattr(self.settings, 'git_branch', 'main'),
                    access_token=getattr(self.settings, 'github_token', None),
                )
            
            elif target_type == "git":
                logger.info(f"Collecting from Git repository: {scan_target}")
                collection_result = self.collector_orchestrator.collect_from_git(
                    repo_path=Path(scan_target),
                    extensions=self.settings.include_extensions,
                    include_uncommitted=getattr(self.settings, 'include_uncommitted', False),
                )
            
            elif target_type == "web":
                logger.info(f"Collecting from website: {scan_target}")
                collection_result = self.collector_orchestrator.collect_from_web(
                    start_url=scan_target,
                    extensions=self.settings.include_extensions,
                    max_depth=getattr(self.settings, 'web_max_depth', 3),
                    max_pages=getattr(self.settings, 'web_max_pages', 100),
                )
            
            else:  # Default to local
                logger.info(f"Collecting from local filesystem: {scan_target}")
                collection_result = self.collector_orchestrator.collect_from_local_path(
                    source_path=Path(scan_target),
                    extensions=self.settings.include_extensions,
                    recursive=True,
                    ignore_patterns=getattr(self.settings, 'ignore_patterns', None),
                )
            
            if collection_result:
                # Store collection metadata
                self.context.collection_result = collection_result
                self.context.stats["collection"] = {
                    "source": collection_result.source,
                    "files_collected": collection_result.total_files,
                    "file_types": list(collection_result.file_types),
                    "total_size_mb": collection_result.total_size_bytes / 1024 / 1024,
                    "organized_dir": str(collection_result.organized_dir),
                    "errors": len(collection_result.errors),
                }
                
                logger.info(collection_result.summary())
                
                # Collect files from the organized directory
                files = self._collect_organized_files(collection_result.organized_dir)
                files = self._filter_files(files)
                self.context.files_collected = files
                self.context.stats["total_files"] = len(files)
                logger.info(f"Collected {len(files)} files from organized directory after filtering")
                
                return files
            else:
                logger.warning("Collection failed, falling back to direct file discovery")
                return self._collect_files_direct(scan_target)
                
        except Exception as e:
            logger.error(f"Error during collection: {e}")
            logger.info("Falling back to direct file discovery")
            return self._collect_files_direct(scan_target)
    
    def _collect_organized_files(self, organized_dir: Path) -> List[Path]:
        """Collect files from the organized directory."""
        files = []
        
        if not organized_dir.exists():
            logger.warning(f"Organized directory does not exist: {organized_dir}")
            return files
        
        # Collect all files from organized directory
        for file_path in organized_dir.rglob('*'):
            if file_path.is_file():
                files.append(file_path)
        
        return files
    
    def _collect_files_direct(self, target: Optional[str] = None) -> List[Path]:
        """
        Direct file collection fallback (legacy method).
        Used when target is a local path.
        """
        logger.info("Collecting files directly from filesystem...")
        
        scan_target = target or self.settings.target
        target_path = Path(scan_target)
        
        files = []
        
        # Directories to skip
        skip_dirs = {
            '.venv', 'venv', 'env', '.env',
            'node_modules', '.git', '.github',
            '__pycache__', '.pytest_cache', '.tox',
            '.idea', '.vscode', 'dist', 'build',
            '*.egg-info'
        }
        
        # For local directories, recursively collect files
        if target_path.is_dir():
            for file_path in target_path.rglob('*'):
                # Skip files in excluded directories
                if any(part in skip_dirs for part in file_path.parts):
                    continue
                if file_path.is_file():
                    files.append(file_path)
        elif target_path.is_file():
            files.append(target_path)
        else:
            logger.warning(f"Target path does not exist: {scan_target}")
        
        # Filter files by extension
        filtered_files = self._filter_files(files)
        
        logger.info(f"Collected {len(files)} files, {len(filtered_files)} after filtering")
        self.context.files_collected = filtered_files
        self.context.stats["total_files"] = len(filtered_files)
        
        return filtered_files
    
    
    def _filter_files(self, files: List[Path]) -> List[Path]:
        """Filter files based on settings."""
        filtered = []
        
        for file_path in files:
            # Check extension
            extension = file_path.suffix.lower()
            
            # Skip excluded extensions
            if any(file_path.name.endswith(ext) for ext in self.settings.exclude_extensions):
                continue
            
            # Check included extensions (if not empty)
            if self.settings.include_extensions:
                if extension not in self.settings.include_extensions:
                    continue
            
            # Check file size
            try:
                file_size = file_path.stat().st_size
                if file_size > self.settings.max_file_size_mb * 1024 * 1024:
                    logger.debug(f"Skipping {file_path}: file too large")
                    continue
            except OSError:
                continue  # Skip if we can't access file
            
            filtered.append(file_path)
        
        # Limit total files if specified
        if self.settings.max_total_files and len(filtered) > self.settings.max_total_files:
            logger.warning(f"Limiting files to {self.settings.max_total_files} (from {len(filtered)})")
            filtered = filtered[:self.settings.max_total_files]
        
        return filtered
    
    def _process_files(self, files: List[Path]):
        """Process files through the pipeline."""
        logger.info(f"Processing {len(files)} files...")
        
        if self.settings.max_workers > 1:
            findings = self.pipeline.process_files_parallel(files)
        else:
            findings = self.pipeline.process_files_sequential(files)
        
        logger.info(f"Processing complete. Found {len(findings)} issues")
    
    def _generate_report(self):
        """Generate scan report."""
        logger.info("Generating report...")
        report_builder = ReportBuilder(self.context)
        results = report_builder.generate_reports()
        self.context.stats["reports"] = {
            format_name: str(path) for format_name, path in results.items()
        }
    
    def _cleanup(self):
        """Cleanup resources after scan."""
        # Clear caches to free memory
        self.context.file_content_cache.clear()
        self.context.ast_cache.clear()
        
        logger.debug("Cleanup completed")
    
    def cancel_scan(self):
        """Cancel the ongoing scan."""
        if not self.is_running:
            return
        
        logger.info("Cancelling scan...")
        self.is_cancelled = True
        
        # Additional cancellation logic can be added here
        # (e.g., stop workers, close connections)
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current scan progress."""
        if not self.is_running:
            return {"status": "idle"}
        
        total_files = len(self.context.files_collected)
        processed_files = len(self.context.files_processed)
        
        if total_files == 0:
            progress = 0
        else:
            progress = (processed_files / total_files) * 100
        
        return {
            "status": "running",
            "progress": round(progress, 2),
            "processed_files": processed_files,
            "total_files": total_files,
            "findings": len(self.context.findings),
            "elapsed_time": time.time() - (self.context.start_time or time.time()),
        }
