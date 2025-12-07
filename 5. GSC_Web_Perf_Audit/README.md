# GSC Analyzer

A Python tool for analyzing Google Search Console data to identify SEO opportunities, detect performance issues, and prioritize actions.

## Features

- **Priority Actions**: Consolidated view of the most critical issues requiring immediate attention
- **CTR Outlier Detection**: Identifies pages/queries with CTR significantly different from expected for their position
- **Traffic Change Detection**: Detects significant changes in traffic (impressions, clicks)
- **Keyword Trend Analysis**: Identifies rising and declining keywords
- **URL Performance Analysis**: Tracks overall performance changes at the page level
- **Seasonality Analysis**: Detects seasonal patterns to contextualize changes
- **Cannibalization Detection**: Identifies potential keyword cannibalization issues

## Installation

### Prerequisites

- Python 3.8+
- Google Search Console API access
- Service account with access to your GSC properties

### Setup

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd gsc-analyzer
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Search Console API access:
   - Place your service account JSON key file in the project root directory as `service_account.json`
   - Ensure your service account has been added to your Search Console property with appropriate permissions

4. Configure your site in `config.py`:
   ```python
   # Update this with your actual site in the format shown in GSC
   SITE_URL = 'sc-domain:yourdomain.com'  # Use the exact format from GSC API
   
   # Update target countries as needed
   TARGET_COUNTRIES = [
       'usa',  # United States
       'gbr',  # United Kingdom 
       'ind',  # India
       # Add other countries as needed
   ]
   ```

## Usage

### Command Line Usage

```bash
python main.py
```

This will:
1. Fetch historical data if needed (first run or if data is older than 30 days)
2. Fetch recent data for analysis
3. Run all analysis modules
4. Generate reports in the ./reports directory

### Web Interface

GSC Analyzer now includes a web-based interface that provides enhanced visualizations and easier access to all features:

```bash
# Install web dependencies
pip install -r requirements_web.txt

# Run the web application
python web_app.py
```

Then open your browser and navigate to:
```
http://127.0.0.1:5000/
```

The web interface provides:
- Interactive dashboard with visualizations
- Easy configuration through a setup wizard
- Interactive charts for all analysis components
- Priority actions display with severity indicators
- One-click access to all reports

For more details, see [WEB_README.md](WEB_README.md).

### Command Line Parameters

| Parameter | Description |
|-----------|-------------|
| `--force-refresh` | Force refresh of historical data even if it's recent |
| `--auto-yes` | Automatically answer yes to all prompts |
| `--skip-historical` | Skip historical data analysis (faster for daily runs) |
| `--output-dir DIR` | Specify a custom directory for reports (default: ./reports) |

### Example Commands

#### Daily Quick Check

For a fast daily check of recent changes:

```bash
python main.py --skip-historical
```

#### Weekly Deep Analysis

For a comprehensive weekly analysis:

```bash
python main.py
```

#### Custom Report Location

Save reports to a specific directory:

```bash
python main.py --output-dir ./my_reports
```

## Generated Reports

All reports are saved in the specified output directory with timestamps:

- **priority_actions**: Critical issues requiring immediate attention
- **ctr_outliers**: Pages/queries with CTR significantly different from expected
- **traffic_changes**: Significant changes in traffic
- **rising_keywords**: Keywords with increasing impressions
- **declining_keywords**: Keywords with decreasing impressions
- **url_performance**: Pages with significant performance changes
- **cannibalization**: Potential keyword cannibalization issues
- **gsc_analysis_full.xlsx**: Combined Excel report with all analyses
- **analysis_summary**: Summary of all findings

## Customizing Thresholds and Parameters

You can customize various thresholds to adjust the sensitivity of the analyzers. Here's a guide to the key parameters you might want to modify:

### Global Settings in `config.py`

```python
# Core significance thresholds - Lines 40-42
SIGNIFICANCE_THRESHOLD = 0.05  # p-value threshold for statistical tests
MIN_IMPRESSIONS = 10  # Minimum impressions to consider for analysis
MIN_CLICKS = 3  # Minimum clicks to consider for analysis

# Expected CTR by position - Lines 43-46
CTR_POSITION_BASELINE = {
    1: 0.20, 2: 0.10, 3: 0.06, 4: 0.04, 5: 0.03,
    6: 0.02, 7: 0.015, 8: 0.01, 9: 0.008, 10: 0.005
}
```

### Priority Actions in `main.py`

The Priority Actions report uses its own thresholds to determine what issues are significant enough to highlight:

```python
# In generate_priority_report function - Around line 370
threshold = 40  # Overall significance score threshold (0-100)

# CTR Underperformers - Around line 385
ctr_difference_pct <= -15  # CTR at least 15% below expected

# Traffic Losses - Around line 409
impressions_change_pct <= -20  # At least 20% traffic loss

# Declining Keywords - Around line 433
impressions_change_pct <= -30  # At least 30% impression loss

# Rising Keywords - Around line 476
impressions_change_pct >= 50  # At least 50% impression gain
```

### CTR Outliers in `analyzers/ctr_outliers.py`

```python
# In analyze method - Around line 50
# Determining if a page is underperforming or overperforming
ctr_difference < -0.02 and ctr_difference_pct < -15  # Underperforming
ctr_difference > 0.02 and ctr_difference_pct > 15  # Overperforming
```

### Traffic Changes in `analyzers/traffic_changes.py`

```python
# In analyze method - Around line 40
comparison_period = 'week'  # 'week' or 'month'
min_change_pct = 10  # Minimum percentage change to be considered significant
```

### Keyword Trends in `analyzers/keyword_trends.py`

```python
# In analyze method - Around line 40
trend_period_days = 30  # Number of days to analyze trends
min_change_pct = 20  # Minimum percentage change to be significant
min_significance = 5  # Minimum significance score
```

### URL Performance in `analyzers/url_performance.py`

```python
# In analyze method - Around line 40
comparison_period = 'month'  # 'week' or 'month'
min_impressions = 20  # Minimum impressions threshold

# In _classify_url_change method - Around line 190
# Various thresholds for classifying performance changes:
position_change < -0.5 and imp_change_pct > 10  # significant_improvement
position_change > 0.5 and imp_change_pct < -10  # significant_decline
query_change_pct < -20 and imp_change_pct < -10  # losing_query_diversity
query_change_pct > 20 and imp_change_pct > 10  # gaining_query_diversity
imp_change_pct > 30  # major_traffic_gain
imp_change_pct < -30  # major_traffic_loss
imp_change_pct > 10  # moderate_traffic_gain
imp_change_pct < -10  # moderate_traffic_loss
```

### Cannibalization in `analyzers/cannibalization.py`

```python
# In analyze method - Around line 40
min_impressions = 50  # Minimum impressions threshold
ranking_volatility_threshold = 2.0  # Threshold for position volatility

# In the results processing - Around line 120
# Severity calculation based on:
row['ranking_volatility'] > ranking_volatility_threshold  # Volatility indicates cannibalization
has_close_positions  # Multiple pages with similar positions
not row['is_primary'] and row['impression_share'] > 25  # Non-primary page getting significant impressions
```

## Report Interpretation

### Priority Actions

- Focus on these issues first - they represent the most critical items requiring attention
- Sorted by priority score, which combines significance and magnitude of the issue
- Each item includes a specific recommended action

### CTR Outliers

- **Underperforming pages**: Consider updating titles, descriptions, or structured data to improve CTR
- **Overperforming pages**: Learn from these to apply successful elements to other pages

### Traffic Changes

- **Traffic increases**: Pages gaining visibility - potential opportunities
- **Traffic decreases**: Pages losing visibility - may require attention or updates

### URL Performance

- Shows overall page performance changes, regardless of specific queries
- Highlights pages with declining traffic or query diversity
- Identifies new pages or pages that have disappeared from search

### Keyword Trends

- **Rising keywords**: Focus optimization efforts on these growing opportunities
- **Declining keywords**: Identify and address issues causing decline

### Cannibalization Issues

- Consolidate content or better differentiate pages competing for the same queries

## Data Storage and Caching

The tool implements efficient data handling:

- **Historical data**: Saved locally and only refreshed when older than 30 days
- **Seasonality patterns**: Calculated once and stored for future use
- **Daily caching**: If you run the tool multiple times in one day, it will use cached data

## Troubleshooting

### API Authentication Issues

If you encounter authentication errors:
- Verify your service account JSON key is correctly placed
- Ensure your service account has been properly added to your GSC property

### No Data Retrieved

- Check that your site URL in config.py exactly matches how it appears in Search Console (e.g., 'sc-domain:example.com')
- Verify that your site has sufficient data in the selected date range

### Rate Limiting

If you hit API rate limits:
- The tool includes automatic retry logic with delay
- Consider running during off-peak hours for initial large data fetches

### Adjusting Thresholds

If you're seeing:
- Too many insignificant issues: Increase the thresholds in the relevant analyzer
- Not enough issues detected: Lower the thresholds to make the detection more sensitive