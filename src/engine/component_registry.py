"""
Registry for managing analyzers, detectors, and processors.
"""

from typing import Dict, List, Optional, Type
from dataclasses import dataclass, field
import logging

from engine.base import BaseAnalyzer, BaseDetector, BaseProcessor


logger = logging.getLogger(__name__)


class ComponentRegistry:
    """
    Registry for managing and accessing analysis components.
    """
    
    def __init__(self):
        self.analyzers: Dict[str, BaseAnalyzer] = {}
        self.detectors: Dict[str, BaseDetector] = {}
        self.processors: Dict[str, BaseProcessor] = {}
    
    # Analyzer methods
    def register_analyzer(self, analyzer: BaseAnalyzer):
        """Register an analyzer."""
        name = analyzer.get_name()
        if name in self.analyzers:
            logger.warning(f"Analyzer {name} already registered, overwriting")
        self.analyzers[name] = analyzer
        logger.debug(f"Registered analyzer: {name}")
    
    def get_analyzer(self, name: str) -> Optional[BaseAnalyzer]:
        """Get an analyzer by name."""
        return self.analyzers.get(name)
    
    def get_analyzers_for_extension(self, extension: str) -> List[BaseAnalyzer]:
        """Get analyzers that support a file extension."""
        supported = []
        for analyzer in self.analyzers.values():
            # This is a simplified check - real implementation would check file types
            if extension in ['.js', '.jsx', '.ts', '.tsx'] and 'javascript' in analyzer.get_name().lower():
                supported.append(analyzer)
            elif extension == '.php' and 'php' in analyzer.get_name().lower():
                supported.append(analyzer)
            elif extension in ['.html', '.htm'] and 'html' in analyzer.get_name().lower():
                supported.append(analyzer)
        return supported
    
    # Detector methods
    def register_detector(self, detector: BaseDetector):
        """Register a detector."""
        name = detector.get_name()
        if name in self.detectors:
            logger.warning(f"Detector {name} already registered, overwriting")
        self.detectors[name] = detector
        logger.debug(f"Registered detector: {name}")
    
    def get_detector(self, name: str) -> Optional[BaseDetector]:
        """Get a detector by name."""
        return self.detectors.get(name)
    
    # Processor methods
    def register_processor(self, processor: BaseProcessor):
        """Register a processor."""
        name = processor.get_name()
        if name in self.processors:
            logger.warning(f"Processor {name} already registered, overwriting")
        self.processors[name] = processor
        logger.debug(f"Registered processor: {name}")
    
    def get_processor(self, name: str) -> Optional[BaseProcessor]:
        """Get a processor by name."""
        return self.processors.get(name)
    
    def list_components(self) -> Dict[str, List[str]]:
        """List all registered components."""
        return {
            "analyzers": list(self.analyzers.keys()),
            "detectors": list(self.detectors.keys()),
            "processors": list(self.processors.keys()),
        }
