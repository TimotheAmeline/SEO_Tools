# Google Indexing API Tool

## Overview
This tool uses Google's Indexing API to submit URLs for faster indexing or removal from Google's search results. It's designed to expedite the indexing process for new or updated content, particularly useful for template pages, blog posts, or time-sensitive content.

## What It Does
- **Batch URL Submission**: Processes multiple URLs automatically with rate limiting
- **Indexing Requests**: Submits URLs to Google for faster crawling and indexing
- **Deletion Requests**: Removes URLs from Google's index when content is removed
- **Rate Limit Compliance**: Built-in delays to respect Google's API quotas
- **Error Handling**: Comprehensive error tracking and reporting
- **Progress Monitoring**: Real-time feedback on submission status

## API Limits & Quotas
Google Indexing API has strict rate limits:
- **Daily Limit**: 200 URLs per day
- **Monthly Limit**: 600 URLs per month
- **Intended Use**: Primarily for job postings and livestream structured data
- **General Content**: Limited approval; mainly for high-value, time-sensitive pages

## Requirements
- Python 3.x
- Required packages: google-auth, google-api-python-client
- Google Cloud Service Account with Indexing API enabled
- Service account credentials JSON file
- Site ownership verification in Google Search Console

## Setup
1. **Create Google Cloud Project**
   - Enable Google Indexing API
   - Create service account
   - Download credentials JSON file

2. **Verify Site Ownership**
   - Add service account email to Search Console as owner
   - Verify you can access the property

3. **Install Dependencies**
   ```bash
   pip install google-auth google-api-python-client
   ```

4. **Configure Credentials**
   - Place credentials JSON file in project directory
   - Update `SERVICE_ACCOUNT_FILE` path in script

## Usage
**Basic execution:**
```bash
python indexing_api.py
```

**Configuration:**
- Update `urls_to_index` list with your URLs
- Modify `SERVICE_ACCOUNT_FILE` path
- Adjust delay timing if needed (currently 2 seconds between requests)

## Code Structure
**Key Components:**
- Service account authentication
- Indexing service initialization
- URL processing loop with error handling
- Rate limiting with delays
- Comprehensive result reporting

**Request Types:**
- `URL_UPDATED`: For new or updated content
- `URL_DELETED`: For removed content

## Features
- **Automatic Rate Limiting**: 2-second delay between requests
- **Comprehensive Logging**: Success/failure tracking for each URL
- **Error Details**: Full error messages for troubleshooting
- **Progress Updates**: Real-time status during processing
- **Batch Processing**: Handles large URL lists efficiently

## Input Format
URLs should be added to the `urls_to_index` list:
```python
urls_to_index = [
    'https://example.com/page1',
    'https://example.com/page2',
    # Add more URLs here
]
```

## Output
The script provides:
- Real-time progress updates
- Success/failure count
- Detailed error messages for failed submissions
- Summary statistics at completion

## Error Handling
Common errors and solutions:
- **Permission Denied**: Verify service account has Search Console access
- **Quota Exceeded**: Check daily/monthly limits
- **Invalid URL**: Ensure URLs are properly formatted and accessible
- **Authentication Failed**: Verify credentials file path and permissions

## Best Practices
- **Prioritize High-Value Content**: Use quota for most important pages
- **Monitor Quotas**: Track daily/monthly usage
- **Verify Ownership**: Ensure all domains are verified in Search Console
- **Test Small Batches**: Start with few URLs to verify setup
- **Regular Monitoring**: Check Search Console for indexing status

## Use Cases
- **New Template Pages**: Fast indexing of new presentation templates
- **Blog Post Publishing**: Expedite indexing of time-sensitive content
- **Product Launches**: Quick indexing of new product pages
- **Event Pages**: Fast indexing of time-limited event content
- **Press Releases**: Immediate indexing of news content

## Limitations
- **Quota Restrictions**: Limited daily/monthly submissions
- **Content Types**: Primarily intended for job postings and livestreams
- **No Guarantee**: API submission doesn't guarantee indexing
- **Approval Required**: General content use requires Google approval
- **Site Verification**: Must own all submitted domains

## Alternative Approaches
If quotas are insufficient:
- **XML Sitemaps**: Submit comprehensive sitemaps to Search Console
- **Internal Linking**: Improve crawlability through site structure
- **Social Signals**: Share content on social platforms
- **Manual Submission**: Use Search Console URL inspection tool
- **RSS Feeds**: Implement feeds for automatic discovery

## Monitoring Results
After submission:
- Check Search Console for indexing status
- Monitor organic traffic for submitted URLs
- Use URL inspection tool to verify indexing
- Track performance changes in analytics

## Security Considerations
- **Credential Protection**: Keep service account JSON secure
- **Access Control**: Limit service account permissions
- **Regular Rotation**: Periodically rotate credentials
- **Environment Variables**: Consider using env vars for sensitive data

## Troubleshooting
**Common Issues:**
- Service account email not added to Search Console
- Incorrect credentials file path
- URLs not owned by verified property
- Rate limits exceeded
- Invalid URL formats

**Debug Steps:**
1. Verify Search Console ownership
2. Check credentials file exists and is readable
3. Ensure URLs match verified properties
4. Monitor API quota usage
5. Test with single URL first