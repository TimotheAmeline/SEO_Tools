# GSC & GA4 Period Comparison Tool

## Overview
This tool compares website performance between two time periods using Google Search Console (GSC) and Google Analytics 4 (GA4) data. It's designed for SEO analysis and content performance evaluation, particularly useful for assessing the impact of content changes, algorithm updates, or marketing campaigns.

## What It Does
- **GSC Analysis**: Compares clicks, impressions, CTR, and average position between two periods
- **GA4 Analysis**: Compares total sessions, organic sessions, paid sessions, and direct sessions between two periods
- **Performance Tracking**: Calculates percentage changes for all metrics
- **Batch Processing**: Analyzes multiple URLs from a CSV file simultaneously
- **Automated Reporting**: Generates detailed CSV reports with sortable data

## Requirements
- Python 3.x
- Google Cloud Service Account with API access
- Google Search Console API enabled
- Google Analytics Data API enabled
- Required Python packages: pandas, google-auth, google-api-python-client

## Setup
1. Create a Google Cloud Service Account
2. Enable GSC and GA4 APIs in Google Cloud Console
3. Download the service account credentials JSON file
4. Install required packages: `pip install pandas google-auth google-api-python-client`

## Usage
```bash
python gsc_comparison.py \
  --urls-file urls.csv \
  --site-url "https://www.yoursite.com/" \
  --ga-property-id "123456789" \
  --credentials "path/to/credentials.json" \
  --period1-start "2024-01-01" \
  --period1-end "2024-01-31" \
  --period2-start "2024-02-01" \
  --period2-end "2024-02-29"
```

## Input Requirements
- **URLs CSV**: Single column file with URLs (no header)
- **GSC Site URL**: Full site URL or domain property format
- **GA4 Property ID**: Numeric property ID from GA4
- **Date Format**: YYYY-MM-DD

## Output
- **GSC Report**: `gsc_comparison.csv` with click/impression/CTR/position data
- **GA4 Report**: `ga4_comparison.csv` with session data by traffic source
- **Console Summary**: Top performers and key statistics
- **Performance Rankings**: Results sorted by improvement percentage

## Key Features
- Handles API rate limits with batching
- Automatic URL format conversion between GSC and GA4
- Comprehensive error handling and progress tracking
- Traffic source segmentation (organic, paid, direct)
- Percentage change calculations with zero-value handling

## Use Cases
- Content pruning analysis
- Algorithm update impact assessment
- Campaign performance evaluation
- SEO strategy optimization
- Technical SEO change tracking

## Notes
- Requires proper API permissions for both GSC and GA4
- Large URL lists may take time due to API limits
- Results are automatically sorted by performance improvement
- Supports both standard and domain properties in GSC