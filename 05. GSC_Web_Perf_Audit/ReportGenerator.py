"""
Report Generator for GSC Analyzer
"""
import os
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

class ReportGenerator:
    """Generate reports from analysis results"""
    
    def __init__(self, output_dir='./reports'):
        """
        Initialize the report generator
        
        Args:
            output_dir (str): Directory to save reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def save_csv(self, df, filename):
        """Save DataFrame to CSV"""
        if df is None or df.empty:
            return None
            
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        filepath = os.path.join(self.output_dir, f"{filename}_{timestamp}.csv")
        df.to_csv(filepath, index=False)
        
        return filepath
    
    def save_excel(self, data_dict, filename):
        """
        Save multiple DataFrames to a single Excel file with adjusted column widths
        
        Args:
            data_dict (dict): Dictionary of sheet_name -> DataFrame pairs
            filename (str): Base filename for the Excel file
        """
        # Skip if no data
        if not data_dict or all(df is None or df.empty for df in data_dict.values()):
            return None
            
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as Excel
        filepath = os.path.join(self.output_dir, f"{filename}_{timestamp}.xlsx")
        
        # Use ExcelWriter with the openpyxl engine
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            for sheet_name, df in data_dict.items():
                if df is not None and not df.empty:
                    # Write the DataFrame to Excel
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Access the worksheet
                    worksheet = writer.sheets[sheet_name]
                    
                    # Set column widths based on content
                    for i, column in enumerate(df.columns):
                        # Find the maximum length in the column
                        column_width = max(
                            # Column header length
                            len(str(column)),
                            # Max content length, with a sample of rows for efficiency
                            df[column].astype(str).str.len().max() if len(df) > 0 else 0
                        )
                        
                        # Set a minimum width for readability
                        column_width = max(10, min(column_width, 50))  # Minimum 10, Maximum 50
                        
                        # Adjust for special columns
                        if 'page' in column.lower() or 'url' in column.lower():
                            column_width = min(60, max(column_width, 40))  # URLs tend to be long
                        elif 'query' in column.lower():
                            column_width = min(40, max(column_width, 30))  # Queries can be long
                        elif 'details' in column.lower():
                            column_width = min(70, max(column_width, 50))  # Details are often long
                        
                        # Set the column width (converting to Excel units)
                        worksheet.column_dimensions[worksheet.cell(row=1, column=i+1).column_letter].width = column_width + 2
        
        print(f"Excel report saved to {filepath}")
        return filepath
    
    def generate_summary(self, results_dict):
        """
        Generate a summary report
        
        Args:
            results_dict (dict): Dictionary of analysis results
            
        Returns:
            str: Path to the summary report
        """
        # Create summary DataFrame
        summary = []
        
        # Traffic changes
        if 'traffic_changes' in results_dict and not results_dict['traffic_changes'].empty:
            tc = results_dict['traffic_changes']
            increases = len(tc[tc['impressions_change'] > 0])
            decreases = len(tc[tc['impressions_change'] < 0])
            
            summary.append({
                'Category': 'Traffic Changes',
                'Metric': 'Increases',
                'Count': increases,
                'Details': f"Top query: {tc.iloc[0]['query'] if increases > 0 else 'None'}"
            })
            
            summary.append({
                'Category': 'Traffic Changes',
                'Metric': 'Decreases',
                'Count': decreases,
                'Details': f"Top query: {tc[tc['impressions_change'] < 0].iloc[0]['query'] if decreases > 0 else 'None'}"
            })
        
        # CTR outliers
        if 'ctr_outliers' in results_dict and not results_dict['ctr_outliers'].empty:
            co = results_dict['ctr_outliers']
            underperforming = len(co[co['is_underperforming']])
            overperforming = len(co[co['is_overperforming']])
            
            summary.append({
                'Category': 'CTR Performance',
                'Metric': 'Underperforming',
                'Count': underperforming,
                'Details': f"Highest impact: {co[co['is_underperforming']].iloc[0]['query'] if underperforming > 0 else 'None'}"
            })
            
            summary.append({
                'Category': 'CTR Performance',
                'Metric': 'Overperforming',
                'Count': overperforming,
                'Details': f"Highest impact: {co[co['is_overperforming']].iloc[0]['query'] if overperforming > 0 else 'None'}"
            })
        
        # Keyword trends
        if 'rising_keywords' in results_dict and not results_dict['rising_keywords'].empty:
            rising = len(results_dict['rising_keywords'])
            summary.append({
                'Category': 'Keyword Trends',
                'Metric': 'Rising Keywords',
                'Count': rising,
                'Details': f"Top opportunity: {results_dict['rising_keywords'].iloc[0]['query'] if rising > 0 else 'None'}"
            })
        
        if 'declining_keywords' in results_dict and not results_dict['declining_keywords'].empty:
            declining = len(results_dict['declining_keywords'])
            summary.append({
                'Category': 'Keyword Trends',
                'Metric': 'Declining Keywords',
                'Count': declining,
                'Details': f"Highest risk: {results_dict['declining_keywords'].iloc[0]['query'] if declining > 0 else 'None'}"
            })
        
        # Cannibalization
        if 'cannibalization' in results_dict and not results_dict['cannibalization'].empty:
            cannibal = len(results_dict['cannibalization'])
            unique_queries = results_dict['cannibalization']['query'].nunique()
            
            summary.append({
                'Category': 'Cannibalization',
                'Metric': 'Issues Detected',
                'Count': cannibal,
                'Details': f"Affecting {unique_queries} unique queries"
            })
        
        # URL Performance
        if 'url_performance' in results_dict and not results_dict['url_performance'].empty:
            up = results_dict['url_performance']
            improvements = len(up[up['performance_change'].isin(['significant_improvement', 'major_traffic_gain', 'moderate_traffic_gain'])])
            declines = len(up[up['performance_change'].isin(['significant_decline', 'major_traffic_loss', 'moderate_traffic_loss'])])
            new_urls = len(up[up['is_new']])
            lost_urls = len(up[up['is_lost']])
            
            summary.append({
                'Category': 'URL Performance',
                'Metric': 'Improving URLs',
                'Count': improvements,
                'Details': f"Top URL: {up[up['performance_change'].isin(['significant_improvement', 'major_traffic_gain'])].iloc[0]['page'] if improvements > 0 else 'None'}"
            })
            
            summary.append({
                'Category': 'URL Performance',
                'Metric': 'Declining URLs',
                'Count': declines,
                'Details': f"Most affected: {up[up['performance_change'].isin(['significant_decline', 'major_traffic_loss'])].iloc[0]['page'] if declines > 0 else 'None'}"
            })
            
            if new_urls > 0:
                summary.append({
                    'Category': 'URL Performance',
                    'Metric': 'New URLs',
                    'Count': new_urls,
                    'Details': f"Top new URL: {up[up['is_new']].iloc[0]['page'] if new_urls > 0 else 'None'}"
                })
            
            if lost_urls > 0:
                summary.append({
                    'Category': 'URL Performance',
                    'Metric': 'Lost URLs',
                    'Count': lost_urls,
                    'Details': f"Most significant loss: {up[up['is_lost']].iloc[0]['page'] if lost_urls > 0 else 'None'}"
                })

        # Create summary DataFrame
        summary_df = pd.DataFrame(summary)
        
        # Save to CSV
        if not summary_df.empty:
            return self.save_csv(summary_df, "analysis_summary")
        
        return None