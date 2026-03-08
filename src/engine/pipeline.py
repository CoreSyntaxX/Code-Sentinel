"""
Pipeline builder and executor.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from models.scan_context import ScanContext
from models.finding import Finding
from models.file_meta import FileMetadata
from engine.base import BaseAnalyzer, BaseProcessor, BaseDetector


logger = logging.getLogger(__name__)


@dataclass
class PipelineStage:
    """Represents a stage in the processing pipeline."""
    name: str
    processor: Callable
    description: str = ""
    enabled: bool = True
    timeout: Optional[int] = None


class ProcessingPipeline:
    """Orchestrates the processing of files through multiple stages."""
    
    def __init__(self, context: ScanContext):
        self.context = context
        self.stages: List[PipelineStage] = []
        
    def add_stage(self, stage: PipelineStage):
        """Add a stage to the pipeline."""
        self.stages.append(stage)
        
    def remove_stage(self, stage_name: str):
        """Remove a stage by name."""
        self.stages = [s for s in self.stages if s.name != stage_name]
        
    def get_stage(self, stage_name: str) -> Optional[PipelineStage]:
        """Get a stage by name."""
        for stage in self.stages:
            if stage.name == stage_name:
                return stage
        return None
    
    def process_file(self, file_path: Path) -> List[Finding]:
        """
        Process a single file through all pipeline stages.
        Returns list of findings.
        """
        findings = []
        self.context.current_file = file_path
        
        try:
            # Skip if file is too large
            file_size = file_path.stat().st_size
            max_size = self.context.settings.max_file_size_mb * 1024 * 1024
            if file_size > max_size:
                logger.warning(f"Skipping {file_path}: file too large ({file_size} bytes)")
                return findings
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Process through each stage
            processed_content = content
            for stage in self.stages:
                if not stage.enabled:
                    continue
                    
                try:
                    logger.debug(f"Processing {file_path} with stage: {stage.name}")
                    
                    if stage.name.startswith("analyze_"):
                        # Analysis stages return findings
                        # Check if the processor (analyzer) supports this file
                        if hasattr(stage.processor, '__self__') and hasattr(stage.processor.__self__, 'supports_file'):
                            if not stage.processor.__self__.supports_file(file_path):
                                logger.debug(f"Analyzer does not support {file_path}, skipping")
                                continue
                        
                        # Call the analyze method
                        stage_findings = stage.processor(
                            file_path, processed_content, self.context
                        )
                        findings.extend(stage_findings)
                    elif stage.name.startswith("detect_"):
                        # Detection stages return findings
                        stage_findings = stage.processor(
                            processed_content, file_path, self.context
                        )
                        findings.extend(stage_findings)
                    else:
                        # Processing stages transform content
                        processed_content = stage.processor(
                            processed_content, self.context
                        )
                        
                except Exception as e:
                    logger.error(f"Stage {stage.name} failed for {file_path}: {e}")
                    continue
                    continue
            
            # If this file came from a collector, overwrite with processed content
            if processed_content != content:
                collection_result = getattr(self.context, "collection_result", None)
                if collection_result and collection_result.organized_dir:
                    try:
                        organized_dir = Path(collection_result.organized_dir).resolve()
                        file_resolved = file_path.resolve()
                        if organized_dir in file_resolved.parents:
                            with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                                f.write(processed_content)
                            logger.debug(f"Overwrote collected file with processed content: {file_path}")
                    except Exception as e:
                        logger.debug(f"Failed to overwrite processed content for {file_path}: {e}")
                    
            # Update context statistics
            self.context.files_processed.append(file_path)
            self.context.stats["processed_files"] += 1
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            self.context.stats["skipped_files"] += 1
        finally:
            if hasattr(self.context, "current_file"):
                delattr(self.context, "current_file")
            
        return findings
    
    def process_files_parallel(self, file_paths: List[Path]) -> List[Finding]:
        """
        Process multiple files in parallel.
        Returns all findings.
        """
        all_findings = []
        max_workers = self.context.settings.max_workers
        
        logger.info(f"Processing {len(file_paths)} files with {max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(self.process_file, file_path): file_path
                for file_path in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    findings = future.result(timeout=self.context.settings.timeout_per_file_seconds)
                    all_findings.extend(findings)
                    
                    # Add findings to context
                    for finding in findings:
                        self.context.add_finding(finding)
                        
                except TimeoutError:
                    logger.error(f"Processing timeout for {file_path}")
                    self.context.stats["skipped_files"] += 1
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    self.context.stats["skipped_files"] += 1
        
        return all_findings
    
    def process_files_sequential(self, file_paths: List[Path]) -> List[Finding]:
        """
        Process files sequentially (for debugging or single-threaded mode).
        """
        all_findings = []
        
        for file_path in file_paths:
            try:
                findings = self.process_file(file_path)
                all_findings.extend(findings)
                
                # Add findings to context
                for finding in findings:
                    self.context.add_finding(finding)
                    
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.context.stats["skipped_files"] += 1
        
        return all_findings
