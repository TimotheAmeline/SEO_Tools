# Sitemap Index Status Checker

A comprehensive tool that crawls XML sitemaps and checks the indexing status of each URL using the Google Search Console API.

## 🎯 What It Does

- **Extracts URLs** from XML sitemaps (supports sitemap indexes and nested sitemaps)
- **Checks indexing status** for each URL via Google Search Console API
- **Provides detailed reporting** with coverage states, indexing information, and error analysis
- **Real-time progress tracking** with estimated completion times
- **Comprehensive error handling** with troubleshooting guidance

## 🚀 Features

### ✅ Sitemap Processing
- Handles regular sitemaps and sitemap indexes
- Supports nested sitemaps (recursive processing)
- Extracts additional metadata (last modified, priority, change frequency)
- Validates XML format and provides detailed error messages

### 🔍 GSC Integration
- URL inspection API for detailed indexing status
- Coverage state analysis (Indexed, Error, Valid with warning, etc.)
- Last crawl time and crawling information
- Mobile usability and robots.txt status
- Rate limiting and quota management

### 📊 Reporting & Analytics
- Comprehensive CSV reports with all indexing data
- Summary statistics and breakdowns
- Problematic URL identification
- Recently crawled URL highlights
- Processing performance metrics

### 🛠️ User Experience
- Real-time progress updates every 10 URLs
- Activity indicators and batch processing status
- Estimated completion times
- Detailed error messages with troubleshooting tips
- Input validation and helpful setup instructions

## 📋 Requirements

- Python 3.7+
- Google Search Console API access
- Service account or OAuth2 credentials

### Python Dependencies
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pandas requests
```

## 🔧 Setup

### 1. Google Search Console API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable the **Google Search Console API**
4. Create credentials:
   - **Service Account** (recommended for automation)
   - **OAuth2** (for interactive use)

### 2. Service Account Setup (Recommended)
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Save as `credentials.json` or specify custom path
4. Add the service account email to your GSC property:
   - Go to [Google Search Console](https://search.google.com/search-console)
   - Select your property
   - Settings → Users and permissions
   - Add user with "Full" permissions

### 3. Find Your Site Property Format
The tool will help identify the correct property format, but common formats are:
- `https://example.com/` (URL prefix property)
- `sc-domain:example.com` (Domain property)

## 💻 Usage

### Basic Usage
```bash
python SitemapIndexStatus.py --site "sc-domain:example.com" --sitemaps "https://example.com/sitemap.xml"
```

### Multiple Sitemaps
```bash
python SitemapIndexStatus.py \
  --site "sc-domain:example.com" \
  --sitemaps "https://example.com/sitemap.xml" "https://example.com/news-sitemap.xml" \
  --output "my_report.csv"
```

### Custom Credentials
```bash
python SitemapIndexStatus.py \
  --site "sc-domain:example.com" \
  --sitemaps "https://example.com/sitemap.xml" \
  --credentials "path/to/service_account.json" \
  --output "indexing_report.csv"
```

### Quiet Mode
```bash
python SitemapIndexStatus.py \
  --site "sc-domain:example.com" \
  --sitemaps "https://example.com/sitemap.xml" \
  --quiet
```

## 📊 Command Line Options

| Option | Required | Description | Default |
|--------|----------|-------------|---------|
| `--site` | ✅ | GSC site property URL | - |
| `--sitemaps` | ✅ | One or more sitemap URLs | - |
| `--output` | ❌ | Output CSV file path | Auto-generated with timestamp |
| `--credentials` | ❌ | Path to credentials JSON file | `credentials.json` |
| `--quiet` | ❌ | Reduce verbose output | False |

## 📈 Output

### CSV Report Columns
- `url` - The URL being checked
- `coverage_state` - Index coverage state (Indexed, Error, etc.)
- `indexing_state` - Indexing permission state
- `last_crawl_time` - When Google last crawled the URL
- `crawled_as` - How the URL was crawled (Desktop/Mobile)
- `verdict` - Overall verdict from GSC
- `page_fetch_state` - Page fetch result
- `robots_txt_state` - Robots.txt access state
- `mobile_usability_verdict` - Mobile usability status
- `error` - Error message if applicable

### Coverage States
- **Indexed** - URL is indexed and can appear in search results
- **Valid with warning** - Indexed but has issues
- **Error** - Cannot be indexed due to errors
- **Valid but not submitted** - Valid URL not in sitemap
- **ERROR** - API request failed
- **PERMISSION_ERROR** - Access denied

## 🔧 Troubleshooting

### Common Issues

#### ❌ "Credentials file not found"
**Solution:** 
1. Download credentials from Google Cloud Console
2. Save as `credentials.json` in the script directory
3. Or specify custom path with `--credentials`

#### ❌ "403 PERMISSION_DENIED"
**Solutions:**
1. Check site property format:
   ```bash
   # Try domain property format
   --site "sc-domain:example.com"
   
   # Or URL prefix format
   --site "https://example.com/"
   ```
2. Add service account to GSC property users
3. Verify the service account has the correct scopes

#### ❌ "No sites found"
**Solution:** Service account needs to be added to GSC property permissions

#### ❌ "Sitemap fetch failed"
**Solutions:**
1. Verify sitemap URL is accessible
2. Check for HTTPS/HTTP redirects
3. Ensure sitemap returns valid XML

### Rate Limiting
The tool automatically handles API rate limits with:
- Conservative request spacing (0.2s between requests)
- Automatic retry on quota errors
- Batch processing to manage load

## 📊 Performance

### Processing Speed
- ~3-5 URLs per second (depending on API response times)
- Batch processing in groups of 50 URLs
- Automatic progress tracking and time estimation

### Large Sitemaps
For sitemaps with thousands of URLs:
- Processing time: ~4-6 minutes per 1,000 URLs
- Memory usage: Minimal (streaming processing)
- Resume capability: Run multiple times safely

## 🔄 Integration Examples

### With Other SEO Tools
```bash
# Generate URL list for other tools
python SitemapIndexStatus.py --site "sc-domain:example.com" --sitemaps "sitemap.xml" --output "urls.csv"

# Filter non-indexed URLs
grep -v "Indexed" urls.csv > non_indexed_urls.csv
```

### Automation Scripts
```bash
#!/bin/bash
# Daily indexing check
python SitemapIndexStatus.py \
  --site "sc-domain:example.com" \
  --sitemaps "https://example.com/sitemap.xml" \
  --output "reports/indexing_$(date +%Y%m%d).csv" \
  --quiet
```

## 🆘 Support

### Getting Help
1. Run with `--help` for command line options
2. Check the detailed error messages and troubleshooting tips
3. Verify GSC API setup and permissions
4. Test with a small sitemap first

### Example Working Command
```bash
python SEOTools/SitemapIndexStatus/SitemapIndexStatus.py \
  --site "sc-domain:example.com" \
  --sitemaps "https://example.com/sitemap.xml" "https://www.example.com/templates-sitemap.xml" \
  --credentials "SEOTools/gsc-analyzer/service_account.json" \
  --output "SEOTools/SitemapIndexStatus/report.csv"
```

## 📝 Notes

- Processing large sitemaps (1000+ URLs) can take significant time
- API quotas may limit the number of URLs you can check per day
- The tool respects GSC API rate limits to avoid quota exhaustion
- Results are saved incrementally, so interruption won't lose all progress