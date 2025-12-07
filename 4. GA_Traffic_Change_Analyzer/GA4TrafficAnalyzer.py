#!/usr/bin/env python3
"""
GA4 Traffic Comparison Export Script (Simplified)
Works with current GA4 API versions
"""

import csv
import json
import os
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Dimension,
    Metric,
    DateRange,
)
from google.oauth2.service_account import Credentials
import argparse
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class GA4Exporter:
    def __init__(self, property_id, credentials_path):
        """Initialize GA4 exporter"""
        self.property_id = property_id
        logging.info(f"🔑 Loading credentials from: {credentials_path}")
        self.credentials = Credentials.from_service_account_file(credentials_path)
        logging.info(f"📊 Connecting to GA4 property: {property_id}")
        self.client = BetaAnalyticsDataClient(credentials=self.credentials)
        logging.info("✅ GA4 client initialized successfully")
    
    def get_traffic_comparison(self, start_date1, end_date1, start_date2, end_date2, channels=None):
        """Get traffic data with date and channel comparisons"""
        
        if channels is None:
            channels = ['Direct', 'Organic Search']
        
        logging.info(f"📅 Period 1: {start_date1} to {end_date1}")
        logging.info(f"📅 Period 2: {start_date2} to {end_date2}")
        logging.info(f"📈 Channels: {', '.join(channels)}")
        
        all_data = []
        total_requests = 2  # One request per period, filter in post-processing
        current_request = 0
        
        # Get data for each date range (we'll filter channels in post-processing)
        for period, (start_date, end_date) in enumerate([
            (start_date1, end_date1), 
            (start_date2, end_date2)
        ], 1):
            
            current_request += 1
            logging.info(f"🔍 Fetching data ({current_request}/{total_requests}): Period {period}")
            
            data = self._fetch_ga4_data(start_date=start_date, end_date=end_date)
            
            # Filter for requested channels and add period info
            filtered_data = []
            for row in data:
                if row['channel_grouping'] in channels:
                    row['period'] = f"Period {period}"
                    row['date_range'] = f"{start_date} to {end_date}"
                    row['channel'] = row['channel_grouping']
                    filtered_data.append(row)
            
            logging.info(f"✅ Retrieved {len(filtered_data)} rows for Period {period} (filtered for {channels})")
            
            # Debug: Show unique channel names found
            if period == 1:
                unique_channels = set(row['channel_grouping'] for row in data)
                logging.info(f"🔍 Available channels in GA4: {sorted(unique_channels)}")
            
            all_data.extend(filtered_data)
        
        logging.info("🔄 Processing comparison data...")
        comparison_data = self._create_comparison_table(all_data, channels)
        
        logging.info(f"✅ Data processing complete. Raw: {len(all_data)} rows, Comparison: {len(comparison_data)} rows")
        return all_data, comparison_data
    
    def _fetch_ga4_data(self, start_date, end_date):
        """Fetch data from GA4 API - simplified version without filters"""
        
        logging.debug(f"Building API request from {start_date} to {end_date}")
        
        # Build request - no filters, get all data
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="pagePath"),
                Dimension(name="pageTitle"), 
                Dimension(name="sessionDefaultChannelGrouping"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=50000,  # Increased limit to catch more data
        )
        
        # Execute request
        logging.debug("📡 Sending API request to GA4...")
        try:
            response = self.client.run_report(request)
            logging.debug(f"📥 Received response with {len(response.rows)} rows")
        except Exception as e:
            logging.error(f"❌ API request failed: {str(e)}")
            raise
        
        # Convert to list of dictionaries
        rows = []
        for row in response.rows:
            # Handle missing values safely
            try:
                sessions = int(row.metric_values[0].value) if row.metric_values[0].value else 0
                users = int(row.metric_values[1].value) if row.metric_values[1].value else 0
                pageviews = int(row.metric_values[2].value) if row.metric_values[2].value else 0
            except (ValueError, IndexError):
                sessions = users = pageviews = 0
            
            row_data = {
                'page_path': row.dimension_values[0].value,
                'page_title': row.dimension_values[1].value,
                'channel_grouping': row.dimension_values[2].value,
                'sessions': sessions,
                'total_users': users,
                'pageviews': pageviews,
            }
            rows.append(row_data)
        
        return rows
    
    def _create_comparison_table(self, all_data, channels):
        """Create a comparison table from raw data"""
        
        # Group data by page path
        page_data = {}
        
        # Debug: Check homepage data specifically
        homepage_debug = []
        
        for row in all_data:
            page_path = row['page_path']
            channel = row['channel']
            period = row['period']
            
            # Debug homepage data
            if page_path == '/':
                homepage_debug.append({
                    'channel': channel,
                    'period': period,
                    'sessions': row['sessions']
                })
            
            if page_path not in page_data:
                page_data[page_path] = {
                    'page_title': row['page_title'],
                    'data': {}
                }
            
            key = f"{channel}_{period}"
            if key in page_data[page_path]['data']:
                # Aggregate sessions if key already exists
                page_data[page_path]['data'][key]['sessions'] += row['sessions']
            else:
                page_data[page_path]['data'][key] = {
                    'sessions': row['sessions'],
                }
        
        # Debug: Show homepage data
        if homepage_debug:
            logging.info("🏠 Homepage (/) debug data:")
            for debug_row in homepage_debug:
                logging.info(f"  {debug_row['channel']} {debug_row['period']}: {debug_row['sessions']} sessions")
        
        # Create comparison rows
        comparison_rows = []
        
        for page_path, data in page_data.items():
            row = {
                'page_path': page_path,
                'page_title': data['page_title']
            }
            
            # Calculate total traffic for each period
            total_period1 = 0
            total_period2 = 0
            
            # Add data for each channel and period
            for channel in channels:
                for period in ['Period 1', 'Period 2']:
                    key = f"{channel}_{period}"
                    sessions = 0
                    if key in data['data']:
                        sessions = data['data'][key]['sessions']
                    
                    # Clean channel name for column
                    clean_channel = channel.replace(' ', '_').replace('Search', '').strip('_')
                    if clean_channel == 'Organic':
                        clean_channel = 'Organic'
                    elif clean_channel == 'Paid':
                        clean_channel = 'Paid'
                    elif clean_channel == 'Direct':
                        clean_channel = 'Direct'
                    
                    period_num = period.split()[1]
                    row[f"{clean_channel}_Period{period_num}"] = sessions
                    
                    # Add to total
                    if period == 'Period 1':
                        total_period1 += sessions
                    else:
                        total_period2 += sessions
            
            # Add totals
            row['Total_Period1'] = total_period1
            row['Total_Period2'] = total_period2
            
            # Calculate percentage changes
            # Total change
            if total_period1 > 0:
                total_change = ((total_period2 - total_period1) / total_period1) * 100
                row['Total_Change'] = round(total_change, 1)
            else:
                row['Total_Change'] = 0 if total_period2 == 0 else 100
            
            # Channel changes
            for channel in channels:
                clean_channel = channel.replace(' ', '_').replace('Search', '').strip('_')
                if clean_channel == 'Organic':
                    clean_channel = 'Organic'
                elif clean_channel == 'Paid':
                    clean_channel = 'Paid'
                elif clean_channel == 'Direct':
                    clean_channel = 'Direct'
                
                period1_sessions = row.get(f"{clean_channel}_Period1", 0)
                period2_sessions = row.get(f"{clean_channel}_Period2", 0)
                
                if period1_sessions > 0:
                    change = ((period2_sessions - period1_sessions) / period1_sessions) * 100
                    row[f"{clean_channel}_Change"] = round(change, 1)
                else:
                    row[f"{clean_channel}_Change"] = 0 if period2_sessions == 0 else 100
            
            comparison_rows.append(row)
        
        return comparison_rows
    
    def export_to_csv(self, raw_data, comparison_data, output_base):
        """Export data to CSV files"""
        
        # Create Reports directory if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        reports_dir = os.path.join(script_dir, "Reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Export raw data
        raw_file = os.path.join(reports_dir, f"{output_base}_raw.csv")
        if raw_data:
            fieldnames = raw_data[0].keys()
            with open(raw_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(raw_data)
            logging.info(f"📄 Raw data exported to: {raw_file}")
        
        # Export comparison data
        comparison_file = os.path.join(reports_dir, f"{output_base}_comparison.csv")
        if comparison_data:
            fieldnames = comparison_data[0].keys()
            with open(comparison_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(comparison_data)
            logging.info(f"📊 Comparison data exported to: {comparison_file}")
        
        return raw_file, comparison_file

def main():
    parser = argparse.ArgumentParser(description='Export GA4 traffic comparison data')
    parser.add_argument('--property-id', required=True, help='GA4 Property ID')
    parser.add_argument('--credentials', required=True, help='Path to service account JSON')
    parser.add_argument('--start1', required=True, help='Start date for period 1 (YYYY-MM-DD)')
    parser.add_argument('--end1', required=True, help='End date for period 1 (YYYY-MM-DD)')
    parser.add_argument('--start2', required=True, help='Start date for period 2 (YYYY-MM-DD)')
    parser.add_argument('--end2', required=True, help='End date for period 2 (YYYY-MM-DD)')
    parser.add_argument('--channels', nargs='+', default=['Direct', 'Organic Search'],
                        help='Channels to compare')
    parser.add_argument('--output', default='ga4_traffic_comparison',
                        help='Output filename base (without extension)')
    
    args = parser.parse_args()
    
    # Initialize exporter
    logging.info("🚀 Starting GA4 Traffic Comparison Export")
    try:
        exporter = GA4Exporter(args.property_id, args.credentials)
    except Exception as e:
        logging.error(f"❌ Failed to initialize GA4 exporter: {str(e)}")
        return
    
    logging.info(f"📊 Analysis Configuration:")
    logging.info(f"  Period 1: {args.start1} to {args.end1}")
    logging.info(f"  Period 2: {args.start2} to {args.end2}")
    logging.info(f"  Channels: {', '.join(args.channels)}")
    
    # Get data
    try:
        raw_data, comparison_data = exporter.get_traffic_comparison(
            start_date1=args.start1,
            end_date1=args.end1,
            start_date2=args.start2,
            end_date2=args.end2,
            channels=args.channels
        )
    except Exception as e:
        logging.error(f"❌ Failed to fetch data: {str(e)}")
        return
    
    # Export to CSV files
    try:
        raw_file, comparison_file = exporter.export_to_csv(raw_data, comparison_data, args.output)
        
        logging.info("✅ Export completed successfully!")
        logging.info(f"📈 Results:")
        logging.info(f"  Raw data: {len(raw_data)} rows")
        logging.info(f"  Comparison data: {len(comparison_data)} rows")
        
        # Show summary of top traffic drops/gains
        if comparison_data:
            # Show top total traffic drops
            sorted_data = sorted(comparison_data, key=lambda x: x.get('Total_Change', 0))
            logging.info(f"📉 Top 5 total traffic drops:")
            for i, row in enumerate(sorted_data[:5]):
                logging.info(f"  {row['page_path']}: {row.get('Total_Change', 0)}%")
        
    except Exception as e:
        logging.error(f"❌ Failed to export data: {str(e)}")
        return

if __name__ == "__main__":
    main()

# Example usage:
"""
python GA4TrafficAnalyzer.py \
    --property-id YOUR_PROPERTY_ID \
    --credentials path/to/service_account.json \
    --start1 2024-05-01 \
    --end1 2024-05-07 \
    --start2 2024-05-08 \
    --end2 2024-05-14 \
    --channels Direct "Organic Search" "Paid Search" \
    --output traffic_comparison_analysis
"""