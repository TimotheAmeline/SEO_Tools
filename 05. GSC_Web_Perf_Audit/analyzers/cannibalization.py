"""
Cannibalization Detector
Identifies potential keyword cannibalization issues
"""
import pandas as pd
import numpy as np
import config

class CannibalizationDetector:
    """Detector for keyword cannibalization issues"""
    
    def __init__(self, historical_data=None):
        """
        Initialize the detector
        
        Args:
            historical_data (pd.DataFrame, optional): Historical GSC data
        """
        self.historical_data = historical_data
    
    def analyze(self, recent_data, min_impressions=None, ranking_volatility_threshold=2.0):
        """
        Analyze potential cannibalization issues
        
        Args:
            recent_data (pd.DataFrame): Recent GSC data
            min_impressions (int, optional): Minimum impressions threshold
            ranking_volatility_threshold (float): Threshold for position volatility
            
        Returns:
            pd.DataFrame: Detected cannibalization issues
        """
        if recent_data is None or recent_data.empty:
            return pd.DataFrame()
        
        if min_impressions is None:
            min_impressions = config.MIN_IMPRESSIONS
        
        # Filter for queries with multiple ranking URLs
        query_url_counts = recent_data.groupby('query')['page'].nunique()
        multi_page_queries = query_url_counts[query_url_counts > 1].index.tolist()
        
        if not multi_page_queries:
            return pd.DataFrame()
        
        # Filter data for these queries
        cannibalization_data = recent_data[recent_data['query'].isin(multi_page_queries)]
        
        # Group by query and page
        grouped = cannibalization_data.groupby(['query', 'page']).agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'position': ['mean', 'std'],  # Average position and standard deviation
            'date': ['min', 'max', 'count']  # Date range and number of days
        })
        
        # Flatten the column multi-index
        grouped.columns = ['_'.join(col).strip() for col in grouped.columns.values]
        grouped = grouped.reset_index()
        
        # Filter for significant pages
        grouped = grouped[grouped['impressions_sum'] >= min_impressions]
        
        # Identify queries with enough data
        valid_queries = grouped.groupby('query').filter(
            lambda x: len(x) > 1 and x['impressions_sum'].sum() >= min_impressions * 2
        )['query'].unique()
        
        if len(valid_queries) == 0:
            return pd.DataFrame()
        
        # Prepare cannibalization results
        results = []
        
        for query in valid_queries:
            query_data = grouped[grouped['query'] == query].copy()
            
            # Skip if only one page left after filtering
            if len(query_data) < 2:
                continue
            
            # Calculate total impressions for this query
            total_impressions = query_data['impressions_sum'].sum()
            
            # Calculate ranking volatility (position std)
            query_data['ranking_volatility'] = query_data['position_std']
            
            # Identify the "primary" page (best position)
            primary_page = query_data.loc[query_data['position_mean'].idxmin(), 'page']
            
            # Calculate cannibalization metrics
            query_data['primary_page'] = primary_page
            query_data['is_primary'] = query_data['page'] == primary_page
            query_data['impression_share'] = (query_data['impressions_sum'] / total_impressions) * 100
            
            # Determine cannibalization severity
            has_volatility = any(query_data['ranking_volatility'] > ranking_volatility_threshold)
            has_close_positions = query_data['position_mean'].max() - query_data['position_mean'].min() < 5
            
            for _, row in query_data.iterrows():
                severity = 0
                
                # Volatility in rankings suggests cannibalization
                if row['ranking_volatility'] > ranking_volatility_threshold:
                    severity += 1
                
                # Similar positions for multiple pages suggests cannibalization
                if has_close_positions:
                    severity += 1
                
                # Non-primary page getting significant impressions
                if not row['is_primary'] and row['impression_share'] > 25:
                    severity += 1
                
                # Only include if some severity detected
                if severity > 0:
                    results.append({
                        'query': query,
                        'page': row['page'],
                        'is_primary': row['is_primary'],
                        'primary_page': primary_page,
                        'position': row['position_mean'],
                        'position_volatility': row['ranking_volatility'],
                        'impressions': row['impressions_sum'],
                        'clicks': row['clicks_sum'],
                        'impression_share': row['impression_share'],
                        'severity': severity,
                        'days_in_serp': row['date_count']
                    })
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        
        # Sort by query and severity
        results_df = results_df.sort_values(
            by=['query', 'severity', 'position'],
            ascending=[True, False, True]
        )
        
        # Clean up and round numeric columns
        for col in results_df.select_dtypes(include=['float']).columns:
            if col in ['position', 'position_volatility']:
                results_df[col] = results_df[col].round(2)
            elif col == 'impression_share':
                results_df[col] = results_df[col].round(1)
            else:
                results_df[col] = results_df[col].round(0)
        
        return results_df