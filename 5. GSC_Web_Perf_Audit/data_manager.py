"""
Data Manager for GSC Analyzer
Handles data storage, retrieval, and management
"""
import os
from datetime import datetime, timedelta
import pickle
import pandas as pd
from pathlib import Path

import config
from gsc_connector import GSCConnector

class DataManager:
    """Data Manager for GSC Analyzer"""
    
    def __init__(self):
        self.gsc = GSCConnector()
        
    def historical_data_exists(self):
        """Check if historical data file exists"""
        for file in os.listdir(config.HISTORICAL_DIR):
            if file.startswith("gsc_data_full_"):
                return True
        return False
    
    def get_latest_historical_file(self):
        """Get the path to the latest historical data file"""
        files = [f for f in os.listdir(config.HISTORICAL_DIR) 
                if f.startswith("gsc_data_full_")]
        
        if not files:
            return None
        
        # Sort by timestamp (assuming format gsc_data_full_YYYYMMDD.parquet)
        latest_file = sorted(files, reverse=True)[0]
        return config.HISTORICAL_DIR / latest_file
    
    def historical_data_age(self):
        """Get the age of historical data in days"""
        latest_file = self.get_latest_historical_file()
        if not latest_file:
            return float('inf')  # Very large number to trigger refresh
        
        # Extract date from filename (format: gsc_data_full_YYYYMMDD.parquet)
        filename = os.path.basename(latest_file)
        date_str = filename.replace("gsc_data_full_", "").replace(".parquet", "")
        
        try:
            file_date = datetime.strptime(date_str, "%Y%m%d")
            days_old = (datetime.now() - file_date).days
            return days_old
        except ValueError:
            return float('inf')  # Invalid format, trigger refresh
    
    def load_historical_data(self):
        """Load historical data from file"""
        latest_file = self.get_latest_historical_file()
        if not latest_file:
            return None
        
        try:
            return pd.read_parquet(latest_file)
        except Exception as e:
            print(f"Error loading historical data: {e}")
            return None
    
    def save_historical_data(self, data):
        """Save historical data to file"""
        timestamp = config.get_timestamp()
        filename = config.HISTORICAL_FILENAME_TEMPLATE.format(timestamp)
        filepath = config.HISTORICAL_DIR / filename
        
        # Save as parquet for efficiency
        data.to_parquet(filepath, index=False)
        print(f"Historical data saved to {filepath}")
        
        return filepath
    
    def fetch_and_save_historical_data(self):
        """Fetch historical data and save to file"""
        print("Fetching historical data from Google Search Console...")
        historical_data = self.gsc.fetch_historical_data()
        
        if historical_data.empty:
            print("No historical data retrieved")
            return None
        
        return self.save_historical_data(historical_data)
    
    def recent_data_exists(self, days):
        """
        Check if recent data file for the given number of days already exists for today
        
        Args:
            days (int): Number of days for the recent data
            
        Returns:
            tuple: (exists, filepath) - Whether the data exists and the filepath if it does
        """
        today = datetime.now().strftime("%Y%m%d")
    
        # Look for files with today's date
        for file in os.listdir(config.RECENT_DIR):
            # Check if file matches the pattern: last_Xdays_YYYYMMDD*.parquet
            if file.startswith(f"last_{days}days_{today}") and file.endswith(".parquet"):
                return True, os.path.join(config.RECENT_DIR, file)
        
        return False, None

    def fetch_recent_data(self, days, force_refresh=False):
        """
        Fetch recent data for analysis, or load from cache if available
        
        Args:
            days (int): Number of days to fetch
            force_refresh (bool): Whether to force a refresh of data
        
        Returns:
            pd.DataFrame: Recent data for analysis
        """
        # Check if data for today already exists
        if not force_refresh:
            exists, filepath = self.recent_data_exists(days)
            if exists:
                print(f"Found recent {days}-day data for today. Loading from cache...")
                try:
                    return pd.read_parquet(filepath)
                except Exception as e:
                    print(f"Error loading cached data: {e}")
                    print("Fetching fresh data instead...")
        
        # If no cached data or force refresh, fetch fresh data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        print(f"Fetching recent {days}-day data...")
        
        all_data = []
        for country in config.TARGET_COUNTRIES:
            data = self.gsc.fetch_data_by_chunks(
                start_date=start_str,
                end_date=end_str,
                dimensions=['page', 'query', 'date'],
                country=country
            )
            
            if not data.empty:
                data['country'] = country
                all_data.append(data)
        
        if not all_data:
            print(f"No recent {days}-day data retrieved")
            return None
        
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        # Save the data
        timestamp = config.get_timestamp()
        filename = config.RECENT_FILENAME_TEMPLATE.format(days, timestamp)
        filepath = config.RECENT_DIR / filename
        combined_data.to_parquet(filepath, index=False)
        
        print(f"Recent {days}-day data saved to {filepath}")
        return combined_data
    
    def get_or_fetch_historical_data(self, force_refresh=False):
        """Get historical data, refreshing if needed"""
        if (force_refresh or 
            not self.historical_data_exists() or 
            self.historical_data_age() > config.HISTORICAL_REFRESH_DAYS):
            
            # Confirm refresh with user if data exists but is old
            if (not force_refresh and 
                self.historical_data_exists() and 
                self.historical_data_age() > config.HISTORICAL_REFRESH_DAYS):
                
                refresh = input(f"Historical data is {self.historical_data_age()} days old. Refresh? (y/n): ")
                if refresh.lower() != 'y':
                    print("Using existing historical data...")
                    return self.load_historical_data()
            
            # Fetch fresh data
            return self.fetch_and_save_historical_data()
        
        # Use existing data
        return self.load_historical_data()
    
    def save_seasonality_patterns(self, patterns):
        """Save seasonality patterns to file"""
        timestamp = config.get_timestamp()
        filename = config.SEASONALITY_FILENAME_TEMPLATE.format(timestamp)
        filepath = config.HISTORICAL_DIR / filename
        
        with open(filepath, 'wb') as f:
            pickle.dump(patterns, f)
        
        print(f"Seasonality patterns saved to {filepath}")
        return filepath
    
    def load_latest_seasonality_patterns(self):
        """Load the latest seasonality patterns"""
        files = [f for f in os.listdir(config.HISTORICAL_DIR) 
                if f.startswith("seasonality_patterns_")]
        
        if not files:
            return None
        
        # Sort by timestamp
        latest_file = sorted(files, reverse=True)[0]
        filepath = config.HISTORICAL_DIR / latest_file
        
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading seasonality patterns: {e}")
            return None