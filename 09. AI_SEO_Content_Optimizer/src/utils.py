import os
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_cache_key(url: str) -> str:
    """Create a unique cache key for a URL."""
    return hashlib.md5(url.encode()).hexdigest()

def get_cache_path() -> Path:
    """Get the path to the cache directory."""
    cache_dir = Path(__file__).parent.parent / 'cache'
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

def get_reports_path() -> Path:
    """Get the path to the reports directory."""
    reports_dir = Path(__file__).parent.parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    return reports_dir

def save_to_cache(data: Dict[str, Any], url: str) -> None:
    """Save data to cache."""
    cache_key = create_cache_key(url)
    cache_path = get_cache_path() / f"{cache_key}.json"
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'data': data
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving to cache: {e}")

def load_from_cache(url: str) -> Optional[Dict[str, Any]]:
    """Load data from cache if it exists and is not expired."""
    cache_key = create_cache_key(url)
    cache_path = get_cache_path() / f"{cache_key}.json"
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            
        # Check if cache is older than 24 hours
        cache_time = datetime.fromisoformat(cached_data['timestamp'])
        if (datetime.now() - cache_time).days >= 1:
            return None
            
        return cached_data['data']
    except Exception as e:
        logger.error(f"Error loading from cache: {e}")
        return None

def save_report(report_data: Dict[str, Any], url: str) -> None:
    """Save the analysis report to the reports directory."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    url_slug = url.replace('https://', '').replace('http://', '').replace('/', '_')
    report_path = get_reports_path() / f"report_{url_slug}_{timestamp}"
    
    # Ensure reports directory exists
    get_reports_path().mkdir(exist_ok=True)
    
    # Save JSON report
    json_path = report_path.with_suffix('.json')
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving JSON report: {e}")
    
    # Save human-readable report
    txt_path = report_path.with_suffix('.txt')
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"SEO Content Analysis Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Target URL: {url}\n\n")
            
            for section, content in report_data.items():
                f.write(f"\n{section.upper()}\n")
                f.write("=" * len(section) + "\n")
                if isinstance(content, dict):
                    for key, value in content.items():
                        f.write(f"\n{key}:\n{value}\n")
                else:
                    f.write(f"{content}\n")
    except Exception as e:
        logger.error(f"Error saving text report: {e}")

def validate_url(url: str) -> bool:
    """Validate if the provided string is a valid URL."""
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def get_word_count(text: str) -> int:
    """Get the word count of a text."""
    return len(text.split())

def calculate_keyword_density(text: str, keyword: str) -> float:
    """Calculate the density of a keyword in the text."""
    if not text or not keyword:
        return 0.0
    
    word_count = get_word_count(text)
    if word_count == 0:
        return 0.0
    
    keyword_count = text.lower().count(keyword.lower())
    return (keyword_count / word_count) * 100 