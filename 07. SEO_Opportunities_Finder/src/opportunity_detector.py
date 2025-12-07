import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from src.analyzers import SEOAnalyzer
from config import THRESHOLDS
from tqdm import tqdm

class OpportunityDetector:
    def __init__(self, merged_data: pd.DataFrame):
        self.data = merged_data
        self.analyzer = SEOAnalyzer()
        self.opportunities = []
        
    def detect_opportunities(self) -> pd.DataFrame:
        """Run all detection algorithms and compile opportunities"""
        print("Detecting optimization opportunities...")
        
        for idx, row in tqdm(self.data.iterrows(), total=len(self.data)):
            # Skip if insufficient data
            if row.get('impressions', 0) < THRESHOLDS['min_impressions']:
                continue
            
            # Skip if already ranking well with good CTR
            if row.get('position', 0) <= 3 and row.get('ctr', 0) >= 0.15:
                continue
            
            opportunity = {
                'url': row['url'],
                'impressions': row.get('impressions', 0),
                'clicks': row.get('clicks', 0),
                'position': row.get('position', 0),
                'current_ctr': row.get('ctr', 0),
                'queries_count': row.get('queries_count', 0),
                'word_count': row.get('word_count', 0),
                'title': row.get('title', ''),
                'title_length': row.get('title_length', 0),
                'top_queries': row.get('top_queries', row.get('query', []))[:5]
            }
            
            # Run analyses
            analysis_results = {}
            
            # CTR Analysis
            ctr_analysis = self.analyzer.analyze_ctr_performance(row)
            analysis_results.update(ctr_analysis)
            
            # Title/Meta Analysis
            title_meta_analysis = self.analyzer.analyze_title_meta_match(row)
            analysis_results.update(title_meta_analysis)
            
            # Content Analysis
            content_analysis = self.analyzer.analyze_content_depth(row)
            analysis_results.update(content_analysis)
            
            # Add analysis results to opportunity
            opportunity.update(analysis_results)
            
            # Calculate opportunity score
            opportunity['opportunity_score'] = self.analyzer.calculate_opportunity_score(
                row, analysis_results
            )
            
            # Classify opportunity
            opportunity['opportunity_types'] = self.analyzer.classify_opportunity(
                analysis_results, row
            )
            
            # Only add if score is significant
            if opportunity['opportunity_score'] > 10:
                self.opportunities.append(opportunity)
        
        # Convert to DataFrame and sort
        opportunities_df = pd.DataFrame(self.opportunities)
        if not opportunities_df.empty:
            opportunities_df = opportunities_df.sort_values('opportunity_score', ascending=False)
        
        print(f"Found {len(opportunities_df)} optimization opportunities")
        return opportunities_df
    
    def generate_recommendations(self, opportunities_df: pd.DataFrame) -> pd.DataFrame:
        """Generate specific, actionable recommendations"""
        print("Generating recommendations...")
        
        recommendations = []
        
        for idx, opp in opportunities_df.iterrows():
            rec = {
                'url': opp['url'],
                'priority': self._calculate_priority(opp),
                'quick_wins': [],
                'recommendations': [],
                'estimated_impact': self._estimate_impact(opp)
            }
            
            # Title optimization
            if 'TITLE_OPTIMIZATION' in opp['opportunity_types']:
                missing_keywords = list(opp.get('missing_keywords', []))[:5]
                if missing_keywords:
                    rec['quick_wins'].append(
                        f"Add these keywords to title: {', '.join(missing_keywords)}"
                    )
                
                for issue in opp.get('title_issues', [])[:2]:
                    rec['recommendations'].append(f"Title: {issue}")
            
            # Meta optimization
            if 'META_OPTIMIZATION' in opp['opportunity_types']:
                rec['quick_wins'].append("Rewrite meta description to include top queries")
                for issue in opp.get('meta_issues', [])[:2]:
                    rec['recommendations'].append(f"Meta: {issue}")
            
            # CTR optimization
            if 'CTR_OPTIMIZATION' in opp['opportunity_types']:
                ctr_gap = opp.get('ctr_gap', 0)
                missed_clicks = opp.get('missed_clicks', 0)
                rec['recommendations'].append(
                    f"CTR is {ctr_gap*100:.1f}% below benchmark - missing ~{missed_clicks} clicks/month"
                )
                rec['quick_wins'].append("Test new title/meta to improve CTR")
            
            # Position-based recommendations
            if 'STRIKING_DISTANCE' in opp['opportunity_types']:
                rec['recommendations'].append(
                    f"Currently position {opp['position']:.1f} - within reach of top 3"
                )
                rec['recommendations'].append(
                    "Add internal links from high-authority pages"
                )
                
            elif 'PAGE2_PUSH' in opp['opportunity_types']:
                rec['recommendations'].append(
                    f"Stuck on page 2 (position {opp['position']:.1f})"
                )
                rec['recommendations'].append(
                    "Major content overhaul needed - aim for 2000+ words"
                )
            
            # Content recommendations
            if 'CONTENT_EXPANSION' in opp['opportunity_types']:
                current_words = opp.get('word_count', 0)
                rec['recommendations'].append(
                    f"Expand content from {current_words} to 1500+ words"
                )
                
                # Suggest sections based on queries
                if opp.get('top_queries'):
                    rec['recommendations'].append(
                        "Add sections covering: " + 
                        ", ".join([f'"{q}"' for q in opp['top_queries'][:3]])
                    )
            
            recommendations.append(rec)
        
        return pd.DataFrame(recommendations)
    
    def _calculate_priority(self, opp: Dict) -> str:
        """Calculate priority based on score and ease of implementation"""
        score = opp.get('opportunity_score', 0)
        
        # Quick wins = high impact + easy to implement
        quick_win = (
            'TITLE_OPTIMIZATION' in opp['opportunity_types'] or 
            'META_OPTIMIZATION' in opp['opportunity_types']
        )
        
        if score > 50 or (score > 30 and quick_win):
            return 'HIGH'
        elif score > 25:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _estimate_impact(self, opp: Dict) -> Dict:
        """Estimate potential impact"""
        current_clicks = opp.get('clicks', 0)
        potential_clicks = opp.get('potential_clicks', current_clicks)
        
        # Conservative estimate - achieve 80% of benchmark
        realistic_clicks = potential_clicks * 0.8
        click_increase = max(0, realistic_clicks - current_clicks)
        
        # Position improvement estimates
        if 'STRIKING_DISTANCE' in opp['opportunity_types']:
            click_increase *= 2.5  # Moving to top 3
        elif 'PAGE2_PUSH' in opp['opportunity_types']:
            click_increase *= 5  # Moving to page 1
        
        return {
            'potential_monthly_clicks': int(click_increase),
            'potential_increase_pct': (
                int(click_increase / current_clicks * 100) 
                if current_clicks > 0 else 0
            )
        }
    
    def export_opportunities(self, opportunities_df: pd.DataFrame, 
                           recommendations_df: pd.DataFrame,
                           output_dir: str = 'data/outputs'):
        """Export opportunities in multiple formats"""
        
        # Merge data
        final_df = pd.merge(
            opportunities_df,
            recommendations_df,
            on='url',
            how='left'
        )
        
        # Extract potential_monthly_clicks from estimated_impact dict
        final_df['potential_monthly_clicks'] = final_df['estimated_impact'].apply(
            lambda x: x.get('potential_monthly_clicks', 0) if isinstance(x, dict) else 0
        )
        
        # Format opportunity types
        final_df['opportunity_types'] = final_df['opportunity_types'].apply(
            lambda x: ' | '.join(x) if isinstance(x, list) else x
        )
        
        # 1. Main CSV export
        csv_columns = [
            'url', 'priority', 'opportunity_score', 'opportunity_types',
            'impressions', 'clicks', 'current_ctr', 'position',
            'potential_monthly_clicks', 'title', 'quick_wins'
        ]
        
        # Check which columns exist
        available_columns = [col for col in csv_columns if col in final_df.columns]
        
        # Ensure we have at least the core columns
        core_columns = ['url', 'priority', 'opportunity_score', 'opportunity_types', 
                       'impressions', 'clicks', 'current_ctr', 'position']
        available_columns = [col for col in core_columns if col in final_df.columns] + \
                          [col for col in available_columns if col not in core_columns]
        
        csv_df = final_df[available_columns].copy()
        
        # Convert lists to strings for CSV export
        if 'quick_wins' in csv_df.columns:
            csv_df['quick_wins'] = csv_df['quick_wins'].apply(
                lambda x: '; '.join(x) if isinstance(x, list) else ''
            )
        csv_df['quick_wins'] = csv_df['quick_wins'].apply(
            lambda x: '; '.join(x) if isinstance(x, list) else ''
        )
        
        csv_path = f"{output_dir}/seo_opportunities.csv"
        csv_df.to_csv(csv_path, index=False)
        print(f"\nExported opportunities to {csv_path}")
        
        # 2. Detailed report
        report_path = f"{output_dir}/opportunity_report.txt"
        with open(report_path, 'w') as f:
            f.write("SEO OPTIMIZATION OPPORTUNITIES REPORT\n")
            f.write(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("=" * 70 + "\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total opportunities: {len(final_df)}\n")
            f.write(f"High priority: {len(final_df[final_df['priority'] == 'HIGH'])}\n")
            
            # Calculate total potential clicks safely
            total_clicks = 0
            if 'potential_monthly_clicks' in final_df.columns:
                total_clicks = final_df['potential_monthly_clicks'].sum()
            f.write(f"Total potential clicks: {total_clicks:,}\n\n")
            
            # Top opportunities by priority
            for priority in ['HIGH', 'MEDIUM', 'LOW']:
                priority_df = final_df[final_df['priority'] == priority]
                if priority_df.empty:
                    continue
                
                f.write(f"\n{priority} PRIORITY ({len(priority_df)} pages)\n")
                f.write("=" * 70 + "\n\n")
                
                for _, row in priority_df.head(10).iterrows():
                    f.write(f"URL: {row['url']}\n")
                    f.write(f"Score: {row['opportunity_score']:.1f}\n")
                    f.write(f"Current Position: {row['position']:.1f}\n")
                    f.write(f"Current CTR: {row['current_ctr']*100:.1f}%\n")
                    
                    # Handle potential_monthly_clicks safely
                    monthly_clicks = row.get('potential_monthly_clicks', 0)
                    f.write(f"Potential Additional Clicks: +{int(monthly_clicks):,}/month\n")
                    f.write(f"Types: {row['opportunity_types']}\n")
                    
                    if row.get('quick_wins'):
                        f.write("\nQuick Wins:\n")
                        for qw in row['quick_wins']:
                            f.write(f"  • {qw}\n")
                    
                    if row.get('recommendations'):
                        f.write("\nRecommendations:\n")
                        for rec in row['recommendations']:
                            f.write(f"  • {rec}\n")
                    
                    if row.get('top_queries'):
                        f.write("\nTop Queries:\n")
                        for q in row['top_queries'][:5]:
                            f.write(f"  • {q}\n")
                    
                    f.write("\n" + "-" * 70 + "\n\n")
        
        print(f"Exported detailed report to {report_path}")
        
        # 3. Quick wins export
        if 'quick_wins' in final_df.columns:
            quick_wins_df = final_df[final_df['quick_wins'].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False
            )].copy()
            
            if not quick_wins_df.empty:
                quick_wins_path = f"{output_dir}/quick_wins.csv"
                quick_wins_cols = ['url', 'priority', 'quick_wins']
                if 'potential_monthly_clicks' in quick_wins_df.columns:
                    quick_wins_cols.append('potential_monthly_clicks')
                
                # Convert quick_wins list to string for CSV
                quick_wins_export = quick_wins_df[quick_wins_cols].copy()
                quick_wins_export['quick_wins'] = quick_wins_export['quick_wins'].apply(
                    lambda x: '; '.join(x) if isinstance(x, list) else ''
                )
                quick_wins_export.to_csv(quick_wins_path, index=False)
                print(f"Exported {len(quick_wins_df)} quick wins to {quick_wins_path}")
        
        return final_df