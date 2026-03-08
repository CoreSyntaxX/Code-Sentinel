"""
Web crawler collector - gathers files from websites via URL spidering.
"""

from pathlib import Path
from typing import List, Optional, Set, Dict
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from http.client import IncompleteRead
import logging
import mimetypes

from .base_collector import BaseCollector, CollectionResult


logger = logging.getLogger(__name__)


class WebCrawler(BaseCollector):
    """Crawl websites and collect source files."""
    
    # MIME types that map to source code
    SOURCE_MIME_TYPES = {
        'text/javascript': '.js',
        'application/javascript': '.js',
        'text/typescript': '.ts',
        'text/plain': '.txt',
        'text/html': '.html',
        'text/css': '.css',
        'application/json': '.json',
        'application/xml': '.xml',
        'text/xml': '.xml',
        'text/x-python': '.py',
        'application/x-python': '.py',
        'text/x-php': '.php',
        'application/x-php': '.php',
    }
    
    def __init__(
        self,
        start_url: str,
        output_dir: Path,
        extensions: Optional[Set[str]] = None,
        max_depth: int = 3,
        max_pages: int = 100,
        ignore_patterns: Optional[List[str]] = None,
        user_agent: Optional[str] = None,
        timeout: int = 10,
    ):
        """
        Initialize web crawler.
        
        Args:
            start_url: Starting URL to crawl
            output_dir: Directory to organize collected files
            extensions: File extensions to collect
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            ignore_patterns: URL patterns to ignore
            user_agent: User agent string for requests
            timeout: Request timeout in seconds
        """
        super().__init__(
            output_dir=output_dir,
            extensions=extensions,
            max_depth=max_depth,
            ignore_patterns=ignore_patterns,
        )
        
        self.start_url = start_url
        self.max_pages = max_pages
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.timeout = timeout
        
        # Parse start URL
        self.base_domain = urlparse(start_url).netloc
        
        logger.info(f"WebCrawler initialized with start URL: {start_url}")
    
    def collect(self) -> CollectionResult:
        """
        Crawl the website and collect files.
        
        Returns:
            CollectionResult with collected files
        """
        logger.info(f"Starting web crawl from {self.start_url}")
        
        files = self._crawl()
        
        logger.info(f"Collected {len(files)} files")
        
        return self.organize_files(
            files=files,
            source_description=self.start_url,
            organize_by='extension'
        )
    
    def _crawl(self) -> List[Path]:
        """Crawl the website and collect files."""
        visited = set()
        to_visit = [(self.start_url, 0)]  # (url, depth)
        files = []
        
        while to_visit and len(visited) < self.max_pages:
            current_url, depth = to_visit.pop(0)
            
            # Check depth
            if depth > self.max_depth:
                continue
            
            # Skip if already visited
            if current_url in visited:
                continue
            
            visited.add(current_url)
            
            # Check domain
            if not self._is_same_domain(current_url):
                continue
            
            # Skip ignored patterns
            if self.should_ignore(Path(current_url)):
                continue
            
            try:
                logger.debug(f"Crawling (depth {depth}): {current_url}")
                content, content_type = self._fetch_url(current_url)
                
                if content:
                    # Try to save as file
                    file_path = self._save_content(current_url, content, content_type)
                    if file_path:
                        files.append(file_path)
                    
                    # Extract links for next crawl (if depth allows)
                    if depth < self.max_depth:
                        links = self._extract_links(content, current_url)
                        for link in links:
                            if link not in visited:
                                to_visit.append((link, depth + 1))
                
            except Exception as e:
                logger.warning(f"Error crawling {current_url}: {e}")
        
        return files
    
    def _fetch_url(self, url: str) -> tuple[Optional[bytes], Optional[str]]:
        """Fetch content from URL and return (content, content_type)."""
        try:
            req = Request(url, headers={'User-Agent': self.user_agent})
            with urlopen(req, timeout=self.timeout) as response:
                content_type = None
                try:
                    content_type = response.headers.get_content_type()
                except Exception:
                    content_type = response.headers.get('Content-Type')
                    if content_type:
                        content_type = content_type.split(';')[0].strip()
                try:
                    return response.read(), content_type
                except IncompleteRead as e:
                    logger.warning(f"Incomplete read from {url}: using partial content")
                    return e.partial, content_type
        except HTTPError as e:
            logger.warning(f"HTTP error fetching {url}: {e.code} {e.reason}")
        except URLError as e:
            logger.warning(f"URL error fetching {url}: {e.reason}")
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
        return None, None
    
    def _save_content(self, url: str, content: bytes, content_type: Optional[str]) -> Optional[Path]:
        """Save fetched content to file."""
        try:
            # Determine file extension
            parsed = urlparse(url)
            path = parsed.path
            
            ext = Path(path).suffix.lower() if path else ''
            if not ext:
                # Try to infer from content type
                if content_type and content_type in self.SOURCE_MIME_TYPES:
                    ext = self.SOURCE_MIME_TYPES[content_type]
                else:
                    ext = '.html'
            
            # Check if valid extension (always allow HTML/JS when content-type indicates)
            if ext.lower() not in self.extensions:
                if content_type in ("text/html", "text/javascript", "application/javascript"):
                    ext = ".html" if "html" in content_type else ".js"
                else:
                    return None
            
            # Generate filename
            filename = Path(path).name or f"index{ext}"
            file_path = self.output_dir / filename
            
            # Handle conflicts
            counter = 1
            while file_path.exists():
                stem = file_path.stem
                file_path = self.output_dir / f"{stem}_{counter}{ext}"
                counter += 1
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.debug(f"Saved: {url} -> {file_path}")
            return file_path
            
        except Exception as e:
            logger.debug(f"Error saving content from {url}: {e}")
            return None
    
    def _extract_links(self, content: bytes, base_url: str) -> List[str]:
        """Extract links from HTML content."""
        links = set()
        
        try:
            # Simple regex-based link extraction (no external HTML parser dependency)
            import re
            
            text = content.decode('utf-8', errors='ignore')
            
            # Find href, src, and action attributes
            patterns = [
                r'href=["\']([^"\']+)["\']',
                r'src=["\']([^"\']+)["\']',
                r'action=["\']([^"\']+)["\']',
            ]
            # Also catch bare .php references in content
            patterns += [
                r'([A-Za-z0-9_./-]+\.php(?:\?[^\s"\'<>]*)?)',
            ]
            matches = []
            for pattern in patterns:
                matches.extend(re.findall(pattern, text))
            
            for match in matches:
                try:
                    if match.startswith(('mailto:', 'javascript:', '#')):
                        continue
                    absolute_url = urljoin(base_url, match)
                    links.add(absolute_url)
                except Exception:
                    pass
            
        except Exception as e:
            logger.debug(f"Error extracting links: {e}")
        
        return list(links)
    
    def _is_same_domain(self, url: str) -> bool:
        """Check if URL is from the same domain."""
        parsed = urlparse(url)
        return parsed.netloc == self.base_domain
