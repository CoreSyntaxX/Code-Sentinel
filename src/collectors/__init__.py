"""
File collectors module - for gathering files from various sources.
"""

from .base_collector import BaseCollector, CollectionResult
from .file_collector import FileCollector
from .web_crawler import WebCrawler
from .github_scraper import GitHubScraper
from .git_collector import GitCollector
from .orchestrator import CollectorOrchestrator, CollectorType

__all__ = [
    'BaseCollector',
    'CollectionResult',
    'FileCollector',
    'WebCrawler',
    'GitHubScraper',
    'GitCollector',
    'CollectorOrchestrator',
    'CollectorType',
]
