"""
Tests for the comparator module.
"""

import pytest
from ..comparator import SEOComparator

@pytest.fixture
def comparator():
    """Create a comparator instance for testing."""
    return SEOComparator()

@pytest.fixture
def sample_baseline():
    """Create a sample baseline snapshot."""
    return {
        'meta_tags': {
            'title': 'Example Page | Brand',
            'description': 'This is an example page description',
            'canonical': 'https://example.com/page',
            'robots': 'index, follow'
        },
        'headers': {
            'h1': ['Main Heading'],
            'h2': ['Sub Heading 1', 'Sub Heading 2'],
            'h3': ['Section 1', 'Section 2']
        },
        'images': [
            {
                'src': 'https://example.com/image1.jpg',
                'alt': 'Image 1 description',
                'title': 'Image 1'
            }
        ],
        'links': {
            'internal': ['/about', '/contact'],
            'external': ['https://external.com']
        },
        'schema': [
            {
                '@type': 'WebPage',
                'name': 'Example Page'
            }
        ],
        'performance': {
            'lcp': 1.5,
            'cls': 0.05,
            'fid': 50
        }
    }

@pytest.fixture
def sample_current():
    """Create a sample current snapshot with changes."""
    return {
        'meta_tags': {
            'title': 'Example Page',  # Changed
            'description': 'This is an example page description',
            'canonical': 'https://example.com/page',
            'robots': 'index, follow'
        },
        'headers': {
            'h1': ['Main Heading'],
            'h2': ['New Sub Heading', 'Sub Heading 2'],  # Changed
            'h3': ['Section 1', 'Section 2']
        },
        'images': [
            {
                'src': 'https://example.com/image1.jpg',
                'alt': 'New image description',  # Changed
                'title': 'Image 1'
            },
            {
                'src': 'https://example.com/image2.jpg',  # Added
                'alt': 'Image 2 description',
                'title': 'Image 2'
            }
        ],
        'links': {
            'internal': ['/about', '/new-page'],  # Changed
            'external': ['https://external.com', 'https://new-external.com']  # Added
        },
        'schema': [
            {
                '@type': 'WebPage',
                'name': 'Example Page',
                'description': 'Added description'  # Changed
            }
        ],
        'performance': {
            'lcp': 2.0,  # Changed
            'cls': 0.05,
            'fid': 50
        }
    }

def test_compare_snapshots(comparator, sample_baseline, sample_current):
    """Test snapshot comparison functionality."""
    changes = comparator.compare_snapshots(sample_baseline, sample_current)
    
    # Check that changes were detected
    assert len(changes) > 0
    
    # Check meta tag changes
    title_changes = [c for c in changes if c['element_type'] == 'meta_title']
    assert len(title_changes) == 1
    assert title_changes[0]['change_type'] == 'critical'
    
    # Check header changes
    h2_changes = [c for c in changes if c['element_type'] == 'h2']
    assert len(h2_changes) == 1
    assert h2_changes[0]['change_type'] == 'warning'
    
    # Check image changes
    image_changes = [c for c in changes if c['element_type'] == 'image']
    assert len(image_changes) == 1
    assert image_changes[0]['change_type'] == 'info'
    
    alt_changes = [c for c in changes if c['element_type'] == 'image_alt']
    assert len(alt_changes) == 1
    assert alt_changes[0]['change_type'] == 'warning'
    
    # Check link changes
    internal_link_changes = [c for c in changes if c['element_type'] == 'internal_links_added']
    assert len(internal_link_changes) == 1
    assert internal_link_changes[0]['change_type'] == 'info'
    
    # Check schema changes
    schema_changes = [c for c in changes if c['element_type'] == 'schema_added']
    assert len(schema_changes) == 1
    assert schema_changes[0]['change_type'] == 'info'
    
    # Check performance changes
    performance_changes = [c for c in changes if c['element_type'] == 'performance_lcp']
    assert len(performance_changes) == 1
    assert performance_changes[0]['change_type'] == 'warning'

def test_change_classification(comparator):
    """Test change classification logic."""
    # Test critical changes
    assert comparator._determine_change_type('meta_title', 'old', 'new') == 'critical'
    assert comparator._determine_change_type('meta_description', 'old', 'new') == 'critical'
    assert comparator._determine_change_type('h1', 'old', 'new') == 'critical'
    assert comparator._determine_change_type('canonical', 'old', 'new') == 'critical'
    
    # Test warning changes
    assert comparator._determine_change_type('h2', 'old', 'new') == 'warning'
    assert comparator._determine_change_type('image_alt', 'old', 'new') == 'warning'
    assert comparator._determine_change_type('internal_links', 'old', 'new') == 'warning'
    
    # Test info changes
    assert comparator._determine_change_type('h3', 'old', 'new') == 'info'
    assert comparator._determine_change_type('schema', 'old', 'new') == 'info'

def test_performance_classification(comparator):
    """Test performance change classification."""
    # Test LCP changes
    assert comparator._determine_performance_change_type('lcp', 1.0, 3.0) == 'critical'
    assert comparator._determine_performance_change_type('lcp', 1.0, 2.0) == 'warning'
    assert comparator._determine_performance_change_type('lcp', 2.0, 1.0) == 'info'
    
    # Test CLS changes
    assert comparator._determine_performance_change_type('cls', 0.05, 0.15) == 'critical'
    assert comparator._determine_performance_change_type('cls', 0.05, 0.08) == 'warning'
    assert comparator._determine_performance_change_type('cls', 0.08, 0.05) == 'info'
    
    # Test FID changes
    assert comparator._determine_performance_change_type('fid', 50, 150) == 'critical'
    assert comparator._determine_performance_change_type('fid', 50, 80) == 'warning'
    assert comparator._determine_performance_change_type('fid', 80, 50) == 'info' 