"""
Comparator module for SEO Auto QA tool.
Handles comparison between snapshots and change detection.
"""

from typing import Dict, List, Tuple
import yaml
import logging
from difflib import SequenceMatcher
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SEOComparator:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the comparator with configuration."""
        self.config = self._load_config(config_path)
        self.element_weights = self.config['element_weights']

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def compare_snapshots(self, baseline: Dict, current: Dict) -> List[Dict]:
        """
        Compare two snapshots and detect changes.
        
        Args:
            baseline: Dictionary containing baseline snapshot data
            current: Dictionary containing current snapshot data
            
        Returns:
            List of dictionaries containing detected changes
        """
        changes = []
        
        # Compare meta tags
        changes.extend(self._compare_meta_tags(baseline['meta_tags'], current['meta_tags']))
        
        # Compare headers
        changes.extend(self._compare_headers(baseline['headers'], current['headers']))
        
        # Compare images
        changes.extend(self._compare_images(baseline['images'], current['images']))
        
        # Compare links
        changes.extend(self._compare_links(baseline['links'], current['links']))
        
        # Compare schema
        changes.extend(self._compare_schema(baseline['schema'], current['schema']))
        
        # Compare performance metrics
        changes.extend(self._compare_performance(baseline['performance'], current['performance']))
        
        return changes

    def _compare_meta_tags(self, baseline: Dict, current: Dict) -> List[Dict]:
        """Compare meta tags between snapshots."""
        changes = []
        
        for tag_name in ['title', 'description', 'canonical', 'robots']:
            if tag_name in baseline and tag_name in current:
                if baseline[tag_name] != current[tag_name]:
                    change_type = self._determine_change_type(tag_name, baseline[tag_name], current[tag_name])
                    impact_score = self._calculate_impact_score(tag_name, baseline[tag_name], current[tag_name])
                    
                    changes.append({
                        'element_type': f'meta_{tag_name}',
                        'change_type': change_type,
                        'old_value': baseline[tag_name],
                        'new_value': current[tag_name],
                        'impact_score': impact_score
                    })
        
        return changes

    def _compare_headers(self, baseline: Dict, current: Dict) -> List[Dict]:
        """Compare header tags between snapshots."""
        changes = []
        
        for level in range(1, 7):
            header_key = f'h{level}'
            if header_key in baseline and header_key in current:
                if baseline[header_key] != current[header_key]:
                    change_type = self._determine_change_type(header_key, baseline[header_key], current[header_key])
                    impact_score = self._calculate_impact_score(header_key, baseline[header_key], current[header_key])
                    
                    changes.append({
                        'element_type': header_key,
                        'change_type': change_type,
                        'old_value': baseline[header_key],
                        'new_value': current[header_key],
                        'impact_score': impact_score
                    })
        
        return changes

    def _compare_images(self, baseline: List[Dict], current: List[Dict]) -> List[Dict]:
        """Compare image information between snapshots."""
        changes = []
        
        # Create lookup dictionaries for easier comparison
        baseline_dict = {img['src']: img for img in baseline}
        current_dict = {img['src']: img for img in current}
        
        # Check for removed images
        for src, img in baseline_dict.items():
            if src not in current_dict:
                changes.append({
                    'element_type': 'image',
                    'change_type': 'warning',
                    'old_value': img,
                    'new_value': None,
                    'impact_score': 0.5
                })
        
        # Check for new images and changes
        for src, img in current_dict.items():
            if src not in baseline_dict:
                changes.append({
                    'element_type': 'image',
                    'change_type': 'info',
                    'old_value': None,
                    'new_value': img,
                    'impact_score': 0.2
                })
            else:
                baseline_img = baseline_dict[src]
                if baseline_img['alt'] != img['alt']:
                    changes.append({
                        'element_type': 'image_alt',
                        'change_type': 'warning',
                        'old_value': baseline_img['alt'],
                        'new_value': img['alt'],
                        'impact_score': 0.4
                    })
        
        return changes

    def _compare_links(self, baseline: Dict, current: Dict) -> List[Dict]:
        """Compare internal and external links between snapshots."""
        changes = []
        
        for link_type in ['internal', 'external']:
            if link_type in baseline and link_type in current:
                baseline_links = set(baseline[link_type])
                current_links = set(current[link_type])
                
                # Check for removed links
                removed_links = baseline_links - current_links
                if removed_links:
                    changes.append({
                        'element_type': f'{link_type}_links_removed',
                        'change_type': 'warning',
                        'old_value': list(removed_links),
                        'new_value': [],
                        'impact_score': 0.3
                    })
                
                # Check for new links
                new_links = current_links - baseline_links
                if new_links:
                    changes.append({
                        'element_type': f'{link_type}_links_added',
                        'change_type': 'info',
                        'old_value': [],
                        'new_value': list(new_links),
                        'impact_score': 0.2
                    })
        
        return changes

    def _compare_schema(self, baseline: List[Dict], current: List[Dict]) -> List[Dict]:
        """Compare schema markup between snapshots."""
        changes = []
        
        # Convert schema to comparable format
        baseline_schema = {json.dumps(s, sort_keys=True): s for s in baseline}
        current_schema = {json.dumps(s, sort_keys=True): s for s in current}
        
        # Check for removed schema
        for schema_str, schema in baseline_schema.items():
            if schema_str not in current_schema:
                changes.append({
                    'element_type': 'schema_removed',
                    'change_type': 'warning',
                    'old_value': schema,
                    'new_value': None,
                    'impact_score': 0.6
                })
        
        # Check for new schema
        for schema_str, schema in current_schema.items():
            if schema_str not in baseline_schema:
                changes.append({
                    'element_type': 'schema_added',
                    'change_type': 'info',
                    'old_value': None,
                    'new_value': schema,
                    'impact_score': 0.3
                })
        
        return changes

    def _compare_performance(self, baseline: Dict, current: Dict) -> List[Dict]:
        """Compare performance metrics between snapshots."""
        changes = []
        
        for metric in ['lcp', 'cls', 'fid']:
            if metric in baseline and metric in current:
                baseline_value = baseline[metric]
                current_value = current[metric]
                
                if baseline_value != current_value:
                    change_type = self._determine_performance_change_type(metric, baseline_value, current_value)
                    impact_score = self._calculate_performance_impact(metric, baseline_value, current_value)
                    
                    changes.append({
                        'element_type': f'performance_{metric}',
                        'change_type': change_type,
                        'old_value': baseline_value,
                        'new_value': current_value,
                        'impact_score': impact_score
                    })
        
        return changes

    def _determine_change_type(self, element_type: str, old_value: any, new_value: any) -> str:
        """Determine the type of change based on element type and values."""
        if element_type in ['meta_title', 'meta_description', 'h1', 'canonical']:
            return 'critical'
        elif element_type in ['h2', 'image_alt', 'internal_links']:
            return 'warning'
        else:
            return 'info'

    def _calculate_impact_score(self, element_type: str, old_value: any, new_value: any) -> float:
        """Calculate the impact score for a change."""
        base_weight = self.element_weights.get(element_type, 0.5)
        
        if isinstance(old_value, str) and isinstance(new_value, str):
            similarity = SequenceMatcher(None, old_value, new_value).ratio()
            return base_weight * (1 - similarity)
        
        return base_weight

    def _determine_performance_change_type(self, metric: str, old_value: float, new_value: float) -> str:
        """Determine the type of performance change."""
        thresholds = self.config['performance']['core_web_vitals']
        
        if metric == 'lcp':
            if new_value > thresholds['lcp_threshold']:
                return 'critical'
            elif new_value > old_value:
                return 'warning'
        elif metric == 'cls':
            if new_value > thresholds['cls_threshold']:
                return 'critical'
            elif new_value > old_value:
                return 'warning'
        elif metric == 'fid':
            if new_value > thresholds['fid_threshold']:
                return 'critical'
            elif new_value > old_value:
                return 'warning'
        
        return 'info'

    def _calculate_performance_impact(self, metric: str, old_value: float, new_value: float) -> float:
        """Calculate the impact score for a performance change."""
        thresholds = self.config['performance']['core_web_vitals']
        
        if metric == 'lcp':
            threshold = thresholds['lcp_threshold']
            impact = (new_value - old_value) / threshold
        elif metric == 'cls':
            threshold = thresholds['cls_threshold']
            impact = (new_value - old_value) / threshold
        elif metric == 'fid':
            threshold = thresholds['fid_threshold']
            impact = (new_value - old_value) / threshold
        else:
            impact = 0.0
        
        return min(max(impact, 0.0), 1.0) 