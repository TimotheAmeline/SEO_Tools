# GA4 Traffic Comparison Analyzer

## Overview
This tool analyzes traffic changes between two time periods using Google Analytics 4 data, providing detailed breakdowns by page and traffic channel. It's designed to help identify traffic drops, gains, and channel-specific performance changes across your website.

## What It Does
- **Period-over-Period Analysis**: Compares traffic metrics between two date ranges
- **Channel Breakdown**: Analyzes performance by traffic source (Direct, Organic Search, Paid, etc.)
- **Page-Level Insights**: Shows traffic changes for individual pages and sections
- **Percentage Calculations**: Automatically calculates growth/decline percentages
- **Dual Export Format**: Provides both raw data and summarized comparison tables
- **Traffic Source Filtering**: Focus analysis on specific channels of interest

## Key Features
- **Flexible Date Ranges**: Compare any two time periods (days, weeks, months)
- **Channel Selection**: Choose which traffic sources to analyze
- **High Volume Handling**: Processes up to 50,000 pages per request
- **Comprehensive Metrics**: Sessions, users, and pageviews for each page/channel
- **Smart Aggregation**: Combines data when multiple rows exist for same page/channel
- **Export Ready**: CSV format optimized for further analysis in Excel/Sheets

## Requirements
- Python 3.x
- Required packages: google-analytics-data, google-auth
- Google Analytics 4 property with data
- Service account with Analytics API access

## Setup
1. **Create Service Account**:
   - Enable Google Analytics Data API
   - Create service account in Google Cloud Console
   - Download credentials JSON file

2. **Grant Analytics Access**:
   - Add service account email to GA4 property
   - Assign "Viewer" role minimum

3. **Install Dependencies**:
   ```bash
   pip install google-analytics-data google-auth
   ```

## Usage
**Basic comparison between two periods:**
```bash
python ga4_analyzer.py \
  --property-id 123456789 \
  --credentials credentials.json \
  --start1 2024-01-01 \
  --end1 2024-01-31 \
  --start2 2024-02-01 \
  --end2 2024-02-29
```

**Include multiple traffic channels:**
```bash
python ga4_analyzer.py \
  --property-id 123456789 \
  --credentials credentials.json \
  --start1 2024-05-01 \
  --end1 2024-05-07 \
  --start2 2024-05-08 \
  --end2 2024-05-14 \
  --channels "Direct" "Organic Search" "Paid Search" "Social"
```

**Custom output filename:**
```bash
python ga4_analyzer.py \
  --property-id 123456789 \
  --credentials credentials.json \
  --start1 2024-04-01 \
  --end1 2024-04-30 \
  --start2 2024-05-01 \
  --end2 2024-05-31 \
  --output monthly_comparison_april_may
```

## Command Line Options
- `--property-id`: GA4 Property ID (required)
- `--credentials`: Path to service account JSON file (required)
- `--start1`: Start date for first period (YYYY-MM-DD) (required)
- `--end1`: End date for first period (YYYY-MM-DD) (required)
- `--start2`: Start date for second period (YYYY-MM-DD) (required)
- `--end2`: End date for second period (YYYY-MM-DD) (required)
- `--channels`: Traffic channels to analyze (default: Direct, Organic Search)
- `--output`: Output filename base (default: ga4_traffic_comparison)

## Output Files
**Raw Data Export** (`_raw.csv`):
- Complete dataset with all page/channel/period combinations
- Columns: page_path, page_title, channel_grouping, sessions, total_users, pageviews, period, date_range

**Comparison Export** (`_comparison.csv`):
- Summarized analysis with percentage changes
- Side-by-side comparison for each page
- Columns include:
  - Page path and title
  - Sessions by channel for each period
  - Total sessions for each period
  - Percentage changes for total and by channel

## Channel Options
Common GA4 channel groupings:
- **Direct**: Direct traffic
- **Organic Search**: Google, Bing organic results
- **Paid Search**: Google Ads, Bing Ads
- **Social**: Facebook, Twitter, LinkedIn, etc.
- **Email**: Email campaigns
- **Referral**: Other websites linking to yours
- **Display**: Display advertising
- **Video**: YouTube and other video platforms

## Use Cases
- **Algorithm Update Analysis**: Compare before/after Google algorithm changes
- **Campaign Impact Assessment**: Measure effect of marketing campaigns
- **Seasonal Trend Analysis**: Compare equivalent periods across different seasons
- **Technical Issue Investigation**: Identify pages affected by site changes
- **Content Performance Tracking**: Monitor specific page/section performance
- **Competitive Analysis**: Understand traffic shifts during competitive events

## Metrics Analyzed
- **Sessions**: Number of website sessions
- **Total Users**: Unique users visiting pages
- **Screen Page Views**: Total page views (GA4 standard)
- **Percentage Changes**: Calculated for all metrics between periods

## Analysis Features
- **Automated Aggregation**: Combines duplicate entries for same page/channel
- **Zero-Handling**: Proper calculation when baseline period has zero traffic
- **Sorting**: Results sorted by total traffic change (biggest drops first)
- **Debug Information**: Logs available channels and data processing steps
- **Error Handling**: Comprehensive error reporting and debugging

## Best Practices
- **Equal Period Lengths**: Use similar time spans for accurate comparison
- **Account for Seasonality**: Consider day-of-week and seasonal patterns
- **Multiple Channel Analysis**: Include all relevant traffic sources
- **Regular Monitoring**: Set up recurring analyses for ongoing insights
- **Combine with Other Data**: Cross-reference with GSC and other tools

## Troubleshooting
**Common Issues:**
- **No Data Returned**: Check property ID and date ranges
- **Authentication Error**: Verify service account has GA4 access
- **Missing Channels**: Review available channel groupings in GA4
- **Empty Results**: Ensure dates are within data retention period

**Debug Steps:**
1. Verify GA4 property ID is correct
2. Check service account email has GA4 access
3. Confirm date ranges contain data
4. Review available channel names in logs
5. Test with shorter date ranges first

## Data Limitations
- **Sampling**: Large datasets may be sampled by GA4
- **Data Freshness**: Recent data may not be immediately available
- **Thresholding**: GA4 may suppress low-volume data for privacy
- **Attribution**: Channel attribution follows GA4 default logic
- **Processing Time**: Large requests may take several minutes

## Output Interpretation
**Positive Changes**: Indicate traffic growth
**Negative Changes**: Show traffic decline
**Zero Changes**: No change between periods
**Channel-Specific Changes**: Help identify source of overall changes

Use comparison data to:
- Identify pages with significant traffic changes
- Understand which channels drove changes
- Prioritize investigation and optimization efforts
- Track success of SEO and marketing initiatives