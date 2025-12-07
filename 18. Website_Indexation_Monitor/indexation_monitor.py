import requests
from bs4 import BeautifulSoup
import logging
import os
import json
import csv
from datetime import datetime
import argparse
import time
import random
import gzip
from io import BytesIO
from urllib.parse import urlparse

# Setup directories
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")
logs_dir = os.path.join(script_dir, "logs")
reports_dir = os.path.join(script_dir, "reports")

# Create directories if they don't exist
os.makedirs(data_dir, exist_ok=True)
os.makedirs(logs_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

# Setup logging
logging.basicConfig(
    filename=os.path.join(logs_dir, 'indexation_monitor.log'),
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# File to store approved noindex URLs
APPROVED_NOINDEX_FILE = os.path.join(data_dir, 'approved_noindex_urls.json')
# File to store the last check results
LAST_RESULTS_FILE = os.path.join(data_dir, 'last_check_results.json')

# Base configurations (overridden by CLI)
BASE_URL = "https://example.com"
SITEMAP_URLS = [
    "https://www.example.com/sitemap.xml",
    "https://www.example.com/templates-sitemap.xml",
]

# Load approved noindex URLs
def load_approved_noindex_urls():
    if os.path.exists(APPROVED_NOINDEX_FILE):
        with open(APPROVED_NOINDEX_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save approved noindex URLs
def save_approved_noindex_urls(approved_urls):
    with open(APPROVED_NOINDEX_FILE, 'w') as f:
        json.dump(approved_urls, f, indent=2)

# Load last check results
def load_last_results():
    if os.path.exists(LAST_RESULTS_FILE):
        with open(LAST_RESULTS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save last check results
def save_last_results(results):
    with open(LAST_RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

# Send macOS notification
def send_notification(title, message):
    os.system(f"""
    osascript -e 'display notification "{message}" with title "{title}" sound name "Basso"'
    """)
    
    # Also log to a special alerts file
    with open(os.path.join(logs_dir, 'indexation_alerts.log'), 'a') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {title} - {message}\n")
    
    logging.warning(f"Alert: {title} - {message}")

# Parse a sitemap XML file using regex for reliable extraction
def parse_sitemap(sitemap_content, is_gzip=False):
    urls = []
    
    try:
        if is_gzip:
            with gzip.GzipFile(fileobj=BytesIO(sitemap_content), mode='rb') as f:
                content = f.read()
        else:
            content = sitemap_content
            
        # Convert to string if it's bytes
        if isinstance(content, bytes):
            content_str = content.decode('utf-8')
        else:
            content_str = content
            
        # Parse with regular expressions (more reliable than XML parsing for sitemaps)
        import re
        
        # Check if this is a sitemap index
        if '<sitemapindex' in content_str:
            # Extract sitemap URLs from sitemap index
            sitemap_matches = re.findall(r'<loc>(https?://[^<]+)</loc>', content_str)
            for url in sitemap_matches:
                urls.append(('sitemap', url.strip()))
        else:
            # Extract page URLs from regular sitemap
            url_matches = re.findall(r'<loc>(https?://[^<]+)</loc>', content_str)
            for url in url_matches:
                urls.append(('url', url.strip()))
            
        logging.info(f"Parsed sitemap with {len(urls)} entries")
            
    except Exception as e:
        logging.error(f"Error parsing sitemap: {e}")
    
    return urls

# Fetch URLs from sitemap(s)
def get_urls_from_sitemaps(base_url: str, sitemap_urls: list):
    all_urls = []
    sitemaps_to_process = sitemap_urls.copy()
    processed_sitemaps = set()
    
    print(f"Starting with {len(sitemaps_to_process)} sitemaps to process")
    
    while sitemaps_to_process:
        sitemap_url = sitemaps_to_process.pop(0)
        
        if sitemap_url in processed_sitemaps:
            continue
            
        processed_sitemaps.add(sitemap_url)
        print(f"Fetching sitemap: {sitemap_url}")
        logging.info(f"Fetching sitemap: {sitemap_url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            }
            
            response = requests.get(sitemap_url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                logging.error(f"Error fetching sitemap {sitemap_url}: HTTP {response.status_code}")
                continue
            
            # Check if this is a gzipped sitemap
            is_gzip = sitemap_url.endswith('.gz')
            
            # Parse the sitemap content
            urls = parse_sitemap(response.content, is_gzip)
            
            # Process the extracted URLs
            for url_type, url in urls:
                if url_type == 'sitemap' and url not in processed_sitemaps:
                    sitemaps_to_process.append(url)
                elif url_type == 'url':
                    # Only include URLs from our domain
                    if urlparse(url).netloc in ['example.com', 'www.example.com']:
                        all_urls.append(url)
            
            # Be nice to the server
            time.sleep(random.uniform(0.5, 1))
            
        except Exception as e:
            logging.error(f"Error fetching sitemap {sitemap_url}: {e}")
    
    # Add the homepage as it's sometimes missing from sitemaps
    if base_url not in all_urls and f"https://www.{base_url.replace('https://', '')}" not in all_urls:
        homepage = f"https://www.{base_url.replace('https://', '')}"
        all_urls.append(homepage)
        
    # Remove duplicates and sort
    all_urls = sorted(list(set(all_urls)))
    
    print(f"Total unique URLs found in sitemaps: {len(all_urls)}")
    logging.info(f"Total unique URLs found in sitemaps: {len(all_urls)}")
    
    return all_urls

# Check for robots meta tags and headers
def check_indexation(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        result = {
            'url': url,
            'status_code': response.status_code,
            'noindex': False,
            'reason': None,
            'redirect_url': None,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Check if there was a redirect
        if response.history:
            result['redirect_url'] = response.url
            logging.info(f"Redirect detected for {url} → {response.url}")
        
        # Check HTTP headers for X-Robots-Tag
        x_robots = response.headers.get('X-Robots-Tag', '')
        if 'noindex' in x_robots.lower():
            result['noindex'] = True
            result['reason'] = f"X-Robots-Tag: {x_robots}"
            logging.info(f"Noindex in X-Robots-Tag for {url}: {x_robots}")
            return result
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check meta robots tags
        meta_robots = soup.find_all('meta', attrs={'name': 'robots'})
        for tag in meta_robots:
            content = tag.get('content', '').lower()
            if 'noindex' in content:
                result['noindex'] = True
                result['reason'] = f"meta robots: {content}"
                logging.info(f"Noindex in meta robots for {url}: {content}")
                return result
        
        # Also check for meta name="googlebot"
        meta_googlebot = soup.find_all('meta', attrs={'name': 'googlebot'})
        for tag in meta_googlebot:
            content = tag.get('content', '').lower()
            if 'noindex' in content:
                result['noindex'] = True
                result['reason'] = f"meta googlebot: {content}"
                logging.info(f"Noindex in meta googlebot for {url}: {content}")
                return result
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error checking {url}: {error_msg}")
        return {
            'url': url,
            'status_code': None,
            'noindex': None,
            'reason': f"Error: {error_msg}",
            'redirect_url': None,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# Check all URLs and return results
def check_all_urls(urls_to_check):
    results = {}
    total_urls = len(urls_to_check)
    
    print(f"Starting indexation check on {total_urls} URLs...")
    
    for i, url in enumerate(urls_to_check):
        # Show progress every 10 URLs or at beginning/end
        if (i + 1) % 10 == 0 or i == 0 or i == total_urls - 1:
            print(f"Progress: {i + 1}/{total_urls} URLs checked ({((i + 1) / total_urls) * 100:.1f}%)")
        
        # Check indexation status
        result = check_indexation(url)
        results[url] = result
        
        # Be nice to the server - reduced delay for faster operation
        time.sleep(random.uniform(0.3, 0.7))
    
    return results

# Analyze results and find issues
def analyze_results(check_results, approved_noindex_urls):
    new_noindex_urls = {}
    missing_urls = []
    status_issues = {}
    
    # Find new noindexed URLs and status issues
    for url, result in check_results.items():
        # Check for noindex
        if result['noindex'] and url not in approved_noindex_urls:
            new_noindex_urls[url] = result['reason']
        
        # Check for status code issues (non-200 responses)
        status_code = result['status_code']
        if status_code is None:
            status_issues[url] = "Connection error"
        elif status_code >= 300:
            if status_code >= 300 and status_code < 400:
                status_issues[url] = f"Redirect (HTTP {status_code})"
                if result['redirect_url']:
                    status_issues[url] += f" → {result['redirect_url']}"
            elif status_code >= 400 and status_code < 500:
                status_issues[url] = f"Client error (HTTP {status_code})"
            elif status_code >= 500:
                status_issues[url] = f"Server error (HTTP {status_code})"
    
    # Find URLs that were present in the last check but not in this one
    last_results = load_last_results()
    if last_results:
        for url in last_results:
            if url not in check_results and url not in approved_noindex_urls:
                missing_urls.append(url)
    
    return new_noindex_urls, missing_urls, status_issues

# Generate CSV report with all issues
def generate_csv_report(check_results, approved_noindex_urls, status_issues):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = os.path.join(reports_dir, f'indexation_report_{timestamp}.csv')
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Status Code', 'Issue Type', 'Details', 'Approved', 'Checked At'])
        
        # First add noindex URLs
        for url, result in sorted(check_results.items()):
            if result['noindex']:
                writer.writerow([
                    url,
                    result['status_code'],
                    'Noindex',
                    result['reason'],
                    'Yes' if url in approved_noindex_urls else 'No',
                    result['checked_at']
                ])
        
        # Then add URLs with status issues
        for url, issue in sorted(status_issues.items()):
            result = check_results[url]
            writer.writerow([
                url,
                result['status_code'],
                'Status Issue',
                issue,
                'N/A',
                result['checked_at']
            ])
    
    print(f"CSV report generated: {csv_file}")
    return csv_file

# Generate a report for notifications
def generate_summary(new_noindex_urls, missing_urls, status_issues, check_results, csv_file):
    total_urls = len(check_results)
    total_noindex = sum(1 for result in check_results.values() if result['noindex'])
    approved_noindex = len(load_approved_noindex_urls())
    error_count = sum(1 for result in check_results.values() if result['status_code'] is None)
    
    summary = f"Indexation Check Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    summary += f"{'=' * 50}\n"
    summary += f"Total URLs checked: {total_urls}\n"
    summary += f"URLs with noindex: {total_noindex}\n"
    summary += f"Previously approved noindex: {approved_noindex}\n"
    summary += f"URLs with connection errors: {error_count}\n"
    summary += f"URLs with status issues (3xx/4xx/5xx): {len(status_issues)}\n"
    summary += f"CSV Report: {os.path.basename(csv_file)}\n"
    
    if new_noindex_urls:
        summary += f"\n{'*' * 20} NEW NOINDEX ISSUES ({len(new_noindex_urls)}) {'*' * 20}\n"
        summary += "These URLs may require attention:\n"
        for url, reason in new_noindex_urls.items():
            summary += f"- {url}: {reason}\n"
    else:
        summary += "\n✅ No new indexation issues found.\n"
    
    if status_issues:
        summary += f"\n{'*' * 20} STATUS ISSUES ({len(status_issues)}) {'*' * 20}\n"
        summary += "These URLs in the sitemap have status code issues:\n"
        # Show first 10 issues, then summarize the rest
        items = list(status_issues.items())
        for url, issue in items[:10]:
            summary += f"- {url}: {issue}\n"
        if len(items) > 10:
            summary += f"... and {len(items) - 10} more status issues (see CSV report for all)\n"
    
    if missing_urls:
        summary += f"\n{'*' * 20} MISSING URLS ({len(missing_urls)}) {'*' * 20}\n"
        summary += "These URLs were present in the last check but not found now:\n"
        # Show first 10 missing URLs, then summarize the rest
        for url in missing_urls[:10]:
            summary += f"- {url}\n"
        if len(missing_urls) > 10:
            summary += f"... and {len(missing_urls) - 10} more missing URLs (see CSV report for all)\n"
    
    return summary

# Approve a noindex URL (for interactive mode)
def approve_noindex_url(url, reason):
    approved_urls = load_approved_noindex_urls()
    approved_urls[url] = reason
    save_approved_noindex_urls(approved_urls)
    logging.info(f"Approved noindex for URL: {url}")
    print(f"✅ Approved noindex for: {url}")

# Main function
def main(interactive=False):
    start_time = datetime.now()
    logging.info(f"Starting indexation monitoring at {start_time}")
    
    print("🔍 Fetching URLs from sitemaps...")
    all_urls = get_urls_from_sitemaps(BASE_URL, SITEMAP_URLS)
    
    print(f"Found {len(all_urls)} URLs in sitemaps.")
    
    if len(all_urls) == 0:
        print("No URLs found! Check the sitemap URLs configuration.")
        return
        
    print("🔍 Checking indexation status of all URLs...")
    check_results = check_all_urls(all_urls)
    
    # Save this check for future reference
    save_last_results(check_results)
    
    approved_noindex_urls = load_approved_noindex_urls()
    new_noindex_urls, missing_urls, status_issues = analyze_results(check_results, approved_noindex_urls)
    
    # Generate CSV report with all issues
    csv_file = generate_csv_report(check_results, approved_noindex_urls, status_issues)
    
    # Generate summary report
    summary = generate_summary(new_noindex_urls, missing_urls, status_issues, check_results, csv_file)
    
    # Write full report to file
    report_file = os.path.join(logs_dir, f"report_{start_time.strftime('%Y%m%d_%H%M%S')}.txt")
    with open(report_file, 'w') as f:
        f.write(summary)
        f.write("\n\n")
        f.write("DETAILED RESULTS:\n")
        f.write("=" * 50 + "\n")
        for url, result in sorted(check_results.items()):
            if result['noindex'] or url in status_issues:
                f.write(f"URL: {url}\n")
                f.write(f"Status: {result['status_code']}\n")
                if result['redirect_url']:
                    f.write(f"Redirects to: {result['redirect_url']}\n")
                f.write(f"Noindex: {result['noindex']}\n")
                if result['reason']:
                    f.write(f"Reason: {result['reason']}\n")
                if url in status_issues:
                    f.write(f"Status Issue: {status_issues[url]}\n")
                f.write(f"Checked at: {result['checked_at']}\n")
                f.write("-" * 50 + "\n")
    
    # Show notification with summary of all issues
    total_issues = len(new_noindex_urls) + len(missing_urls) + len(status_issues)
    if total_issues > 0:
        issue_breakdown = []
        if new_noindex_urls:
            issue_breakdown.append(f"{len(new_noindex_urls)} noindex")
        if status_issues:
            issue_breakdown.append(f"{len(status_issues)} status issues")
        if missing_urls:
            issue_breakdown.append(f"{len(missing_urls)} missing")
            
        issue_summary = ", ".join(issue_breakdown)
        
        send_notification(
            f"⚠️ {total_issues} Indexation Issues Found", 
            f"Issues: {issue_summary}. CSV report generated."
        )
    else:
        send_notification(
            "✅ No Indexation Issues Found", 
            f"All {len(check_results)} pages checked. No issues detected."
        )
    
    print("\n" + summary)
    
    # Interactive mode for approving noindex URLs
    if interactive and new_noindex_urls:
        print("\n🔄 Interactive Mode: Review and approve noindex URLs")
        for url, reason in new_noindex_urls.items():
            response = input(f"URL: {url}\nReason: {reason}\nApprove this noindex? (y/n): ")
            if response.lower() == 'y':
                approve_noindex_url(url, reason)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logging.info(f"Completed indexation monitoring in {duration:.2f} seconds")
    print(f"\n✅ Monitoring completed in {duration:.2f} seconds")
    print(f"CSV report saved to: {csv_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor website indexation status")
    parser.add_argument("--base-url", default=BASE_URL, help="Base site URL")
    parser.add_argument("--sitemaps", nargs="*", default=SITEMAP_URLS, help="Sitemap URLs to process")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode to approve noindex URLs")
    args = parser.parse_args()

    main(base_url=args.base_url, sitemap_urls=args.sitemaps, interactive=args.interactive)
