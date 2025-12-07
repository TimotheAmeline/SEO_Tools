import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import DataLoader
from src.opportunity_detector import OpportunityDetector
from config import GSC_CONFIG, THRESHOLDS

def main():
    """Main execution function"""
    load_dotenv()
    
    # Paths
    screaming_frog_file = 'data/inputs/screaming_frog_export.csv'
    gsc_credentials = os.getenv('GSC_CREDENTIALS_PATH', 'credentials.json')
    output_dir = 'data/outputs'
    
    # Create directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs('data/inputs', exist_ok=True)
    
    print("=== SEO Opportunity Detector (GSC Edition) ===\n")
    
    # Initialize data loader
    loader = DataLoader(gsc_credentials_path=gsc_credentials)
    
    # 1. Load GSC data
    try:
        gsc_df = loader.load_gsc_data(
            site_url=GSC_CONFIG['site_url'],
            days=GSC_CONFIG['date_range_days']
        )
        
        if gsc_df.empty:
            print("ERROR: No data returned from GSC. Check your site URL and credentials.")
            return
            
    except Exception as e:
        print(f"ERROR loading GSC data: {e}")
        print("\nTroubleshooting:")
        print("1. Check credentials.json exists and is valid")
        print("2. Verify site URL in config.py matches GSC exactly")
        print("3. Ensure the account has access to the property")
        return
    
    # 2. Load Screaming Frog data (optional but recommended)
    sf_df = None
    if os.path.exists(screaming_frog_file):
        try:
            sf_df = loader.load_screaming_frog_data(screaming_frog_file)
            
            # Merge GSC and Screaming Frog data
            merged_data = loader.merge_gsc_screaming_frog(gsc_df, sf_df)
            
        except Exception as e:
            print(f"WARNING: Error loading Screaming Frog data: {e}")
            print("Continuing with GSC data only...")
            merged_data = None
    else:
        print("\nNOTE: No Screaming Frog export found.")
        print("For better analysis, export 'Internal > All' from Screaming Frog")
        print(f"and save as: {screaming_frog_file}")
        merged_data = None
    
    # 3. Prepare data for analysis
    if merged_data is None:
        # Use GSC data only - aggregate by URL
        print("\nUsing GSC data only (no metadata available)...")
        merged_data = gsc_df.groupby('url').agg({
            'query': lambda x: list(x),
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        # Add placeholder columns
        merged_data['title'] = ''
        merged_data['meta_description'] = ''
        merged_data['word_count'] = 0
        merged_data['title_length'] = 0
        merged_data['meta_length'] = 0
        merged_data['h1'] = ''
        merged_data['top_queries'] = merged_data['query'].apply(lambda x: x[:10])
        merged_data['queries_count'] = merged_data['query'].apply(len)
    
    # 4. Detect opportunities
    detector = OpportunityDetector(merged_data)
    opportunities_df = detector.detect_opportunities()
    
    if opportunities_df.empty:
        print("\nNo optimization opportunities found.")
        print("This could mean:")
        print("1. Your site is very well optimized (unlikely)")
        print("2. The thresholds are too strict")
        print("3. Not enough impression data")
        
        # Show some stats
        print(f"\nTotal URLs analyzed: {len(merged_data)}")
        print(f"URLs with 100+ impressions: {len(merged_data[merged_data['impressions'] >= 100])}")
        print(f"Average position: {merged_data['position'].mean():.1f}")
        return
    
    # 5. Generate recommendations
    recommendations_df = detector.generate_recommendations(opportunities_df)
    
    # 6. Export results
    final_df = detector.export_opportunities(
        opportunities_df, 
        recommendations_df,
        output_dir=output_dir
    )
    
    # 7. Print summary
    print("\n=== SUMMARY ===")
    print(f"Total opportunities found: {len(final_df)}")
    
    print(f"\nBy Priority:")
    print(final_df['priority'].value_counts())
    
    print(f"\nTop 10 Opportunities by Score:")
    summary_cols = ['url', 'priority', 'opportunity_score']
    if 'potential_monthly_clicks' in final_df.columns:
        summary_cols.append('potential_monthly_clicks')
    print(final_df[summary_cols].head(10).to_string(index=False))
    
    print(f"\nBy Opportunity Type:")
    all_types = []
    for types in final_df['opportunity_types']:
        all_types.extend(types.split(' | '))
    type_counts = pd.Series(all_types).value_counts()
    print(type_counts)
    
    # Quick wins summary
    if 'quick_wins' in final_df.columns:
        quick_wins = final_df[final_df['quick_wins'].apply(
            lambda x: len(x) > 0 if isinstance(x, list) else False
        )]
        
        if not quick_wins.empty:
            print(f"\n=== QUICK WINS ({len(quick_wins)} pages) ===")
            print("These can be implemented immediately for quick results:")
            for _, row in quick_wins.head(5).iterrows():
                print(f"\n{row['url']}:")
                for qw in row['quick_wins']:
                    print(f"  • {qw}")
    
    print(f"\n✅ Analysis complete!")
    print(f"📊 Check {output_dir}/seo_opportunities.csv for full results")
    print(f"📄 Check {output_dir}/opportunity_report.txt for detailed recommendations")

if __name__ == "__main__":
    main()