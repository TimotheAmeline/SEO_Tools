"""
Configuration settings for the GSC Analyzer
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
HISTORICAL_DIR = DATA_DIR / "historical"
RECENT_DIR = DATA_DIR / "recent"

# Create directories if they don't exist
for dir_path in [DATA_DIR, HISTORICAL_DIR, RECENT_DIR]:
    dir_path.mkdir(exist_ok=True)

# GSC API Configuration
USE_SERVICE_ACCOUNT = True  # Set to True if using a service account
GSC_SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
GSC_CLIENT_SECRETS_FILE = BASE_DIR / 'client_secrets.json'  # For OAuth
GSC_CREDENTIALS_FILE = BASE_DIR / 'credentials.json'  # For OAuth
GSC_SERVICE_ACCOUNT_FILE = BASE_DIR / 'service_account.json'  # For service account

# Default site URL - replace with your property
SITE_URL = 'sc-domain:example.com'  # Update this with your actual site

# Data timeframes
MAX_HISTORICAL_DAYS = 16 * 30  # Approximately 16 months
HISTORICAL_REFRESH_DAYS = 30  # Refresh historical data after this many days
RECENT_SHORT_DAYS = 7  # For very recent analysis
RECENT_MEDIUM_DAYS = 30  # For medium-term analysis

# Analysis parameters
SIGNIFICANCE_THRESHOLD = 0.05  # p-value threshold for statistical tests
MIN_IMPRESSIONS = 10  # Minimum impressions to consider for analysis
MIN_CLICKS = 3  # Minimum clicks to consider for analysis
CTR_POSITION_BASELINE = {  # Expected CTR by position (you can refine these)
    1: 0.20, 2: 0.10, 3: 0.06, 4: 0.04, 5: 0.03,
    6: 0.02, 7: 0.015, 8: 0.01, 9: 0.008, 10: 0.005
}

# Target countries (add/remove as needed)
TARGET_COUNTRIES = [
    'usa',  # United States
    'gbr',  # United Kingdom 
    'ind',  # India
    #'can',  # Canada
    #'aus',  # Australia
]

# Data storage settings
HISTORICAL_FILENAME_TEMPLATE = "gsc_data_full_{}.parquet"
SEASONALITY_FILENAME_TEMPLATE = "seasonality_patterns_{}.pkl"
BASELINE_FILENAME_TEMPLATE = "baseline_metrics_{}.pkl"
RECENT_FILENAME_TEMPLATE = "last_{}days_{}.parquet"

def get_timestamp():
    """Generate a timestamp string for filenames"""
    return datetime.now().strftime("%Y%m%d")