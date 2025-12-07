"""
CTR Outlier Analyzer
Detects pages with CTR significantly different from expected for their position
"""
import pandas as pd
import numpy as np
from .utils import get_expected_ctr_for_position, calculate_significance_score, filter_significant_data
import config

class CTROutlierAnalyzer:
    """Analyzer for CTR outliers"""
    
    def __init__(self, historical_data=None):
        """
        Initialize the analyzer
        
        Args:
            historical_data (pd.DataFrame, optional): Historical GSC data
        """
        self.historical_data = historical_data
        self.position_ctr_baselines = {}
        
        # Calculate position-CTR baselines if historical data available
        if historical_data is not None:
            self.calculate_position_ctr_baselines()
    
    def calculate_position_ctr_baselines(self):
        """Calculate baseline CTR for each position based on historical data"""
        if self.historical_data is None or self.historical_data.empty:
            return
        
        # Filter for significant data
        filtered_data = filter_significant_data(self.historical_data)
        
        # Group by rounded position
        filtered_data['position_rounded'] = filtered_data['position'].round().astype(int)
        position_groups = filtered_data.groupby('position_rounded')
        
        # Calculate median CTR for each position
        for position, group in position_groups:
            if position > 0 and position <= 20:  # Only care about top 20 positions
                median_ctr = group['ctr'].median()
                self.position_ctr_baselines[position] = median_ctr
    
    def analyze(self, data, use_baseline=True):
        """
        Analyze CTR outliers
        
        Args:
            data (pd.DataFrame): GSC data to analyze
            use_baseline (bool): Whether to use calculated baselines or config defaults
            
        Returns:
            pd.DataFrame: Outlier analysis results
        """
        if data is None or data.empty:
            return pd.DataFrame()
        
        # Filter for significant data
        filtered_data = filter_significant_data(data)
        
        if filtered_data.empty:
            return pd.DataFrame()
        
        # Calculate expected CTR for each position
        results = []
        
        # Group by page and query
        groups = filtered_data.groupby(['page', 'query'])
        
        for (page, query), group in groups:
            # Calculate averages
            avg_position = group['position'].mean()
            avg_ctr = group['ctr'].mean()
            total_impressions = group['impressions'].sum()
            total_clicks = group['clicks'].sum()
            
            # Skip if below thresholds
            if total_impressions < config.MIN_IMPRESSIONS or total_clicks < config.MIN_CLICKS:
                continue
            
            # Get expected CTR based on position
            if use_baseline and avg_position in self.position_ctr_baselines:
                expected_ctr = self.position_ctr_baselines[int(round(avg_position))]
            else:
                expected_ctr = get_expected_ctr_for_position(avg_position)
            
            # Calculate CTR difference
            ctr_difference = avg_ctr - expected_ctr
            ctr_difference_pct = (ctr_difference / expected_ctr) * 100 if expected_ctr > 0 else 0
            
            # Determine if outlier
            is_underperforming = ctr_difference < -0.02 and ctr_difference_pct < -15
            is_overperforming = ctr_difference > 0.02 and ctr_difference_pct > 15
            
            # Calculate significance score
            significance = calculate_significance_score(total_impressions, total_clicks)
            
            # Add to results
            results.append({
                'page': page,
                'query': query,
                'avg_position': round(avg_position, 2),
                'actual_ctr': round(avg_ctr, 4),
                'expected_ctr': round(expected_ctr, 4),
                'ctr_difference': round(ctr_difference, 4),
                'ctr_difference_pct': round(ctr_difference_pct, 2),
                'impressions': total_impressions,
                'clicks': total_clicks,
                'is_underperforming': is_underperforming,
                'is_overperforming': is_overperforming,
                'significance_score': round(significance, 2),
                'status': 'underperforming' if is_underperforming else 
                          'overperforming' if is_overperforming else 'normal'
            })
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame and sort by significance
        results_df = pd.DataFrame(results)
        
        # Sort by significance score and status (underperforming first)
        results_df = results_df.sort_values(
            by=['is_underperforming', 'significance_score'], 
            ascending=[False, False]
        )
        
        return results_df