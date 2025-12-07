import pandas as pd
import numpy as np
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
import json
from typing import Dict, List, Tuple
from tqdm import tqdm

class DataLoader:
    def __init__(self, gsc_credentials_path: str = None):
        self.gsc_credentials_path = gsc_credentials_path
        self.gsc_service = None
        
    def init_gsc_service(self):
        """Initialize Google Search Console service"""
        if not self.gsc_credentials_path:
            raise ValueError("GSC credentials path not provided")
        
        # Check if it's a service account or OAuth credentials
        with open(self.gsc_credentials_path, 'r') as f:
            cred_data = json.load(f)
        
        if 'type' in cred_data and cred_data['type'] == 'service_account':
            # Service account
            credentials = service_account.Credentials.from_service_account_file(
                self.gsc_credentials_path,
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
        else:
            # OAuth credentials
            credentials = Credentials.from_authorized_user_file(
                self.gsc_credentials_path,
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
            
        self.gsc_service = build('searchconsole', 'v1', credentials=credentials)
    
    def load_gsc_data(self, site_url: str, days: int = 90) -> pd.DataFrame:
        """Load comprehensive data from Google Search Console API"""
        if not self.gsc_service:
            self.init_gsc_service()
            
        print(f"Loading GSC data for last {days} days...")
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        all_data = []
        
        # Fetch data in chunks to handle API limits
        request = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['page', 'query'],
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'page',
                    'operator': 'notContains',
                    'expression': '#'  # Exclude fragments
                }]
            }],
            'rowLimit': 25000,
            'startRow': 0
        }
        
        while True:
            try:
                response = self.gsc_service.searchanalytics().query(
                    siteUrl=site_url, body=request
                ).execute()
                
                rows = response.get('rows', [])
                if not rows:
                    break
                
                for row in rows:
                    all_data.append({
                        'url': row['keys'][0],
                        'query': row['keys'][1],
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0)
                    })
                
                # Check if there are more rows
                if len(rows) < 25000:
                    break
                    
                request['startRow'] += 25000
                
            except Exception as e:
                print(f"Error fetching GSC data: {e}")
                break
        
        df = pd.DataFrame(all_data)
        
        # Clean URLs
        df['url'] = df['url'].str.replace(site_url, '', regex=False)
        df['url'] = df['url'].apply(lambda x: x if x else '/')
        
        print(f"Loaded {len(df)} query-page combinations from GSC")
        return df
    
    def load_screaming_frog_data(self, filepath: str) -> pd.DataFrame:
        """Load crawl data from Screaming Frog export"""
        print(f"Loading Screaming Frog data from {filepath}...")
        
        # Common column mappings for different SF export types
        column_mapping = {
            'Address': 'url',
            'Title 1': 'title',
            'Title 1 Length': 'title_length',
            'Meta Description 1': 'meta_description',
            'Meta Description 1 Length': 'meta_length',
            'H1-1': 'h1',
            'H2-1': 'h2',
            'Word Count': 'word_count',
            'Status Code': 'status_code',
            'Indexability': 'indexability',
            'Canonical Link Element 1': 'canonical'
        }
        
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
        except:
            df = pd.read_csv(filepath, encoding='utf-16')
        
        # Rename columns if they exist
        df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)
        
        # Filter only indexable HTML pages
        if 'indexability' in df.columns:
            df = df[df['indexability'] == 'Indexable']
        if 'status_code' in df.columns:
            df = df[df['status_code'] == 200]
        
        # Clean URLs to match GSC format
        if 'url' in df.columns:
            df['url'] = df['url'].str.replace('https://', '').str.replace('http://', '')
            df['url'] = df['url'].str.replace('www.example.com', 'example.com')
            df['url'] = df['url'].str.replace('example.com/', '/')
            df['url'] = df['url'].str.replace('example.com', '/')
        
        # Convert numeric columns
        numeric_cols = ['title_length', 'meta_length', 'word_count']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"Loaded {len(df)} pages from Screaming Frog")
        return df
    
    def merge_gsc_screaming_frog(self, gsc_df: pd.DataFrame, sf_df: pd.DataFrame) -> pd.DataFrame:
        """Merge GSC and Screaming Frog data"""
        print("Merging GSC and Screaming Frog data...")
        
        # Aggregate GSC data by URL
        gsc_by_url = gsc_df.groupby('url').agg({
            'query': lambda x: list(x),
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        # Also get top queries by impressions for each URL
        top_queries = gsc_df.sort_values('impressions', ascending=False).groupby('url').agg({
            'query': lambda x: list(x)[:10]  # Top 10 queries
        }).reset_index()
        top_queries.rename(columns={'query': 'top_queries'}, inplace=True)
        
        gsc_by_url = pd.merge(gsc_by_url, top_queries, on='url', how='left')
        
        # Merge with Screaming Frog data
        merged = pd.merge(
            gsc_by_url,
            sf_df,
            on='url',
            how='left',
            suffixes=('_gsc', '_sf')
        )
        
        # Fill missing values
        merged['title'] = merged['title'].fillna('')
        merged['meta_description'] = merged['meta_description'].fillna('')
        merged['h1'] = merged['h1'].fillna('')
        merged['word_count'] = merged['word_count'].fillna(0)
        
        # Calculate additional metrics
        merged['queries_count'] = merged['query'].apply(len)
        merged['avg_query_length'] = merged['query'].apply(
            lambda queries: np.mean([len(q.split()) for q in queries]) if queries else 0
        )
        
        print(f"Merged data contains {len(merged)} URLs")
        return merged
    
    def load_gsc_page_data(self, site_url: str, days: int = 90) -> pd.DataFrame:
        """Load page-level data from GSC (without query dimension)"""
        if not self.gsc_service:
            self.init_gsc_service()
            
        print(f"Loading page-level GSC data...")
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        request = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['page'],
            'rowLimit': 25000
        }
        
        response = self.gsc_service.searchanalytics().query(
            siteUrl=site_url, body=request
        ).execute()
        
        rows = response.get('rows', [])
        data = []
        
        for row in rows:
            data.append({
                'url': row['keys'][0].replace(site_url, ''),
                'clicks_total': row.get('clicks', 0),
                'impressions_total': row.get('impressions', 0),
                'ctr_overall': row.get('ctr', 0),
                'position_overall': row.get('position', 0)
            })
        
        return pd.DataFrame(data)
