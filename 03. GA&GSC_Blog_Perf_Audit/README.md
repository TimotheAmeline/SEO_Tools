# Blog Performance Analysis Tool

This tool analyzes blog performance by combining data from Google Search Console (GSC) and Google Analytics 4 (GA4). It provides insights into how your blog posts are performing in search results and how users interact with them.

## Features

- Combines GSC and GA4 data for comprehensive blog analysis
- Supports multiple GA4 properties for different domains/subdomains
- Classifies blog posts into performance categories:
  - Performing: Pages driving significant traffic
  - Potential: Pages with good impressions but low clicks
  - Struggling: Pages with meaningful impressions but low performance
  - Dead: Pages with minimal to no traffic
- Extracts top search queries for struggling and potential pages
- Generates detailed Excel reports with multiple sheets
- Optional query data extraction for faster analysis

## Prerequisites

- Python 3.7+
- Google Search Console API access
- Google Analytics 4 API access
- Service account credentials with access to both GSC and GA4

## Installation

1. Clone the repository
2. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

1. Set up a Google Cloud project and enable the Search Console API and Google Analytics Data API
2. Create a service account and download the credentials JSON file
3. Add the service account email to your GSC and GA4 properties with appropriate permissions

## Usage

### Basic Usage

```bash
python main.py \
  --site-url "https://example.com" \
  --ga-property-ids "123456789,987654321" \
  --credentials "path/to/credentials.json"
```

### Advanced Usage

```bash
python main.py \
  --site-url "https://example.com" \
  --ga-property-ids "123456789,987654321" \
  --credentials "path/to/credentials.json" \
  --source-file "path/to/urls.csv" \
  --days-back 90 \
  --output "path/to/output.xlsx" \
  --skip-queries
```

### Parameters

- `--site-url`: Your website URL (required)
- `--ga-property-ids`: Comma-separated list of GA4 Property IDs (required)
- `--credentials`: Path to service account credentials JSON file (required)
- `--source-file`: Path to CSV file containing blog URLs (default: SEOTools/BlogPerformance/Source/Source.csv)
- `--days-back`: Number of days of historical data to analyze (default: 90)
- `--output`: Path for the output Excel file (default: SEOTools/BlogPerformance/Reports/blog_performance_analysis.xlsx)
- `--skip-queries`: Flag to skip query data extraction for faster analysis

### Source CSV Format

The source CSV file should contain a column with blog URLs. The tool will automatically detect the URL column from common names like:
- url
- URL
- address
- Address
- page_url
- link

## Output

The tool generates an Excel report with the following sheets:

1. **All Pages**: Complete dataset of all analyzed pages
2. **Summary**: Overview of page categories and total metrics
3. **Pages with Potential**: Pages that could perform better with optimization
4. **Struggling Pages**: Pages that need attention
5. **Dead Pages**: Pages with minimal traffic

Each sheet includes relevant metrics and, when query extraction is enabled, top search queries for potential and struggling pages.

## Multiple GA4 Properties

The tool supports analyzing URLs across multiple GA4 properties. This is useful when:
- You have different properties for different domains/subdomains
- You've migrated from Universal Analytics to GA4 and have overlapping data
- You want to combine data from multiple properties

The tool will:
1. Try each property in sequence
2. Use the first property that has data for each URL
3. Show a summary of how many URLs were found in each property
4. Continue working even if some properties fail or don't have data

## Performance Optimization

For faster analysis of large URL sets:
1. Use the `--skip-queries` flag to skip query data extraction
2. Adjust the `--days-back` parameter to analyze a shorter time period
3. Split your URL list into smaller chunks if needed

## Troubleshooting

Common issues and solutions:

1. **API Access Errors**
   - Verify service account permissions
   - Check if APIs are enabled in Google Cloud Console
   - Ensure credentials file is valid

2. **No Data Found**
   - Verify GA4 property IDs
   - Check if URLs are properly formatted
   - Ensure the date range contains data

3. **Slow Performance**
   - Use `--skip-queries` for faster analysis
   - Reduce the `--days-back` value
   - Split URL list into smaller batches

## Contributing

Feel free to submit issues and enhancement requests!