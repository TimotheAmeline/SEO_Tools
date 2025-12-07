"""
GSC Analyzer Main Script
"""
import argparse
import sys
import os
from datetime import datetime
import pandas as pd

import config
from data_manager import DataManager
from analyzers.ctr_outliers import CTROutlierAnalyzer
from analyzers.traffic_changes import TrafficChangeAnalyzer
from analyzers.seasonality import SeasonalityAnalyzer
from analyzers.keyword_trends import KeywordTrendAnalyzer
from analyzers.ctr_outliers import CTROutlierAnalyzer
from analyzers.cannibalization import CannibalizationDetector
from ReportGenerator import ReportGenerator
from analyzers.url_performance import URLPerformanceAnalyzer


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Google Search Console Data Analyzer')
    parser.add_argument('--force-refresh', action='store_true', 
                        help='Force refresh of historical data')
    parser.add_argument('--auto-yes', action='store_true',
                        help='Automatically answer yes to all prompts')
    parser.add_argument('--skip-historical', action='store_true',
                        help='Skip historical data analysis (faster)')
    
    # Fix the default output directory to be relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_output_dir = os.path.join(script_dir, "reports")
    
    parser.add_argument('--output-dir', type=str, default=default_output_dir,
                        help='Directory to save reports')
    return parser.parse_args()

def save_report(df, filename, output_dir, sheet_name=None):
    """Save a report DataFrame to CSV and Excel"""
    if df is None or df.empty:
        print(f"No data for {filename}, skipping report.")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save as CSV
    csv_path = os.path.join(output_dir, f"{filename}_{timestamp}.csv")
    df.to_csv(csv_path, index=False)
    print(f"Report saved to {csv_path}")
    
    # Save as Excel if not None
    if sheet_name:
        excel_path = os.path.join(output_dir, f"{sheet_name}_{timestamp}.xlsx")
        df.to_excel(excel_path, sheet_name=sheet_name, index=False)
        print(f"Excel report saved to {excel_path}")
    
    return csv_path

def main():
    """Main function"""
    print("=" * 50)
    print("GSC Analyzer - Search Console Data Analysis Tool")
    print("=" * 50)
    
    # Parse arguments
    args = parse_args()
    
    # Initialize data manager
    data_manager = DataManager()
    
    # Initialize report generator - MOVED HERE, BEFORE ANALYSES
    report_generator = ReportGenerator(output_dir=args.output_dir)
    
    try:
        # Get historical data if needed
        historical_data = None
        
        if not args.skip_historical:
            print("\n== Historical Data ==")
            historical_data = data_manager.get_or_fetch_historical_data(
                force_refresh=args.force_refresh
            )
            
            if historical_data is None:
                print("Failed to retrieve historical data. Exiting.")
                sys.exit(1)
            
            print(f"Historical data shape: {historical_data.shape}")
            print(f"Date range: {historical_data['date'].min()} to {historical_data['date'].max()}")
        
        # Get recent data
        print("\n== Recent Data ==")
        recent_7d_data = data_manager.fetch_recent_data(days=config.RECENT_SHORT_DAYS, force_refresh=args.force_refresh)
        recent_30d_data = data_manager.fetch_recent_data(days=config.RECENT_MEDIUM_DAYS, force_refresh=args.force_refresh)
        
        if recent_7d_data is None or recent_7d_data.empty:
            print("Failed to retrieve recent data. Exiting.")
            sys.exit(1)
        
        print("\n== Analysis ==")
        
        # Initialize analyzers
        seasonality_analyzer = None
        
        if historical_data is not None:
            print("\nAnalyzing seasonality patterns...")
            seasonality_analyzer = SeasonalityAnalyzer(historical_data)
            seasonality_patterns = seasonality_analyzer.analyze()
            
            # Save seasonality patterns if found
            if seasonality_patterns and any(seasonality_patterns.values()):
                data_manager.save_seasonality_patterns(seasonality_patterns)
                print(f"Found seasonality patterns in your data.")
        
        # 1. CTR Outliers Analysis
        print("\nAnalyzing CTR outliers...")
        ctr_analyzer = CTROutlierAnalyzer(historical_data)
        ctr_outliers = ctr_analyzer.analyze(recent_30d_data)
        
        if not ctr_outliers.empty:
            print(f"Found {len(ctr_outliers)} CTR outliers.")
            underperforming = ctr_outliers[ctr_outliers['is_underperforming']]
            overperforming = ctr_outliers[ctr_outliers['is_overperforming']]
            print(f"  - {len(underperforming)} underperforming pages/queries")
            print(f"  - {len(overperforming)} overperforming pages/queries")
        else:
            print("No significant CTR outliers found.")
        
        # 2. Traffic Changes Analysis
        print("\nAnalyzing traffic changes...")
        traffic_analyzer = TrafficChangeAnalyzer(historical_data, seasonality_analyzer)
        traffic_changes = traffic_analyzer.analyze(recent_7d_data, comparison_period='week')
        
        if not traffic_changes.empty:
            print(f"Found {len(traffic_changes)} significant traffic changes.")
            increase = traffic_changes[traffic_changes['impressions_change'] > 0]
            decrease = traffic_changes[traffic_changes['impressions_change'] < 0]
            print(f"  - {len(increase)} increasing trends")
            print(f"  - {len(decrease)} decreasing trends")
        else:
            print("No significant traffic changes found.")
        
        # 3. Keyword Trends Analysis
        print("\nAnalyzing keyword trends...")
        keyword_analyzer = KeywordTrendAnalyzer(historical_data, seasonality_analyzer)
        rising_keywords, declining_keywords = keyword_analyzer.analyze(recent_30d_data)
        
        if not rising_keywords.empty:
            print(f"Found {len(rising_keywords)} rising keywords.")
        else:
            print("No significant rising keywords found.")
            
        if not declining_keywords.empty:
            print(f"Found {len(declining_keywords)} declining keywords.")
        else:
            print("No significant declining keywords found.")
        
        # 4. Cannibalization Analysis
        print("\nAnalyzing keyword cannibalization...")
        cannibalization_detector = CannibalizationDetector(historical_data)
        cannibalization_issues = cannibalization_detector.analyze(recent_30d_data)
        
        if not cannibalization_issues.empty:
            print(f"Found {len(cannibalization_issues)} potential cannibalization issues.")
            print(f"  - Affecting {cannibalization_issues['query'].nunique()} unique queries")
        else:
            print("No significant cannibalization issues found.")
        
        # 5. URL Performance Analysis
        print("\nAnalyzing URL performance...")
        url_analyzer = URLPerformanceAnalyzer(historical_data)
        url_performance = url_analyzer.analyze(recent_30d_data, comparison_period='month')

        if not url_performance.empty:
            print(f"Found {len(url_performance)} URLs with significant performance changes.")
            improvements = url_performance[url_performance['performance_change'].isin(['significant_improvement', 'major_traffic_gain', 'moderate_traffic_gain'])]
            declines = url_performance[url_performance['performance_change'].isin(['significant_decline', 'major_traffic_loss', 'moderate_traffic_loss'])]
            print(f"  - {len(improvements)} URLs with performance improvements")
            print(f"  - {len(declines)} URLs with performance declines")
            print(f"  - {len(url_performance[url_performance['is_new']])} new URLs")
            print(f"  - {len(url_performance[url_performance['is_lost']])} lost URLs")
        else:
            print("No significant URL performance changes found.")
        
        # Generate the priority report
        print("\n== Generating Priority Actions Report ==")
        
        def generate_priority_report(data_dict, threshold=40):
            """
            Generate a priority actions report highlighting items requiring urgent attention
            Test version with more sensitive thresholds
            
            Args:
                data_dict (dict): Dictionary containing all analysis results
                threshold (int): Significance score threshold for inclusion (0-100)
                
            Returns:
                pd.DataFrame: Priority actions report
            """
            priority_items = []
            
            # 1. CTR underperformers - more sensitive
            if 'ctr_outliers' in data_dict and not getattr(data_dict['ctr_outliers'], 'empty', True):
                # Check if DataFrame has required columns
                required_columns = ['is_underperforming', 'significance_score', 'ctr_difference_pct', 'avg_position', 
                                'actual_ctr', 'expected_ctr', 'query', 'page']
                if all(col in data_dict['ctr_outliers'].columns for col in required_columns):
                    extreme_ctr_issues = data_dict['ctr_outliers'][
                        (data_dict['ctr_outliers']['is_underperforming']) & 
                        (data_dict['ctr_outliers']['significance_score'] >= threshold) &
                        (data_dict['ctr_outliers']['ctr_difference_pct'] <= -15)
                    ].copy()
                    
                    if not extreme_ctr_issues.empty:
                        extreme_ctr_issues['issue_type'] = 'CTR Underperforming'
                        extreme_ctr_issues['action'] = 'Optimize title/meta description'
                        extreme_ctr_issues['priority_score'] = extreme_ctr_issues['significance_score'] * (abs(extreme_ctr_issues['ctr_difference_pct'])/100)
                        extreme_ctr_issues['details'] = extreme_ctr_issues.apply(
                            lambda row: f"Position: {row['avg_position']:.1f}, CTR: {row['actual_ctr']:.1%} vs Expected: {row['expected_ctr']:.1%}",
                            axis=1
                        )
                        
                        # Select only needed columns
                        priority_ctr = extreme_ctr_issues[[
                            'query', 'page', 'issue_type', 'action', 'priority_score', 'details'
                        ]]
                        
                        priority_items.append(priority_ctr)
            
            # 2. Traffic losses - more sensitive
            if 'traffic_changes' in data_dict and not getattr(data_dict['traffic_changes'], 'empty', True):
                # Check if DataFrame has required columns
                required_columns = ['impressions_change_pct', 'significance_score', 'change_type', 
                                'impressions_current', 'position_change', 'query', 'page']
                if all(col in data_dict['traffic_changes'].columns for col in required_columns):
                    traffic_losses = data_dict['traffic_changes'][
                        (data_dict['traffic_changes']['impressions_change_pct'] <= -20) &
                        (data_dict['traffic_changes']['significance_score'] >= threshold) &
                        (~data_dict['traffic_changes']['change_type'].isin(['seasonal_decrease', 'weekend_decrease']))  # Not seasonal
                    ].copy()
                    
                    if not traffic_losses.empty:
                        traffic_losses['issue_type'] = 'Traffic Loss'
                        traffic_losses['action'] = 'Check for ranking drops or indexing issues'
                        traffic_losses['priority_score'] = traffic_losses['significance_score'] * (abs(traffic_losses['impressions_change_pct'])/100)
                        traffic_losses['details'] = traffic_losses.apply(
                            lambda row: f"Impressions: {row['impressions_current']:.0f} (down {abs(row['impressions_change_pct']):.1f}%), Position change: {row['position_change']:.1f}",
                            axis=1
                        )
                        
                        # Select only needed columns
                        priority_traffic = traffic_losses[[
                            'query', 'page', 'issue_type', 'action', 'priority_score', 'details'
                        ]]
                        
                        priority_items.append(priority_traffic)
            
            # 3. Declining keywords - more sensitive
            if 'declining_keywords' in data_dict and not getattr(data_dict['declining_keywords'], 'empty', True):
                # Check if DataFrame has required columns
                required_columns = ['impressions_change_pct', 'significance_score', 'risk_score', 
                                'impressions_current', 'impressions_previous', 'query', 'page']
                if all(col in data_dict['declining_keywords'].columns for col in required_columns):
                    declining_kw = data_dict['declining_keywords'][
                        (data_dict['declining_keywords']['impressions_change_pct'] <= -30) &
                        (data_dict['declining_keywords']['significance_score'] >= threshold)
                    ].copy()
                    
                    if not declining_kw.empty:
                        declining_kw['issue_type'] = 'Declining Keyword'
                        declining_kw['action'] = 'Update content or improve relevance signals'
                        declining_kw['priority_score'] = declining_kw['risk_score']
                        declining_kw['details'] = declining_kw.apply(
                            lambda row: f"Impressions: {row['impressions_current']:.0f} (down {abs(row['impressions_change_pct']):.1f}%), Previously: {row['impressions_previous']:.0f}",
                            axis=1
                        )
                        
                        # Select only needed columns
                        priority_kw = declining_kw[[
                            'query', 'page', 'issue_type', 'action', 'priority_score', 'details'
                        ]]
                        
                        priority_items.append(priority_kw)
            
            # 4. Page performance declines - more sensitive
            if 'url_performance' in data_dict and not getattr(data_dict['url_performance'], 'empty', True):
                # Check if DataFrame has required columns
                required_columns = ['performance_change', 'significance_score', 'impressions_change_pct', 
                                'impressions_change', 'position_change', 'page']
                if all(col in data_dict['url_performance'].columns for col in required_columns):
                    # Include more performance change types
                    url_declines = data_dict['url_performance'][
                        (data_dict['url_performance']['performance_change'].isin([
                            'significant_decline', 'major_traffic_loss', 'moderate_traffic_loss', 'losing_query_diversity'
                        ])) &
                        (data_dict['url_performance']['significance_score'] >= threshold)
                    ].copy()
                    
                    if not url_declines.empty:
                        url_declines['issue_type'] = 'Page Performance Decline'
                        url_declines['action'] = 'Audit page content and technical elements'
                        url_declines['priority_score'] = url_declines['significance_score'] * (abs(url_declines['impressions_change_pct'])/100)
                        url_declines['details'] = url_declines.apply(
                            lambda row: f"Lost {abs(row['impressions_change']):.0f} impressions ({abs(row['impressions_change_pct']):.1f}%), Position change: {row['position_change']:.1f}",
                            axis=1
                        )
                        
                        # Ensure we have query column (might be missing in URL analysis)
                        if 'query' not in url_declines.columns:
                            url_declines['query'] = 'Multiple queries'
                            
                        # Select only needed columns
                        priority_url = url_declines[[
                            'query', 'page', 'issue_type', 'action', 'priority_score', 'details'
                        ]]
                        
                        priority_items.append(priority_url)
            
            # 5. Rising keywords - more sensitive
            if 'rising_keywords' in data_dict and not getattr(data_dict['rising_keywords'], 'empty', True):
                # Check if DataFrame has required columns
                required_columns = ['opportunity_score', 'impressions_change_pct', 'impressions_current', 
                                'position_current', 'query', 'page']
                if all(col in data_dict['rising_keywords'].columns for col in required_columns):
                    rising_kw = data_dict['rising_keywords'][
                        (data_dict['rising_keywords']['opportunity_score'] >= threshold) &
                        (data_dict['rising_keywords']['impressions_change_pct'] >= 50)
                    ].copy()
                    
                    if not rising_kw.empty:
                        rising_kw['issue_type'] = 'Rising Keyword Opportunity'
                        rising_kw['action'] = 'Optimize further to capitalize on trend'
                        rising_kw['priority_score'] = rising_kw['opportunity_score']
                        rising_kw['details'] = rising_kw.apply(
                            lambda row: f"Impressions: {row['impressions_current']:.0f} (up {row['impressions_change_pct']:.1f}%), Position: {row['position_current']:.1f}",
                            axis=1
                        )
                        
                        # Select only needed columns
                        priority_rising = rising_kw[[
                            'query', 'page', 'issue_type', 'action', 'priority_score', 'details'
                        ]]
                        
                        priority_items.append(priority_rising)
            
            # Combine all priority items
            if not priority_items:
                return pd.DataFrame(columns=['query', 'page', 'issue_type', 'action', 'priority_score', 'details'])
            
            try:
                combined_priorities = pd.concat(priority_items, ignore_index=True)
                
                # Sort by priority score (descending)
                combined_priorities = combined_priorities.sort_values('priority_score', ascending=False)
                
                # Round the priority score
                combined_priorities['priority_score'] = combined_priorities['priority_score'].round(1)
                
                return combined_priorities
            except Exception as e:
                print(f"Error combining priority items: {e}")
                return pd.DataFrame(columns=['query', 'page', 'issue_type', 'action', 'priority_score', 'details'])

        # Generate priority actions report
        priority_actions = generate_priority_report({
            'ctr_outliers': ctr_outliers,
            'traffic_changes': traffic_changes,
            'rising_keywords': rising_keywords,
            'declining_keywords': declining_keywords,
            'url_performance': url_performance
        })

        if not priority_actions.empty:
            print(f"Found {len(priority_actions)} items requiring urgent attention!")
            
            # Display top 5 priority items
            print("\nTop 5 priority actions:")
            for i, (_, row) in enumerate(priority_actions.head(5).iterrows()):
                print(f"{i+1}. [{row['issue_type']}] {row['query']} (Score: {row['priority_score']:.1f})")
                print(f"   Page: {row['page'][:100]}...")
                print(f"   Action: {row['action']}")
                print(f"   Details: {row['details']}")
        else:
            print("No urgent issues detected.")

        # Save individual reports
        if not ctr_outliers.empty:
            report_generator.save_csv(ctr_outliers, "ctr_outliers")
        
        if not traffic_changes.empty:
            report_generator.save_csv(traffic_changes, "traffic_changes")
        
        if not rising_keywords.empty:
            report_generator.save_csv(rising_keywords, "rising_keywords")
        
        if not declining_keywords.empty:
            report_generator.save_csv(declining_keywords, "declining_keywords")
        
        if not cannibalization_issues.empty:
            report_generator.save_csv(cannibalization_issues, "cannibalization")
        
        if not url_performance.empty:
            report_generator.save_csv(url_performance, "url_performance")
        
        # Save priority actions report
        if not priority_actions.empty:
            report_generator.save_csv(priority_actions, "priority_actions")
            print(f"Priority actions report saved with {len(priority_actions)} items")
        
        # Generate a combined Excel report with priority actions as the first tab
        excel_data = {
            'Priority_Actions': priority_actions if not priority_actions.empty else pd.DataFrame(),
            'CTR_Outliers': ctr_outliers if not getattr(ctr_outliers, 'empty', True) else pd.DataFrame(),
            'Traffic_Changes': traffic_changes if not getattr(traffic_changes, 'empty', True) else pd.DataFrame(),
            'Rising_Keywords': rising_keywords if not getattr(rising_keywords, 'empty', True) else pd.DataFrame(),
            'Declining_Keywords': declining_keywords if not getattr(declining_keywords, 'empty', True) else pd.DataFrame(),
            'Cannibalization': cannibalization_issues if not getattr(cannibalization_issues, 'empty', True) else pd.DataFrame(),
            'URL_Performance': url_performance if not getattr(url_performance, 'empty', True) else pd.DataFrame()
        }
        
        report_generator.save_excel(excel_data, "gsc_analysis_full")

        # Generate a summary
        report_generator.generate_summary({
            'priority_actions': priority_actions if not priority_actions.empty else pd.DataFrame(),
            'ctr_outliers': ctr_outliers if not getattr(ctr_outliers, 'empty', True) else pd.DataFrame(),
            'traffic_changes': traffic_changes if not getattr(traffic_changes, 'empty', True) else pd.DataFrame(),
            'rising_keywords': rising_keywords if not getattr(rising_keywords, 'empty', True) else pd.DataFrame(),
            'declining_keywords': declining_keywords if not getattr(declining_keywords, 'empty', True) else pd.DataFrame(),
            'cannibalization': cannibalization_issues if not getattr(cannibalization_issues, 'empty', True) else pd.DataFrame(),
            'url_performance': url_performance if not getattr(url_performance, 'empty', True) else pd.DataFrame()
        })
        
        print("\n== Analysis Complete ==")
        print(f"All reports saved to {args.output_dir}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()