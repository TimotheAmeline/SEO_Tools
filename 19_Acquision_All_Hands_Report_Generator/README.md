# All Hands Report Generator

A comprehensive SEO analytics tool that generates multi-period performance reports by combining Google Search Console (GSC) and Google Analytics 4 (GA4) data.

## Overview

This tool creates detailed Excel reports for SEO performance analysis, providing insights across multiple time periods including weekly trends, month-over-month comparisons, and year-over-year analysis. It's designed for stakeholders who need comprehensive SEO performance summaries.

## Features

- **Weekly Performance Tracking**: GSC and GA4 data broken down by week with week-over-week changes
- **Multi-Period Analysis**: 3-month detailed comparison with percentage changes
- **Year-over-Year Comparison**: Same period comparison from previous year
- **URL Performance Analysis**: Top losing and winning URLs by traffic
- **Query Performance Tracking**: Top 25 losing search queries
- **Traffic Segmentation**: Organic, paid, direct, and other traffic categorization
- **Formatted Excel Output**: Professional reports with styling and multiple sheets

## Requirements

```bash
pip install pandas google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client openpyxl
```

## Setup

1. **Google Service Account**: Create a service account with access to:
   - Google Search Console API (scope: `webmasters.readonly`)
   - Google Analytics Data API (scope: `analytics.readonly`)

2. **Permissions**: Ensure the service account has access to:
   - Your GSC property
   - Your GA4 property

## Usage

```bash
python all_hands_report.py \
  --site-url "https://www.example.com/" \
  --ga-property-id "123456789" \
  --credentials "path/to/service-account.json" \
  --start-date "2025-05-01" \
  --end-date "2025-05-31" \
  --output "reports/may_2025_report.xlsx"
```

### Parameters

- `--site-url`: GSC site URL (with protocol, e.g., https://www.example.com/)
- `--ga-property-id`: GA4 Property ID (numbers only)
- `--credentials`: Path to Google service account JSON file
- `--start-date`: Analysis start date (YYYY-MM-DD format)
- `--end-date`: Analysis end date (YYYY-MM-DD format)
- `--output`: Output Excel file path (optional, defaults to AllHandsReports/all_hands_report.xlsx)

## Report Structure

The generated Excel file contains 8 sheets:

1. **GSC Weekly Performance**: Weekly GSC metrics with week-over-week changes
2. **GA4 Weekly Performance**: Weekly GA4 sessions by traffic source
3. **3-Month View**: Comparative analysis across three consecutive periods
4. **Year over Year**: Current period vs same period last year
5. **GSC Top 10 Losing URLs**: URLs with biggest click drops
6. **GSC Top 25 Losing Queries**: Search queries with biggest click drops
7. **GA4 Top 10 Losing URLs**: URLs with biggest session drops
8. **GA4 Top 10 Winning URLs**: URLs with highest session volumes

## Key Metrics

### GSC Metrics
- Clicks, Impressions, CTR, Average Position
- Month-over-month and year-over-year changes
- URL and query-level performance

### GA4 Metrics
- Total Sessions, Organic Sessions, Paid Sessions, Direct Sessions
- Traffic source categorization
- Session trends and changes

## Date Range Calculations

The tool automatically calculates comparison periods:
- **Current Period**: User-specified date range
- **Previous Period**: Same number of days immediately before current
- **Previous-2 Period**: Same number of days before previous period
- **Year-over-Year**: Same dates from previous year

## Output Features

- Professional Excel formatting with headers and styling
- Percentage change calculations
- CTR changes shown in both percentage and percentage points
- Auto-adjusted column widths
- Color-coded headers and titles

## Error Handling

The tool includes comprehensive error handling for:
- API connection failures
- Missing credentials
- Invalid date formats
- Empty data responses
- Property access issues

## Example Output Summary

```
📊 All Hands Report Summary:
   Period analyzed: 2025-05-01 to 2025-05-31 (31 days)
   GSC Weekly data points: 5
   GA4 Weekly data points: 5
   GA4 total sessions (current): 15,432
   GA4 organic sessions (current): 8,765
   GSC total clicks (current): 12,345
   Top losing URLs identified: 10 (GSC), 10 (GA4)
   Top winning URLs identified: 10 (GA4)
```

## Notes

- The tool handles both standard GSC properties and domain properties
- Traffic categorization is based on GA4's default channel grouping
- Large datasets are paginated to ensure complete data retrieval
- URL normalization preserves original paths while handling edge cases

## Example
python SEOTools/All_hands_report/all_hands_report.py \
  --site-url "https://www.example.com/" \
  --ga-property-id "386754123" \
  --credentials "SEOTools/gsc-analyzer/service_account.json" \
  --start-date "2025-05-01" \
  --end-date "2025-05-31" \
  --output "SEOTools/All_hands_report/may_2025_report.xlsx"