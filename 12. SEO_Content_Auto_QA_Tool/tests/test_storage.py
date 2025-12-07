"""
Tests for the storage module.
"""

import pytest
from datetime import datetime, timedelta
from ..storage import Storage, PageSnapshot, PageChange

@pytest.fixture
def storage():
    """Create a storage instance for testing."""
    return Storage('test_config.yaml')

@pytest.fixture
def sample_seo_data():
    """Create sample SEO data for testing."""
    return {
        'url': 'https://example.com',
        'timestamp': datetime.utcnow().isoformat(),
        'status_code': 200,
        'meta': {
            'title': 'Example Page',
            'description': 'Test description',
            'canonical': 'https://example.com',
            'robots': 'index, follow'
        },
        'headers': {
            'h1': ['Main Heading'],
            'h2': ['Sub Heading']
        },
        'images': [
            {
                'src': 'https://example.com/image.jpg',
                'alt': 'Test image',
                'title': 'Image title'
            }
        ],
        'links': {
            'internal': ['/about'],
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
def sample_change_data():
    """Create sample change data for testing."""
    return {
        'element_type': 'meta_title',
        'change_type': 'critical',
        'old_value': 'Old Title',
        'new_value': 'New Title',
        'impact_score': 0.8
    }

def test_save_snapshot(storage, sample_seo_data):
    """Test saving a snapshot."""
    snapshot_id = storage.save_snapshot(sample_seo_data)
    assert snapshot_id is not None
    
    # Verify snapshot was saved
    session = storage.Session()
    try:
        snapshot = session.query(PageSnapshot).get(snapshot_id)
        assert snapshot is not None
        assert snapshot.url == sample_seo_data['url']
        assert snapshot.status_code == sample_seo_data['status_code']
        assert snapshot.meta_tags == sample_seo_data['meta']
        assert snapshot.headers == sample_seo_data['headers']
        assert snapshot.images == sample_seo_data['images']
        assert snapshot.links == sample_seo_data['links']
        assert snapshot.schema == sample_seo_data['schema']
        assert snapshot.performance == sample_seo_data['performance']
    finally:
        session.close()

def test_save_change(storage, sample_seo_data, sample_change_data):
    """Test saving a change."""
    # First save a snapshot
    snapshot_id = storage.save_snapshot(sample_seo_data)
    
    # Then save a change
    storage.save_change(snapshot_id, sample_change_data)
    
    # Verify change was saved
    session = storage.Session()
    try:
        change = session.query(PageChange).filter_by(snapshot_id=snapshot_id).first()
        assert change is not None
        assert change.element_type == sample_change_data['element_type']
        assert change.change_type == sample_change_data['change_type']
        assert change.old_value == sample_change_data['old_value']
        assert change.new_value == sample_change_data['new_value']
        assert change.impact_score == sample_change_data['impact_score']
    finally:
        session.close()

def test_get_latest_snapshot(storage, sample_seo_data):
    """Test retrieving the latest snapshot."""
    # Save a snapshot
    storage.save_snapshot(sample_seo_data)
    
    # Get latest snapshot
    snapshot = storage.get_latest_snapshot(sample_seo_data['url'])
    
    assert snapshot is not None
    assert snapshot['url'] == sample_seo_data['url']
    assert snapshot['status_code'] == sample_seo_data['status_code']
    assert snapshot['meta_tags'] == sample_seo_data['meta']
    assert snapshot['headers'] == sample_seo_data['headers']
    assert snapshot['images'] == sample_seo_data['images']
    assert snapshot['links'] == sample_seo_data['links']
    assert snapshot['schema'] == sample_seo_data['schema']
    assert snapshot['performance'] == sample_seo_data['performance']

def test_get_changes(storage, sample_seo_data, sample_change_data):
    """Test retrieving changes for a snapshot."""
    # Save a snapshot and its changes
    snapshot_id = storage.save_snapshot(sample_seo_data)
    storage.save_change(snapshot_id, sample_change_data)
    
    # Get changes
    changes = storage.get_changes(snapshot_id)
    
    assert len(changes) == 1
    change = changes[0]
    assert change['element_type'] == sample_change_data['element_type']
    assert change['change_type'] == sample_change_data['change_type']
    assert change['old_value'] == sample_change_data['old_value']
    assert change['new_value'] == sample_change_data['new_value']
    assert change['impact_score'] == sample_change_data['impact_score']

def test_cleanup_old_data(storage, sample_seo_data):
    """Test cleanup of old data."""
    # Save a snapshot
    storage.save_snapshot(sample_seo_data)
    
    # Modify retention period to 1 day
    storage.config['storage']['history_retention_days'] = 1
    
    # Create old snapshot
    old_data = sample_seo_data.copy()
    old_data['timestamp'] = (datetime.utcnow() - timedelta(days=2)).isoformat()
    storage.save_snapshot(old_data)
    
    # Run cleanup
    storage.cleanup_old_data()
    
    # Verify old data was removed
    session = storage.Session()
    try:
        snapshots = session.query(PageSnapshot).all()
        assert len(snapshots) == 1
        assert snapshots[0].timestamp > datetime.utcnow() - timedelta(days=1)
    finally:
        session.close() 