"""
Utility functions for analysis modules
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from statsmodels.tsa.seasonal import seasonal_decompose
import config

def calculate_significance_score(impressions, clicks, baseline=None):
    """
    Calculate business significance score based on volume
    
    Args:
        impressions (int): Number of impressions
        clicks (int): Number of clicks
        baseline (dict, optional): Baseline metrics for comparison
        
    Returns:
        float: Significance score (0-100)
    """
    # Base significance on log scale of impressions and clicks
    # This prioritizes high-volume pages/queries
    if impressions <= 0:
        return 0
    
    # Log scale for impressions (1-10 impressions → low score, 1000+ → high score)
    imp_score = min(100, max(0, 20 * np.log10(impressions)))
    
    # Click contribution - even more valuable
    click_score = min(100, max(0, 25 * np.log10(clicks + 1)))
    
    # Combine scores (weighted average)
    combined_score = (imp_score * 0.4) + (click_score * 0.6)
    
    # If baseline available, adjust based on relative performance
    if baseline and isinstance(baseline, dict):
        rel_factor = 1.0  # Default no adjustment
        
        # Example: adjust by % difference from baseline
        if 'avg_impressions' in baseline and baseline['avg_impressions'] > 0:
            imp_factor = impressions / baseline['avg_impressions']
            rel_factor *= min(2.0, max(0.5, imp_factor))
            
        combined_score *= rel_factor
    
    return min(100, combined_score)

def filter_significant_data(df, min_impressions=None, min_clicks=None):
    """
    Filter data to only include rows with significant metrics
    
    Args:
        df (pd.DataFrame): DataFrame to filter
        min_impressions (int, optional): Minimum impressions threshold
        min_clicks (int, optional): Minimum clicks threshold
        
    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    if min_impressions is None:
        min_impressions = config.MIN_IMPRESSIONS
        
    if min_clicks is None:
        min_clicks = config.MIN_CLICKS
    
    # Basic threshold filtering
    filtered = df.copy()
    filtered = filtered[filtered['impressions'] >= min_impressions]
    
    return filtered

def get_expected_ctr_for_position(position):
    """
    Get expected CTR for a given position based on baseline data
    
    Args:
        position (float): Average position
        
    Returns:
        float: Expected CTR for that position
    """
    # Round position to nearest integer (or use float index if available)
    pos_int = round(position)
    
    # Get from config or use exponential decay model if position not in config
    if pos_int in config.CTR_POSITION_BASELINE:
        return config.CTR_POSITION_BASELINE[pos_int]
    elif pos_int < 1:
        return 0.25  # Edge case: position < 1 (rare)
    else:
        # Exponential decay model for positions beyond our config
        return 0.20 * (0.70 ** (pos_int - 1))

def detect_is_weekend(date):
    """Check if a date is a weekend day"""
    if isinstance(date, str):
        date = pd.to_datetime(date)
    return date.weekday() >= 5  # 5=Saturday, 6=Sunday

def group_data_by_time_period(df, period='daily'):
    """
    Group data by time period
    
    Args:
        df (pd.DataFrame): DataFrame with 'date' column
        period (str): 'daily', 'weekly', or 'monthly'
        
    Returns:
        pd.DataFrame: Grouped DataFrame
    """
    # Ensure date is datetime type
    if df.empty:
        return df
        
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Create period groupers
    if period == 'weekly':
        df['period'] = df['date'].dt.to_period('W').astype(str)
    elif period == 'monthly':
        df['period'] = df['date'].dt.to_period('M').astype(str)
    else:  # daily
        df['period'] = df['date']
    
    return df

def detect_seasonal_pattern(time_series, period=7):
    """
    Detect if a time series has a seasonal pattern
    
    Args:
        time_series (pd.Series): Time series data
        period (int): Seasonality period to check (7=weekly, 30=monthly)
        
    Returns:
        tuple: (has_seasonality, seasonal_components, strength)
    """
    if len(time_series) < period * 2:
        return False, None, 0
    
    try:
        # Apply seasonal decomposition
        decomposition = seasonal_decompose(
            time_series, 
            model='additive', 
            period=period,
            extrapolate_trend='freq'
        )
        
        # Get components
        trend = decomposition.trend
        seasonal = decomposition.seasonal
        residual = decomposition.resid
        
        # Calculate strength of seasonality
        # (variance of seasonality / variance of seasonality + residual)
        var_seasonal = np.nanvar(seasonal)
        var_residual = np.nanvar(residual)
        
        if var_seasonal + var_residual > 0:
            strength = var_seasonal / (var_seasonal + var_residual)
        else:
            strength = 0
            
        # Determine if seasonal pattern exists
        has_seasonality = strength > 0.3  # Threshold for significance
        
        return has_seasonality, decomposition, strength
        
    except Exception as e:
        print(f"Error detecting seasonality: {e}")
        return False, None, 0