# Content Pruning Tool

## Overview
This tool identifies underperforming content that should be pruned, improved, or consolidated to enhance overall site quality and SEO performance. It combines crawl data with Google Search Console and Google Analytics metrics to calculate data-driven pruning scores for each URL.

## What It Does
- **Performance Analysis**: Combines GSC clicks/impressions with GA pageviews/sessions
- **Content Quality Assessment**: Evaluates word count, meta descriptions, and other quality indicators
- **Pruning Score Calculation**: Generates 0-100 scores (higher = stronger pruning candidate)
- **Automated Recommendations**: Categorizes content into PRUNE, REVIEW, IMPROVE, MONITOR, or KEEP
- **Comprehensive Reporting**: Exports detailed CSV reports with all metrics and recommendations
- **Summary Statistics**: Provides breakdown of content distribution across recommendation categories

## Scoring Algorithm
The pruning score (0-100) is calculated using weighted factors:

**GSC Performance (40% weight):**
- Clicks: 0 clicks = +20 points, <10 = +15, <50 = +10, <100 = +5
- Position: >50 = +10 points, >20 = +5
- Impressions: <100 = +10 points, <500 = +5
- No GSC data = +25 points

**GA Performance (30% weight):**
- Pageviews: 0 = +15 points, <10 = +12, <50 = +8, <100 = +4
- No GA data = +15 points

**Content Quality (30% weight):**
- Word count: <300 = +15 points, <500 = +10, <800 = +5
- Missing meta description = +8 points

## Recommendation Categories
- **PRUNE (80+ score)**: Strong candidates for removal
- **REVIEW (60-79)**: Consider pruning or major improvement
- **IMPROVE (40-59)**: Optimize content and SEO
- **MONITOR (20-39)**: Minor improvements needed
- **KEEP (<20)**: Good performing content

## Requirements
- Python 3.x
- Required packages: pandas, requests, google-auth, google-api-python-client
- Google Search Console API access (optional)
- Google Analytics 4 API access (optional)
- Website crawl data (CSV/Excel format)

## Setup
1. Install dependencies: `pip install pandas requests google-auth google-api-python-client`
2. Set up Google Cloud project with GSC and GA4 APIs enabled
3. Create service account and download credentials JSON files
4. Export crawl data from tools like Screaming Frog, Sitebulb, or similar

## Input Requirements
**Crawl Data File (CSV/Excel):**
- URL column (required): url, address, page_url, link, or source
- Status code column (optional): status_code, response_code, http_status
- Indexability column (optional): indexability, indexable, robots_txt
- Content columns (optional): title, meta_description, word_count

The tool automatically:
- Filters to 200-status URLs only
- Removes non-indexable content
- Cleans and deduplicates URLs
- Handles missing columns gracefully

## Usage
**Complete analysis with all data sources:**
```bash
python content_pruning.py \
  --crawl-file crawl_data.csv \
  --site-url "https://www.yoursite.com/" \
  --ga-property-id "123456789" \
  --gsc-credentials "gsc_credentials.json" \
  --ga-credentials "ga_credentials.json"
```

**Analysis with crawl data only:**
```bash
python content_pruning.py --crawl-file crawl_data.csv
```

**Custom time period and output:**
```bash
python content_pruning.py \
  --crawl-file data.csv \
  --days-back 180 \
  --output "custom_pruning_report.csv"
```

## Command Line Options
- `--crawl-file`: Path to crawl data file (required)
- `--site-url`: GSC property URL for search data
- `--ga-property-id`: GA4 property ID (numbers only)
- `--gsc-credentials`: Path to GSC service account JSON
- `--ga-credentials`: Path to GA service account JSON
- `--days-back`: Historical data period in days (default: 90)
- `--output`: Output file path

## Output Files
**Main Report**: Detailed analysis with columns:
- URL and pruning score
- Recommendation category
- GSC metrics (clicks, impressions, CTR, position)
- GA metrics (pageviews, sessions)
- Content quality indicators

**Summary Report**: High-level statistics showing content distribution across recommendation categories

## Key Features
- **Flexible Input**: Supports multiple crawl tool formats
- **Smart Filtering**: Automatically focuses on indexable, accessible content
- **API Integration**: Combines multiple data sources for comprehensive analysis
- **Graceful Degradation**: Works with partial data when APIs aren't available
- **Data Validation**: Handles missing values and inconsistent formats
- **Performance Focused**: Efficiently processes large datasets

## Use Cases
- **Site Migrations**: Identify content to exclude from new site architecture
- **Content Strategy**: Focus resources on high-performing content
- **Technical SEO**: Remove crawl budget waste from low-value pages
- **Performance Optimization**: Eliminate pages that dilute overall site quality
- **Resource Allocation**: Prioritize improvement efforts on content with potential

## Best Practices
- **Combine Data Sources**: Use both GSC and GA data for comprehensive analysis
- **Review Before Pruning**: Manually review high-scoring candidates for business value
- **Consider Seasonality**: Adjust time periods for seasonal content patterns
- **Preserve Important Journeys**: Don't prune pages that support conversion paths
- **Monitor After Changes**: Track impact of pruning decisions on overall performance

## Data Privacy & Security
- Uses read-only API access to Google services
- Processes data locally without external transmission
- Service account credentials should be kept secure
- No user data is stored or transmitted beyond Google's APIs

## Limitations
- Requires historical performance data for accurate scoring
- Cannot assess business value or brand importance automatically
- GSC data may have sampling limitations for large sites
- Some metrics may be affected by recent algorithm changes