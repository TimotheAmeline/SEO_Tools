"""
URL Performance Analyzer
Analyzes performance changes at the URL level
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .utils import calculate_significance_score, filter_significant_data
import config

class URLPerformanceAnalyzer:
    """Analyzer for URL-level performance changes"""
    
    def __init__(self, historical_data=None):
        """
        Initialize the analyzer
        
        Args:
            historical_data (pd.DataFrame, optional): Historical GSC data
        """
        self.historical_data = historical_data
    
    def analyze(self, recent_data, comparison_period='month', min_impressions=25):
        """
        Analyze URL-level performance changes
        
        Args:
            recent_data (pd.DataFrame): Recent GSC data
            comparison_period (str): 'week' or 'month'
            min_impressions (int): Minimum impressions threshold
            
        Returns:
            pd.DataFrame: URL performance analysis results
        """
        if recent_data is None or recent_data.empty:
            return pd.DataFrame()
        
        if self.historical_data is None or self.historical_data.empty:
            return pd.DataFrame()
        
        # Check if historical_data is a Path object instead of DataFrame
        if isinstance(self.historical_data, (str, pd.core.indexes.base.Index)):
            try:
                print(f"Loading historical data from path: {self.historical_data}")
                self.historical_data = pd.read_parquet(self.historical_data)
            except Exception as e:
                print(f"Error loading historical data from path: {e}")
                return pd.DataFrame()
        
        # Determine date ranges
        max_date = recent_data['date'].max()
        
        if comparison_period == 'week':
            current_start = max_date - timedelta(days=7)
            previous_start = current_start - timedelta(days=7)
        else:  # month
            current_start = max_date - timedelta(days=30)
            previous_start = current_start - timedelta(days=30)
        
        # Filter data for different periods
        current_period = recent_data[recent_data['date'] >= current_start]
        previous_period = self.historical_data[
            (self.historical_data['date'] >= previous_start) & 
            (self.historical_data['date'] < current_start)
        ]
        
        # Apply significance filtering
        current_period = filter_significant_data(current_period)
        previous_period = filter_significant_data(previous_period)
        
        if current_period.empty or previous_period.empty:
            return pd.DataFrame()
        
        # Group by URL and aggregate metrics
        current_urls = current_period.groupby('page').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'position': 'mean',
            'query': lambda x: x.nunique()  # Count unique queries
        }).rename(columns={'query': 'unique_queries'}).reset_index()
        
        previous_urls = previous_period.groupby('page').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'position': 'mean',
            'query': lambda x: x.nunique()  # Count unique queries
        }).rename(columns={'query': 'unique_queries'}).reset_index()
        
        # Merge the periods
        merged = pd.merge(
            current_urls, 
            previous_urls,
            on='page', 
            how='outer', 
            suffixes=('_current', '_previous')
        )
        
        # Fill NaN values with 0 for new or disappeared URLs
        for col in ['impressions_current', 'clicks_current', 'unique_queries_current',
                    'impressions_previous', 'clicks_previous', 'unique_queries_previous']:
            merged[col] = merged[col].fillna(0)
        
        # Calculate changes
        for metric in ['impressions', 'clicks', 'unique_queries']:
            merged[f'{metric}_change'] = merged[f'{metric}_current'] - merged[f'{metric}_previous']
            merged[f'{metric}_change_pct'] = merged.apply(
                lambda row: (row[f'{metric}_change'] / row[f'{metric}_previous'] * 100)
                if row[f'{metric}_previous'] > 0 else 
                (100 if row[f'{metric}_current'] > 0 else 0),
                axis=1
            )
        
        # Position change (negative is improvement)
        merged['position_change'] = merged.apply(
            lambda row: row.get('position_current', 0) - row.get('position_previous', 0)
            if not pd.isna(row.get('position_current')) and not pd.isna(row.get('position_previous'))
            else 0,
            axis=1
        )
        
        # Calculate significance score based on volume
        merged['significance_score'] = merged.apply(
            lambda row: calculate_significance_score(
                row.get('impressions_current', 0), 
                row.get('clicks_current', 0)
            ),
            axis=1
        )
        
        # Filter for significant URLs
        significant_urls = merged[merged['impressions_current'] >= min_impressions].copy()
        
        # Determine if URL is new or lost
        significant_urls['is_new'] = significant_urls['impressions_previous'] == 0
        significant_urls['is_lost'] = significant_urls['impressions_current'] == 0
        
        # Classify performance changes
        significant_urls.loc[:, 'performance_change'] = significant_urls.apply(
            lambda row: self._classify_url_change(
                row['impressions_change_pct'],
                row['unique_queries_change_pct'],
                row['position_change'],
                row['is_new'],
                row['is_lost']
            ),
            axis=1
        )
        
        # Sort by significance and impressions
        significant_urls = significant_urls.sort_values(
            by=['significance_score', 'impressions_current'], 
            ascending=[False, False]
        )
        
        # Format for output
        for col in significant_urls.select_dtypes(include=['float']).columns:
            if 'pct' in col:
                significant_urls[col] = significant_urls[col].round(1)
            elif 'position' in col:
                significant_urls[col] = significant_urls[col].round(2)
            else:
                significant_urls[col] = significant_urls[col].round(0)
        
        return significant_urls
    
    def _classify_url_change(self, imp_change_pct, query_change_pct, position_change, is_new, is_lost):
        """
        Classify URL performance change
        
        Args:
            imp_change_pct (float): Impressions change percentage
            query_change_pct (float): Unique queries change percentage
            position_change (float): Position change (negative is improvement)
            is_new (bool): Whether the URL is new
            is_lost (bool): Whether the URL is lost
            
        Returns:
            str: Classification of performance change
        """
        if is_new:
            return "new_page"
        elif is_lost:
            return "lost_page"
        elif position_change < -0.5 and imp_change_pct > 10:
            return "significant_improvement"
        elif position_change > 0.5 and imp_change_pct < -10:
            return "significant_decline"
        elif query_change_pct < -20 and imp_change_pct < -10:
            return "losing_query_diversity"
        elif query_change_pct > 20 and imp_change_pct > 10:
            return "gaining_query_diversity"
        elif imp_change_pct > 30:
            return "major_traffic_gain"
        elif imp_change_pct < -30:
            return "major_traffic_loss"
        elif imp_change_pct > 10:
            return "moderate_traffic_gain"
        elif imp_change_pct < -10:
            return "moderate_traffic_loss"
        else:
            return "stable"