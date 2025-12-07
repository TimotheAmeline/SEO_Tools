"""
Seasonality Analyzer
Detects seasonal patterns in Search Console data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
from pathlib import Path  # Add this import
from .utils import (
    group_data_by_time_period,
    detect_seasonal_pattern,
    detect_is_weekend
)
import config

class SeasonalityAnalyzer:
    """Analyzer for seasonal patterns in GSC data"""
    
    def __init__(self, historical_data=None):
        """
        Initialize the analyzer
        
        Args:
            historical_data (pd.DataFrame, optional): Historical GSC data
        """
        self.historical_data = historical_data
        self.seasonal_patterns = {}
        self.page_query_patterns = {}
        self.day_of_week_patterns = {}
    
    def analyze(self, min_data_points=60):
        """
        Analyze seasonal patterns in the historical data
    
        Args:
            min_data_points (int): Minimum number of data points required
        
        Returns:
            dict: Dictionary of detected seasonal patterns
        """
        # Initialize results dictionary
        results = {
            'weekly_patterns': {},
            'monthly_patterns': {},
            'page_query_patterns': {},
            'day_of_week_patterns': {}
        }
        
        # Check if historical_data is a Path object instead of DataFrame
        if isinstance(self.historical_data, (str, Path)):
            try:
                print(f"Loading historical data from path: {self.historical_data}")
                self.historical_data = pd.read_parquet(self.historical_data)
            except Exception as e:
                print(f"Error loading historical data from path: {e}")
                return results
    
        if self.historical_data is None or not isinstance(self.historical_data, pd.DataFrame) or self.historical_data.empty:
            print("No valid historical data available for seasonality analysis.")
            return results
        
        if len(self.historical_data) < min_data_points:
            print(f"Insufficient data points for seasonality analysis. Need at least {min_data_points}, but got {len(self.historical_data)}.")
            return results
        
        # Ensure date is datetime
        data = self.historical_data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data['date']):
            data['date'] = pd.to_datetime(data['date'])
        
        # Add day of week
        data['day_of_week'] = data['date'].dt.dayofweek
        data['is_weekend'] = data['day_of_week'].apply(lambda x: x >= 5)
        
        # === 1. Overall site patterns ===
        daily_data = data.groupby('date').agg({
            'impressions': 'sum',
            'clicks': 'sum'
        }).reset_index()
        
        # Check for weekly seasonality
        impressions_series = daily_data.set_index('date')['impressions']
        clicks_series = daily_data.set_index('date')['clicks']
        
        weekly_imp_seasonal, weekly_imp_decomp, weekly_imp_strength = detect_seasonal_pattern(
            impressions_series, period=7
        )
        
        weekly_clicks_seasonal, weekly_clicks_decomp, weekly_clicks_strength = detect_seasonal_pattern(
            clicks_series, period=7
        )
        
        # Store results
        results['weekly_patterns']['impressions'] = {
            'has_seasonality': weekly_imp_seasonal,
            'strength': weekly_imp_strength,
            'pattern': weekly_imp_decomp.seasonal.tolist() if weekly_imp_seasonal else None
        }
        
        results['weekly_patterns']['clicks'] = {
            'has_seasonality': weekly_clicks_seasonal,
            'strength': weekly_clicks_strength,
            'pattern': weekly_clicks_decomp.seasonal.tolist() if weekly_clicks_seasonal else None
        }
        
        # === 2. Monthly patterns ===
        if len(impressions_series) >= 60:  # Need at least 60 days for monthly
            monthly_imp_seasonal, monthly_imp_decomp, monthly_imp_strength = detect_seasonal_pattern(
                impressions_series, period=30
            )
            
            monthly_clicks_seasonal, monthly_clicks_decomp, monthly_clicks_strength = detect_seasonal_pattern(
                clicks_series, period=30
            )
            
            results['monthly_patterns']['impressions'] = {
                'has_seasonality': monthly_imp_seasonal,
                'strength': monthly_imp_strength,
                'pattern': monthly_imp_decomp.seasonal.tolist() if monthly_imp_seasonal else None
            }
            
            results['monthly_patterns']['clicks'] = {
                'has_seasonality': monthly_clicks_seasonal,
                'strength': monthly_clicks_strength,
                'pattern': monthly_clicks_decomp.seasonal.tolist() if monthly_clicks_seasonal else None
            }
        
        # === 3. Day of week patterns ===
        dow_patterns = data.groupby('day_of_week').agg({
            'impressions': 'sum',
            'clicks': 'sum'
        })
        
        # Calculate relative strength by day of week
        total_imp = dow_patterns['impressions'].sum()
        total_clicks = dow_patterns['clicks'].sum()
        
        dow_patterns['imp_ratio'] = dow_patterns['impressions'] / (total_imp / 7)
        dow_patterns['clicks_ratio'] = dow_patterns['clicks'] / (total_clicks / 7)
        
        results['day_of_week_patterns'] = dow_patterns.to_dict()
        self.day_of_week_patterns = dow_patterns.to_dict()
        
        # === 4. Page/query specific patterns ===
        # Group by page, query, and date
        top_combos = data.groupby(['page', 'query']).agg({
            'impressions': 'sum'
        }).reset_index().sort_values('impressions', ascending=False).head(100)
        
        # For each top page/query combo, check for seasonality
        for _, row in top_combos.iterrows():
            page = row['page']
            query = row['query']
            
            # Get time series for this page/query
            page_query_data = data[(data['page'] == page) & (data['query'] == query)]
            
            if len(page_query_data) < 30:  # Skip if not enough data
                continue
                
            # Create time series
            page_query_ts = page_query_data.groupby('date').agg({
                'impressions': 'sum',
                'clicks': 'sum'
            })
            
            # Check for weekly seasonality
            weekly_pq_seasonal, _, weekly_pq_strength = detect_seasonal_pattern(
                page_query_ts['impressions'], period=7
            )
            
            if weekly_pq_seasonal:
                key = (page, query)
                self.page_query_patterns[key] = {
                    'has_seasonality': True,
                    'strength': weekly_pq_strength,
                    'avg_impressions': page_query_ts['impressions'].mean(),
                    'day_of_week_pattern': page_query_data.groupby('day_of_week')['impressions'].mean().to_dict()
                }
                
                results['page_query_patterns'][f"{page}|{query}"] = self.page_query_patterns[key]
        
        # Save the patterns for later use
        self.seasonal_patterns = results
        return results
    
    def is_change_seasonal(self, page, query, change_pct):
        """
        Check if a traffic change is likely due to seasonality
        
        Args:
            page (str): Page URL
            query (str): Query string
            change_pct (float): Percentage change
            
        Returns:
            bool: True if change is likely seasonal
        """
        # If we have page/query specific pattern, use that
        key = (page, query)
        if key in self.page_query_patterns:
            pattern = self.page_query_patterns[key]
            if pattern['has_seasonality'] and pattern['strength'] > 0.4:
                return True
        
        # Check if today is a weekend and we have strong weekend patterns
        today = datetime.now()
        is_weekend_today = detect_is_weekend(today)
        
        if is_weekend_today and self.day_of_week_patterns:
            try:
                imp_ratio = self.day_of_week_patterns['imp_ratio'].get(today.weekday(), 1.0)
                if (imp_ratio < 0.7 and change_pct < 0) or (imp_ratio > 1.3 and change_pct > 0):
                    return True
            except (KeyError, AttributeError):
                pass
        
        # Otherwise, check overall patterns
        if self.seasonal_patterns and 'weekly_patterns' in self.seasonal_patterns:
            weekly = self.seasonal_patterns['weekly_patterns']
            if ('impressions' in weekly and 
                weekly['impressions']['has_seasonality'] and 
                weekly['impressions']['strength'] > 0.3):
                return True
        
        return False
    
    def get_expected_seasonal_adjustment(self, date=None):
        """
        Get expected seasonal adjustment factor for a given date
        
        Args:
            date (datetime, optional): Date to check (default: today)
            
        Returns:
            float: Expected adjustment factor (1.0 = no adjustment)
        """
        if date is None:
            date = datetime.now()
            
        if not self.seasonal_patterns:
            return 1.0
            
        # Check day of week patterns
        day_of_week = date.weekday()
        
        if self.day_of_week_patterns and 'imp_ratio' in self.day_of_week_patterns:
            try:
                return self.day_of_week_patterns['imp_ratio'].get(day_of_week, 1.0)
            except (KeyError, AttributeError):
                pass
        
        # Otherwise, check weekly patterns
        if ('weekly_patterns' in self.seasonal_patterns and 
            'impressions' in self.seasonal_patterns['weekly_patterns'] and
            self.seasonal_patterns['weekly_patterns']['impressions']['has_seasonality']):
            
            pattern = self.seasonal_patterns['weekly_patterns']['impressions']['pattern']
            if pattern:
                day_idx = day_of_week % len(pattern)
                return 1.0 + pattern[day_idx] / 100.0
        
        return 1.0