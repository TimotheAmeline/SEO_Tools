"""
Google Search Console API connector
Handles authentication and data retrieval
"""
import os
import sys
import time
from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
from googleapiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from oauth2client.tools import run_flow
from oauth2client.service_account import ServiceAccountCredentials

import config

class GSCConnector:
    """Google Search Console API connector"""
    
    def __init__(self):
        """
        Initialize the connector
        """
        self.site_url = config.SITE_URL
        self.credentials = self._authenticate()
        self.service = self._build_service()
    
    def _authenticate(self):
        """Authenticate with Google Search Console API"""
        if hasattr(config, 'USE_SERVICE_ACCOUNT') and config.USE_SERVICE_ACCOUNT:
            return self._authenticate_service_account()
        else:
            return self._authenticate_oauth()

    def _authenticate_service_account(self):
        """Authenticate using a service account"""
        # Check if service account file exists
        if not os.path.exists(config.GSC_SERVICE_ACCOUNT_FILE):
            print(f"Error: {config.GSC_SERVICE_ACCOUNT_FILE} not found!")
            print("Please place your service account JSON key file in the project directory.")
            sys.exit(1)
            
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                config.GSC_SERVICE_ACCOUNT_FILE,
                scopes=config.GSC_SCOPES
            )
            
            print("Service account authentication successful!")
            return credentials
            
        except Exception as e:
            print(f"Service account authentication error: {e}")
            print("\nPlease ensure your service_account.json file is valid and has the correct permissions.")
            sys.exit(1)

    def _authenticate_oauth(self):
        """Authenticate using OAuth flow"""
        # Check if client_secrets.json exists
        if not os.path.exists(config.GSC_CLIENT_SECRETS_FILE):
            print(f"Error: {config.GSC_CLIENT_SECRETS_FILE} not found!")
            print("Please follow the setup instructions in SETUP.md to create and download your credentials.")
            sys.exit(1)
            
        # Check if credentials already exist
        storage = Storage(config.GSC_CREDENTIALS_FILE)
        credentials = storage.get()
        
        # If credentials don't exist or are invalid, run the auth flow
        if not credentials or credentials.invalid:
            # Set up the OAuth flow
            try:
                flow = OAuth2WebServerFlow.from_client_secrets_file(
                    config.GSC_CLIENT_SECRETS_FILE,
                    scope=config.GSC_SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                )
                
                print("\nAuthorization required:")
                print("A browser window should open. Please authorize the application.")
                print("If no browser opens, go to this URL manually:")
                
                # Run the flow
                credentials = run_flow(flow, storage)
                print("Authorization successful! Credentials saved for future use.")
                
            except Exception as e:
                print(f"Authentication error: {e}")
                print("\nPlease ensure your client_secrets.json file is valid and try again.")
                sys.exit(1)
        
        return credentials
    
    def _build_service(self):
        """Build the Search Console service"""
        return build(
            'webmasters',
            'v3',
            credentials=self.credentials
        )
    
    def execute_request(self, request):
        """Execute a request with retry logic for API quotas"""
        try:
            return request.execute()
        except Exception as e:
            if "quota" in str(e).lower():
                print("API quota exceeded. Waiting 60 seconds before retrying...")
                time.sleep(60)
                return request.execute()
            else:
                raise e
    
    def fetch_search_data(self, start_date, end_date, dimensions=None, 
                         row_limit=25000, country=None):
        """
        Fetch search analytics data from GSC
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            dimensions (list): List of dimensions (e.g., ['page', 'query'])
            row_limit (int): Max rows to return per request
            country (str): Country filter (e.g., 'usa')
            
        Returns:
            pd.DataFrame: Dataframe with search analytics data
        """
        if dimensions is None:
            dimensions = ['page', 'query', 'date']
        
        # Prepare the request
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dimensions,
            'rowLimit': row_limit,
            'searchType': 'web'
        }
        
        # Add country filter if specified
        if country:
            request_body['dimensionFilterGroups'] = [{
                'filters': [{
                    'dimension': 'country',
                    'expression': country
                }]
            }]
        
        # Execute the request
        request = self.service.searchanalytics().query(
            siteUrl=self.site_url,
            body=request_body
        )
        response = self.execute_request(request)
        
        # Check if we got any data
        if 'rows' not in response:
            return pd.DataFrame(columns=dimensions + ['clicks', 'impressions', 'ctr', 'position'])
        
        # Convert to DataFrame
        data = []
        for row in response['rows']:
            record = {}
            # Add dimensions
            for i, dimension in enumerate(dimensions):
                record[dimension] = row['keys'][i]
            
            # Add metrics
            record['clicks'] = row['clicks']
            record['impressions'] = row['impressions']
            record['ctr'] = row['ctr']
            record['position'] = row['position']
            
            data.append(record)
        
        return pd.DataFrame(data)
    
    def fetch_data_by_chunks(self, start_date, end_date, dimensions=None, country=None):
        """
        Fetch data in chunks by date ranges to avoid exceeding API limits
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            dimensions (list): List of dimensions
            country (str): Country filter
            
        Returns:
            pd.DataFrame: Combined dataframe with all data
        """
        if dimensions is None:
            dimensions = ['page', 'query', 'date']
        
        # Convert string dates to datetime
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Calculate total days and create chunks
        total_days = (end_dt - start_dt).days + 1
        chunk_size = 7  # Fetch 7 days at a time to avoid quota issues
        chunks = [
            (start_dt + timedelta(days=i), 
             min(start_dt + timedelta(days=i+chunk_size-1), end_dt))
            for i in range(0, total_days, chunk_size)
        ]
        
        all_data = []
        for start_chunk, end_chunk in tqdm(chunks, desc=f"Fetching GSC data for {country or 'all countries'}"):
            # Format dates as strings for the API
            chunk_start = start_chunk.strftime('%Y-%m-%d')
            chunk_end = end_chunk.strftime('%Y-%m-%d')
            
            # Fetch data for the chunk
            chunk_data = self.fetch_search_data(
                start_date=chunk_start,
                end_date=chunk_end,
                dimensions=dimensions,
                country=country
            )
            
            if not chunk_data.empty:
                all_data.append(chunk_data)
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        # Combine all chunks
        if not all_data:
            return pd.DataFrame(columns=dimensions + ['clicks', 'impressions', 'ctr', 'position'])
        
        return pd.concat(all_data, ignore_index=True)
    
    def fetch_historical_data(self, days=None, countries=None):
        """
        Fetch historical data for all specified countries
        
        Args:
            days (int): Number of days to fetch (default: config.MAX_HISTORICAL_DAYS)
            countries (list): List of country codes (default: config.TARGET_COUNTRIES)
            
        Returns:
            pd.DataFrame: Combined dataframe with all historical data
        """
        if days is None:
            days = config.MAX_HISTORICAL_DAYS
        
        if countries is None:
            countries = config.TARGET_COUNTRIES
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Format dates as strings
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        all_data = []
        
        # Fetch data for each country
        for country in countries:
            country_data = self.fetch_data_by_chunks(
                start_date=start_str,
                end_date=end_str,
                dimensions=['page', 'query', 'date'],
                country=country
            )
            
            if not country_data.empty:
                # Add country column
                country_data['country'] = country
                all_data.append(country_data)
        
        # Combine all data
        if not all_data:
            return pd.DataFrame(columns=['page', 'query', 'date', 'country', 
                                         'clicks', 'impressions', 'ctr', 'position'])
        
        combined_data = pd.concat(all_data, ignore_index=True)
        
        # Convert date strings to datetime
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        return combined_data