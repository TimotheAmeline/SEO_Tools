"""
Tests for the crawler module.
"""

import pytest
import asyncio
from ..crawler import SEOCrawler

@pytest.fixture
def crawler():
    """Create a crawler instance for testing."""
    return SEOCrawler()

@pytest.mark.asyncio
async def test_crawler_initialization(crawler):
    """Test crawler initialization."""
    await crawler.initialize()
    assert crawler.browser is not None
    assert crawler.context is not None
    await crawler.close()

@pytest.mark.asyncio
async def test_crawl_page(crawler):
    """Test page crawling functionality."""
    await crawler.initialize()
    try:
        result = await crawler.crawl_page("https://example.com")
        
        # Check basic structure
        assert 'url' in result
        assert 'timestamp' in result
        assert 'status_code' in result
        assert 'meta' in result
        assert 'headers' in result
        assert 'images' in result
        assert 'links' in result
        assert 'schema' in result
        assert 'performance' in result
        
        # Check meta tags
        assert 'title' in result['meta']
        assert 'description' in result['meta']
        assert 'canonical' in result['meta']
        assert 'robots' in result['meta']
        
        # Check headers
        for i in range(1, 7):
            assert f'h{i}' in result['headers']
        
        # Check performance metrics
        assert 'lcp' in result['performance']
        assert 'cls' in result['performance']
        assert 'fid' in result['performance']
        
    finally:
        await crawler.close()

@pytest.mark.asyncio
async def test_error_handling(crawler):
    """Test error handling for invalid URLs."""
    await crawler.initialize()
    try:
        with pytest.raises(Exception):
            await crawler.crawl_page("https://invalid-url-that-does-not-exist.com")
    finally:
        await crawler.close() 