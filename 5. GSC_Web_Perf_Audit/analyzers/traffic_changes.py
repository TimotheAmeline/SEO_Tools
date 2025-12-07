"""
Traffic Change Analyzer
Detects significant changes in traffic (impressions, clicks) over time
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .utils import (
    calculate_significance_score, 
    filter_significant_data,
    group_data_by_time_period,
    detect_is_weekend
)
import config

class TrafficChangeAnalyzer:
    """Analyzer for significant traffic changes"""
    
    def __init__(self, historical_data=None, seasonality_analyzer=None):
        """
        Initialize the analyzer
        
        Args:
            historical_data (pd.DataFrame, optional): Historical GSC data
            seasonality_analyzer (SeasonalityAnalyzer, optional): Seasonality analyzer instance
        """
        self.historical_data = historical_data
        self.seasonality_analyzer = seasonality_analyzer
    
    def analyze(self, recent_data, comparison_period='week', min_change_pct=15):
        """
        Analyze traffic changes
        
        Args:
            recent_data (pd.DataFrame): Recent GSC data
            comparison_period (str): 'week' or 'month'
            min_change_pct (float): Minimum change percentage to consider significant
            
        Returns:
            pd.DataFrame: Traffic change analysis results
        """
        if recent_data is None or recent_data.empty:
            return pd.DataFrame()
        
        if self.historical_data is None or self.historical_data.empty:
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
        
        # Group by page and query
        current_grouped = current_period.groupby(['page', 'query']).agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'position': 'mean',
            'country': lambda x: x.iloc[0] if not x.empty else None  # Take first country
        }).reset_index()
        
        previous_grouped = previous_period.groupby(['page', 'query']).agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'position': 'mean'
        }).reset_index()
        
        # Merge the periods
        merged = pd.merge(
            current_grouped, 
            previous_grouped,
            on=['page', 'query'], 
            how='outer', 
            suffixes=('_current', '_previous')
        )
        
        # Fill NaN values with 0 for new or disappeared pages/queries
        for col in ['impressions_current', 'clicks_current', 
                    'impressions_previous', 'clicks_previous']:
            merged[col] = merged[col].fillna(0)
        
        # Calculate changes
        merged['impressions_change'] = merged['impressions_current'] - merged['impressions_previous']
        merged['clicks_change'] = merged['clicks_current'] - merged['clicks_previous']
        
        # Calculate percentage changes (handle division by zero)
        merged['impressions_change_pct'] = merged.apply(
            lambda row: (row['impressions_change'] / row['impressions_previous'] * 100)
            if row['impressions_previous'] > 0 else 
            (100 if row['impressions_current'] > 0 else 0),
            axis=1
        )
        
        merged['clicks_change_pct'] = merged.apply(
            lambda row: (row['clicks_change'] / row['clicks_previous'] * 100)
            if row['clicks_previous'] > 0 else 
            (100 if row['clicks_current'] > 0 else 0),
            axis=1
        )
        
        # Position change (negative is improvement)
        merged['position_change'] = merged.apply(
            lambda row: row.get('position_current', 0) - row.get('position_previous', 0)
            if not pd.isna(row.get('position_current')) and not pd.isna(row.get('position_previous'))
            else 0,
            axis=1
        )
        
        # Calculate significance
        merged['significance_score'] = merged.apply(
            lambda row: calculate_significance_score(
                row['impressions_current'], 
                row['clicks_current']
            ),
            axis=1
        )
        
        # Check for seasonality effects if seasonality analyzer is available
        if self.seasonality_analyzer is not None:
            merged['seasonality_adjusted'] = merged.apply(
                lambda row: self.seasonality_analyzer.is_change_seasonal(
                    row['page'], 
                    row['query'], 
                    row['impressions_change_pct']
                ),
                axis=1
            )
        else:
            merged['seasonality_adjusted'] = False
            
        # Determine if weekend effect (if current period has more weekend days)
        current_weekend_days = sum(detect_is_weekend(date) for date in current_period['date'].unique())
        previous_weekend_days = sum(detect_is_weekend(date) for date in previous_period['date'].unique())
        weekend_effect = current_weekend_days > previous_weekend_days
        
        # Filter for significant changes
        significant_changes = merged[
            (abs(merged['impressions_change_pct']) >= min_change_pct) |
            (abs(merged['clicks_change_pct']) >= min_change_pct)
        ].copy()
        
        # Add change type classification
        significant_changes.loc[:, 'change_type'] = significant_changes.apply(
            lambda row: self._classify_change(
                row['impressions_change'],
                row['clicks_change'],
                row['position_change'],
                row['seasonality_adjusted'],
                weekend_effect
            ),
            axis=1
        )
        
        # Sort by significance and magnitude of change
        significant_changes = significant_changes.sort_values(
            by=['significance_score', 'impressions_change_pct'], 
            ascending=[False, False]
        )
        
        # Clean up and round numeric columns
        for col in significant_changes.select_dtypes(include=['float']).columns:
            if 'pct' in col:
                significant_changes[col] = significant_changes[col].round(1)
            elif 'position' in col:
                significant_changes[col] = significant_changes[col].round(2)
            else:
                significant_changes[col] = significant_changes[col].round(0)
        
        return significant_changes
    
    def _classify_change(self, imp_change, click_change, pos_change, 
                         is_seasonal, weekend_effect):
        """
        Classify the type of traffic change
        
        Args:
            imp_change (float): Impressions change
            click_change (float): Clicks change
            pos_change (float): Position change (negative is improvement)
            is_seasonal (bool): Whether change is due to seasonality
            weekend_effect (bool): Whether weekend effect is present
            
        Returns:
            str: Classification of change type
        """
        # Position improvement
        if pos_change < -0.5 and imp_change > 0:
            return "ranking_improvement"
        
        # Position decline
        elif pos_change > 0.5 and imp_change < 0:
            return "ranking_decline"
        
        # Seasonal change
        elif is_seasonal:
            if imp_change > 0:
                return "seasonal_increase"
            else:
                return "seasonal_decrease"
        
        # Weekend effect
        elif weekend_effect and abs(imp_change) > 0:
            if imp_change > 0:
                return "weekend_increase"
            else:
                return "weekend_decrease"
        
        # CTR improvement
        elif imp_change > 0 and click_change > imp_change * 0.01:  # Clicks increased more than proportionally
            return "ctr_improvement"
        
        # CTR decline
        elif imp_change > 0 and click_change < imp_change * 0.005:  # Clicks increased less than proportionally
            return "ctr_decline"
        
        # General traffic changes
        elif imp_change > 0:
            return "traffic_increase"
        elif imp_change < 0:
            return "traffic_decrease"
        
        # Default
        return "other"