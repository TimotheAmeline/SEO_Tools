"""
Keyword Trend Analyzer
Detects rising and declining keywords
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .utils import calculate_significance_score, filter_significant_data
import config

class KeywordTrendAnalyzer:
    """Analyzer for keyword trends"""
    
    def __init__(self, historical_data=None, seasonality_analyzer=None):
        """
        Initialize the analyzer
        
        Args:
            historical_data (pd.DataFrame, optional): Historical GSC data
            seasonality_analyzer (SeasonalityAnalyzer, optional): Seasonality analyzer
        """
        self.historical_data = historical_data
        self.seasonality_analyzer = seasonality_analyzer
    
    def analyze(self, recent_data, min_impressions=None, trend_period_days=30,
                min_change_pct=20, min_significance=5):
        """
        Analyze keyword trends to find rising and declining queries
        
        Args:
            recent_data (pd.DataFrame): Recent GSC data
            min_impressions (int, optional): Minimum impressions threshold
            trend_period_days (int): Number of days to analyze trends
            min_change_pct (float): Minimum percentage change to be significant
            min_significance (float): Minimum significance score
            
        Returns:
            tuple: (rising_keywords_df, declining_keywords_df)
        """
        if recent_data is None or recent_data.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        if self.historical_data is None or self.historical_data.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        if min_impressions is None:
            min_impressions = config.MIN_IMPRESSIONS
        
        # Determine date ranges
        max_date = recent_data['date'].max()
        current_start_date = max_date - timedelta(days=trend_period_days)
        previous_start_date = current_start_date - timedelta(days=trend_period_days)
        
        # Filter data for current and previous periods
        current_period = recent_data[recent_data['date'] >= current_start_date]
        previous_period = self.historical_data[
            (self.historical_data['date'] >= previous_start_date) &
            (self.historical_data['date'] < current_start_date)
        ]
        
        # Filter for significant data
        current_period = filter_significant_data(current_period, min_impressions=min_impressions)
        previous_period = filter_significant_data(previous_period, min_impressions=min_impressions)
        
        # Group by query and aggregate metrics
        current_queries = current_period.groupby('query').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'position': 'mean',
            'page': lambda x: x.value_counts().index[0]  # Top page for this query
        }).reset_index()
        
        previous_queries = previous_period.groupby('query').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'position': 'mean',
            'page': lambda x: x.value_counts().index[0]  # Top page for this query
        }).reset_index()
        
        # Merge periods
        merged = pd.merge(
            current_queries,
            previous_queries,
            on=['query'],
            how='outer',
            suffixes=('_current', '_previous')
        )
        
        # Fill NaN values with 0 for new or disappeared queries
        for col in ['impressions_current', 'clicks_current', 
                    'impressions_previous', 'clicks_previous']:
            merged[col] = merged[col].fillna(0)
        
        # Calculate changes
        merged['impressions_change'] = merged['impressions_current'] - merged['impressions_previous']
        merged['impressions_change_pct'] = merged.apply(
            lambda row: (row['impressions_change'] / row['impressions_previous'] * 100)
            if row['impressions_previous'] > 0 else
            (100 if row['impressions_current'] > 0 else 0),
            axis=1
        )
        
        merged['clicks_change'] = merged['clicks_current'] - merged['clicks_previous']
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
        
        # Calculate significance score
        merged['significance_score'] = merged.apply(
            lambda row: calculate_significance_score(
                row['impressions_current'],
                row['clicks_current']
            ),
            axis=1
        )
        
        # Check for seasonality if analyzer is available
        if self.seasonality_analyzer is not None:
            merged['is_seasonal'] = merged.apply(
                lambda row: self.seasonality_analyzer.is_change_seasonal(
                    row.get('page_current', row.get('page_previous', '')),
                    row['query'],
                    row['impressions_change_pct']
                ),
                axis=1
            )
        else:
            merged['is_seasonal'] = False
        
        # Determine if keyword is new (no previous impressions)
        merged['is_new'] = merged['impressions_previous'] == 0
        
        # Determine if keyword is lost (no current impressions)
        merged['is_lost'] = merged['impressions_current'] == 0
        
        # Filter for significant rising keywords
        rising_keywords = merged[
            (merged['impressions_change_pct'] >= min_change_pct) &
            (merged['impressions_current'] >= min_impressions) &
            (merged['significance_score'] >= min_significance) #&
            #(~merged['is_seasonal'])  # Not due to seasonality
        ].copy()
        
        # Filter for significant declining keywords
        declining_keywords = merged[
            (merged['impressions_change_pct'] <= -min_change_pct) &
            (merged['impressions_previous'] >= min_impressions) &
            (merged['significance_score'] >= min_significance) #&
            #(~merged['is_seasonal'])  # Not due to seasonality
        ].copy()
        
        # Add opportunity score for rising keywords
        rising_keywords['opportunity_score'] = rising_keywords.apply(
            lambda row: self._calculate_opportunity_score(
                row['impressions_current'],
                row['clicks_current'],
                row['impressions_change_pct'],
                row['position_current'] if not pd.isna(row['position_current']) else 100,
                row['is_new']
            ),
            axis=1
        )
        
        # Add risk score for declining keywords
        declining_keywords['risk_score'] = declining_keywords.apply(
            lambda row: self._calculate_risk_score(
                row['impressions_previous'],
                row['clicks_previous'],
                abs(row['impressions_change_pct']),
                row['is_lost']
            ),
            axis=1
        )
        
        # Sort by scores
        rising_keywords = rising_keywords.sort_values(
            by=['opportunity_score'], ascending=False
        )
        
        declining_keywords = declining_keywords.sort_values(
            by=['risk_score'], ascending=False
        )
        
        # Clean up and round numeric columns
        for df in [rising_keywords, declining_keywords]:
            for col in df.select_dtypes(include=['float']).columns:
                if 'pct' in col:
                    df[col] = df[col].round(1)
                elif 'position' in col:
                    df[col] = df[col].round(2)
                elif 'score' in col:
                    df[col] = df[col].round(1)
                else:
                    df[col] = df[col].round(0)
        
        return rising_keywords, declining_keywords
    
    def _calculate_opportunity_score(self, impressions, clicks, change_pct, position, is_new):
        """
        Calculate opportunity score for rising keywords
        
        Args:
            impressions (int): Current impressions
            clicks (int): Current clicks 
            change_pct (float): Percentage change in impressions
            position (float): Current position
            is_new (bool): Whether this is a new keyword
            
        Returns:
            float: Opportunity score (0-100)
        """
        # Base score on significance
        base_score = calculate_significance_score(impressions, clicks)
        
        # Adjust for growth rate (higher growth = more opportunity)
        growth_factor = min(2.0, 1.0 + (change_pct / 100))
        
        # Adjust for position (higher positions have less room to grow)
        position_factor = 1.0
        if position <= 10:
            position_factor = 0.7 + (0.3 * position / 10)  # 0.7-1.0 for pos 1-10
        elif position <= 20:
            position_factor = 1.0 + ((position - 10) / 10) * 0.5  # 1.0-1.5 for pos 11-20
        else:
            position_factor = 1.5  # More opportunity for keywords beyond page 2
        
        # Bonus for new keywords
        new_bonus = 1.3 if is_new else 1.0
        
        # Combine factors
        opportunity_score = base_score * growth_factor * position_factor * new_bonus
        
        return min(100, opportunity_score)
    
    def _calculate_risk_score(self, impressions, clicks, change_pct, is_lost):
        """
        Calculate risk score for declining keywords
        
        Args:
            impressions (int): Previous impressions
            clicks (int): Previous clicks
            change_pct (float): Absolute percentage change in impressions
            is_lost (bool): Whether this keyword is completely lost
            
        Returns:
            float: Risk score (0-100)
        """
        # Base score on significance
        base_score = calculate_significance_score(impressions, clicks)
        
        # Adjust for decline rate (steeper decline = higher risk)
        decline_factor = min(2.0, 1.0 + (change_pct / 100))
        
        # Extra risk for completely lost keywords
        lost_penalty = 1.5 if is_lost else 1.0
        
        # Combine factors
        risk_score = base_score * decline_factor * lost_penalty
        
        return min(100, risk_score)