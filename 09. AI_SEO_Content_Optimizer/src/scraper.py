import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import urljoin, urlparse
import json
from .utils import load_from_cache, save_to_cache

logger = logging.getLogger(__name__)

class ContentScraper:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch the content of a URL."""
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None

    def extract_meta_tags(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta tags from the page."""
        meta_tags = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            meta_tags['title'] = title_tag.text.strip()
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            meta_tags['description'] = meta_desc.get('content', '').strip()
        
        # Other meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            if name:
                meta_tags[name] = meta.get('content', '').strip()
        
        return meta_tags

    def extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract headings from the page."""
        headings = {}
        for level in range(1, 4):
            heading_tags = soup.find_all(f'h{level}')
            headings[f'h{level}'] = [h.text.strip() for h in heading_tags]
        return headings

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> Tuple[List[str], List[str]]:
        """Extract internal and external links from the page."""
        internal_links = []
        external_links = []
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Skip javascript: and mailto: links
            if href.startswith(('javascript:', 'mailto:')):
                continue
            
            # Skip anchor links
            if href.startswith('#'):
                continue
            
            try:
                parsed_url = urlparse(full_url)
                if parsed_url.netloc == base_domain:
                    internal_links.append(full_url)
                else:
                    external_links.append(full_url)
            except Exception as e:
                logger.error(f"Error parsing URL {href}: {e}")
        
        return list(set(internal_links)), list(set(external_links))

    def extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract structured data from the page."""
        structured_data = []
        
        # Look for JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error parsing JSON-LD: {e}")
        
        return structured_data

    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content of the page."""
        # Try to find the main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=['content', 'main', 'article'])
        
        if main_content:
            # Remove unwanted elements
            for element in main_content.find_all(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            return main_content.get_text(separator=' ', strip=True)
        
        # Fallback: get all text from body
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)
        
        return ''

    def analyze_url(self, url: str) -> Optional[Dict]:
        """Analyze a URL and extract all relevant content."""
        # Check cache first
        cached_data = load_from_cache(url)
        if cached_data:
            return cached_data
        
        # Fetch the page
        html_content = self.fetch_url(url)
        if not html_content:
            return None
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract all content
            content_data = {
                'meta_tags': self.extract_meta_tags(soup),
                'headings': self.extract_headings(soup),
                'main_content': self.extract_main_content(soup),
                'structured_data': self.extract_structured_data(soup)
            }
            
            # Extract links
            internal_links, external_links = self.extract_links(soup, url)
            content_data['internal_links'] = internal_links
            content_data['external_links'] = external_links
            
            # Save to cache
            save_to_cache(content_data, url)
            
            return content_data
            
        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {e}")
            return None 