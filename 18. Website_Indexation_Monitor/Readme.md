# Website Indexation Monitor

## Overview
This tool automatically monitors your website's indexation status by crawling all URLs in your sitemaps and checking for noindex directives, status code issues, and missing pages. It's designed to catch indexation problems before they impact your SEO performance.

## What It Does
- **Sitemap Crawling**: Automatically discovers and processes all URLs from your XML sitemaps
- **Indexation Detection**: Checks for noindex meta tags, X-Robots-Tag headers, and googlebot directives
- **Status Monitoring**: Identifies HTTP errors, redirects, and connection issues
- **Change Tracking**: Compares results with previous runs to detect new issues or missing pages
- **Alert System**: Sends macOS notifications when issues are detected
- **Approval System**: Allows you to mark certain noindex URLs as intentional/approved
- **Detailed Reporting**: Generates CSV reports and text summaries for analysis

## Key Features
- **Multi-sitemap Support**: Processes sitemap indexes and nested sitemaps automatically
- **Smart Parsing**: Uses regex-based XML parsing for reliable sitemap processing
- **Polite Crawling**: Built-in delays and rate limiting to avoid overwhelming servers
- **Persistent Storage**: Remembers approved noindex URLs and previous check results
- **Interactive Mode**: Allows real-time approval of noindex URLs during execution
- **Comprehensive Logging**: Maintains detailed logs for troubleshooting and audit trails

## Requirements
- Python 3.x
- Required packages: requests, beautifulsoup4
- macOS (for notification system)

## Setup
1. Install dependencies: `pip install requests beautifulsoup4`
2. Ensure script has permission to send macOS notifications

## Usage
**Basic monitoring:**
```bash
python indexation_monitor.py --base-url https://example.com --sitemaps https://example.com/sitemap.xml
```

**Interactive mode (allows approving noindex URLs):**
```bash
python indexation_monitor.py --base-url https://example.com --sitemaps https://example.com/sitemap.xml --interactive
```

## Configuration
You can override the base URL and sitemap URLs using command line arguments.

## Output Files
- **CSV Reports**: `reports/indexation_report_YYYYMMDD_HHMMSS.csv`
- **Text Reports**: `logs/report_YYYYMMDD_HHMMSS.txt`
- **Activity Logs**: `logs/indexation_monitor.log`
- **Alert Logs**: `logs/indexation_alerts.log`
- **Approved URLs**: `data/approved_noindex_urls.json`
- **Previous Results**: `data/last_check_results.json`

## Issue Detection
The tool identifies:
- **New Noindex Issues**: URLs with noindex directives not previously approved
- **Status Problems**: 3xx redirects, 4xx client errors, 5xx server errors
- **Missing URLs**: Pages present in previous checks but not found now
- **Connection Errors**: URLs that couldn't be reached

## Notification System
- Desktop notifications for issue summaries
- Special alert log for critical issues
- Progress updates during execution
- Summary statistics at completion

## Use Cases
- **Daily SEO Monitoring**: Schedule to run daily and catch indexation issues early
- **Post-deployment Checks**: Verify no pages were accidentally noindexed after releases
- **Sitemap Validation**: Ensure all sitemap URLs are accessible and indexable
- **Redirect Monitoring**: Track unintended redirects that might hurt SEO
- **Content Audit**: Identify pages with indexation problems during site reviews

## Best Practices
- Run regularly (daily or weekly) to catch issues quickly
- Review and approve intentional noindex URLs to reduce false alerts
- Monitor the CSV reports for trends in status codes or redirect patterns
- Use interactive mode during initial setup to build your approved URL list
- Check alert logs for critical issues that need immediate attention

## Notes
- Designed for general websites and easily adaptable to any domain
- Respects robots.txt through polite crawling practices
- Handles large sitemaps with automatic batching
- Supports both standard and compressed (gzip) sitemaps
- Maintains state between runs for effective change detection
