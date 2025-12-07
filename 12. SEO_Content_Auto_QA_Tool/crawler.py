"""
Crawler module for SEO Auto QA tool.
Handles page fetching, rendering, and initial SEO element extraction.
"""

import asyncio
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
import yaml
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SEOCrawler:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the SEO crawler with configuration."""
        self.config = self._load_config(config_path)
        self.browser: Optional[Browser] = None
        self.context = None

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    async def initialize(self):
        """Initialize the browser and context."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport=self.config['crawler']['viewport'],
            user_agent=self.config['crawler']['user_agent']
        )

    async def close(self):
        """Close browser and cleanup resources."""
        if self.browser:
            await self.browser.close()

    async def crawl_page(self, url: str) -> Dict:
        """
        Crawl a single page and extract SEO elements.
        
        Args:
            url: The URL to crawl
            
        Returns:
            Dict containing extracted SEO elements and metadata
        """
        if not self.browser:
            await self.initialize()

        page = await self.context.new_page()
        try:
            # Navigate to the page
            response = await page.goto(
                url,
                wait_until="networkidle",
                timeout=self.config['crawler']['timeout']
            )

            if not response:
                raise Exception(f"Failed to load page: {url}")

            # Wait for JavaScript rendering
            await page.wait_for_load_state("networkidle")

            # Extract page content
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            # Extract SEO elements
            seo_data = {
                'url': url,
                'timestamp': datetime.utcnow().isoformat(),
                'status_code': response.status,
                'meta': self._extract_meta_tags(soup),
                'headers': self._extract_headers(soup),
                'images': self._extract_images(soup),
                'links': self._extract_links(soup),
                'schema': self._extract_schema(soup),
                'performance': await self._get_performance_metrics(page)
            }

            return seo_data

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            raise
        finally:
            await page.close()

    def _extract_meta_tags(self, soup: BeautifulSoup) -> Dict:
        """Extract meta tags from the page."""
        meta_tags = {}
        
        # Title
        title_tag = soup.find('title')
        meta_tags['title'] = title_tag.text if title_tag else None

        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_tags['description'] = meta_desc.get('content') if meta_desc else None

        # Canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        meta_tags['canonical'] = canonical.get('href') if canonical else None

        # Robots
        robots = soup.find('meta', attrs={'name': 'robots'})
        meta_tags['robots'] = robots.get('content') if robots else None

        return meta_tags

    def _extract_headers(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract header tags (h1-h6) from the page."""
        headers = {}
        for i in range(1, 7):
            headers[f'h{i}'] = [h.text.strip() for h in soup.find_all(f'h{i}')]
        return headers

    def _extract_images(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract image information including alt text."""
        images = []
        for img in soup.find_all('img'):
            images.append({
                'src': img.get('src'),
                'alt': img.get('alt'),
                'title': img.get('title')
            })
        return images

    def _extract_links(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract internal and external links."""
        links = {
            'internal': [],
            'external': []
        }
        base_domain = self._get_base_domain(self.config['monitoring']['urls'][0])
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/') or base_domain in href:
                links['internal'].append(href)
            else:
                links['external'].append(href)
        
        return links

    def _extract_schema(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract structured data/schema markup."""
        schema_data = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                schema_data.append(json.loads(script.string))
            except:
                continue
        return schema_data

    async def _get_performance_metrics(self, page: Page) -> Dict:
        """Get Core Web Vitals and other performance metrics."""
        metrics = {}
        try:
            # Get Core Web Vitals
            metrics['lcp'] = await page.evaluate('''() => {
                return new Promise((resolve) => {
                    new PerformanceObserver((entryList) => {
                        const entries = entryList.getEntries();
                        resolve(entries[entries.length - 1].startTime);
                    }).observe({entryTypes: ['largest-contentful-paint']});
                });
            }''')
            
            metrics['cls'] = await page.evaluate('''() => {
                return new Promise((resolve) => {
                    let cls = 0;
                    new PerformanceObserver((entryList) => {
                        for (const entry of entryList.getEntries()) {
                            cls += entry.value;
                        }
                        resolve(cls);
                    }).observe({entryTypes: ['layout-shift']});
                });
            }''')
            
            metrics['fid'] = await page.evaluate('''() => {
                return new Promise((resolve) => {
                    new PerformanceObserver((entryList) => {
                        const entries = entryList.getEntries();
                        resolve(entries[0].duration);
                    }).observe({entryTypes: ['first-input']});
                });
            }''')
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
        
        return metrics

    @staticmethod
    def _get_base_domain(url: str) -> str:
        """Extract base domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

async def main():
    """Example usage of the crawler."""
    crawler = SEOCrawler()
    try:
        await crawler.initialize()
        result = await crawler.crawl_page("https://example.com")
        print(result)
    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(main()) 