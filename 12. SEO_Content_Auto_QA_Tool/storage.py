"""
Storage module for SEO Auto QA tool.
Handles data persistence using SQLAlchemy.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import yaml
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class PageSnapshot(Base):
    """Model for storing page snapshots."""
    __tablename__ = 'page_snapshots'

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    status_code = Column(Integer)
    meta_tags = Column(JSON)
    headers = Column(JSON)
    images = Column(JSON)
    links = Column(JSON)
    schema = Column(JSON)
    performance = Column(JSON)

    changes = relationship("PageChange", back_populates="snapshot")

class PageChange(Base):
    """Model for storing detected changes between snapshots."""
    __tablename__ = 'page_changes'

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('page_snapshots.id'))
    element_type = Column(String, nullable=False)
    change_type = Column(String, nullable=False)  # 'critical', 'warning', 'info'
    old_value = Column(JSON)
    new_value = Column(JSON)
    timestamp = Column(DateTime, nullable=False)
    impact_score = Column(Float)

    snapshot = relationship("PageSnapshot", back_populates="changes")

class Storage:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize storage with configuration."""
        self.config = self._load_config(config_path)
        self.engine = create_engine(self.config['storage']['database_url'])
        self.Session = sessionmaker(bind=self.engine)
        self._create_tables()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def _create_tables(self):
        """Create database tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def save_snapshot(self, seo_data: Dict) -> int:
        """
        Save a page snapshot to the database.
        
        Args:
            seo_data: Dictionary containing SEO data from crawler
            
        Returns:
            ID of the created snapshot
        """
        session = self.Session()
        try:
            snapshot = PageSnapshot(
                url=seo_data['url'],
                timestamp=datetime.fromisoformat(seo_data['timestamp']),
                status_code=seo_data['status_code'],
                meta_tags=seo_data['meta'],
                headers=seo_data['headers'],
                images=seo_data['images'],
                links=seo_data['links'],
                schema=seo_data['schema'],
                performance=seo_data['performance']
            )
            session.add(snapshot)
            session.commit()
            return snapshot.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving snapshot: {e}")
            raise
        finally:
            session.close()

    def save_change(self, snapshot_id: int, change_data: Dict) -> None:
        """
        Save a detected change to the database.
        
        Args:
            snapshot_id: ID of the associated snapshot
            change_data: Dictionary containing change information
        """
        session = self.Session()
        try:
            change = PageChange(
                snapshot_id=snapshot_id,
                element_type=change_data['element_type'],
                change_type=change_data['change_type'],
                old_value=change_data['old_value'],
                new_value=change_data['new_value'],
                timestamp=datetime.utcnow(),
                impact_score=change_data.get('impact_score', 0.0)
            )
            session.add(change)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving change: {e}")
            raise
        finally:
            session.close()

    def get_latest_snapshot(self, url: str) -> Optional[Dict]:
        """
        Get the most recent snapshot for a URL.
        
        Args:
            url: The URL to get the snapshot for
            
        Returns:
            Dictionary containing snapshot data or None if not found
        """
        session = self.Session()
        try:
            snapshot = session.query(PageSnapshot)\
                .filter(PageSnapshot.url == url)\
                .order_by(PageSnapshot.timestamp.desc())\
                .first()
            
            if snapshot:
                return {
                    'id': snapshot.id,
                    'url': snapshot.url,
                    'timestamp': snapshot.timestamp.isoformat(),
                    'status_code': snapshot.status_code,
                    'meta_tags': snapshot.meta_tags,
                    'headers': snapshot.headers,
                    'images': snapshot.images,
                    'links': snapshot.links,
                    'schema': snapshot.schema,
                    'performance': snapshot.performance
                }
            return None
        finally:
            session.close()

    def get_changes(self, snapshot_id: int) -> List[Dict]:
        """
        Get all changes associated with a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot
            
        Returns:
            List of dictionaries containing change data
        """
        session = self.Session()
        try:
            changes = session.query(PageChange)\
                .filter(PageChange.snapshot_id == snapshot_id)\
                .all()
            
            return [{
                'id': change.id,
                'element_type': change.element_type,
                'change_type': change.change_type,
                'old_value': change.old_value,
                'new_value': change.new_value,
                'timestamp': change.timestamp.isoformat(),
                'impact_score': change.impact_score
            } for change in changes]
        finally:
            session.close()

    def cleanup_old_data(self) -> None:
        """Remove data older than the retention period."""
        session = self.Session()
        try:
            retention_days = self.config['storage']['history_retention_days']
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Delete old snapshots and their associated changes
            old_snapshots = session.query(PageSnapshot)\
                .filter(PageSnapshot.timestamp < cutoff_date)\
                .all()
            
            for snapshot in old_snapshots:
                session.delete(snapshot)
            
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up old data: {e}")
            raise
        finally:
            session.close() 