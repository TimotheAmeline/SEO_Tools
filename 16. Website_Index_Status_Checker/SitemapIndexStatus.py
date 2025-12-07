#!/usr/bin/env python3
"""
Sitemap Crawler + Google Search Console Index Checker
Crawls sitemaps and verifies indexing status via GSC API
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import pandas as pd
from datetime import datetime
import time
import json
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
from typing import List, Dict, Set
import argparse
import logging

class SitemapGSCChecker:
    def __init__(self, credentials_file: str = 'credentials.json', verbose: bool = True):
        """Initialize with GSC API credentials"""
        self.SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
        self.credentials_file = credentials_file
        self.service = None
        self.verbose = verbose
        self.setup_logging()
        print("\n🚀 SITEMAP + GSC INDEX CHECKER STARTING...")
        print(f"📁 Credentials file: {credentials_file}")
        print(f"🔍 Verbose mode: {'ON' if verbose else 'OFF'}")
        self.setup_gsc_api()
    
    def setup_logging(self):
        """Setup logging configuration"""
        if self.verbose:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
        self.logger = logging.getLogger(__name__)
    
    def setup_gsc_api(self):
        """Setup Google Search Console API authentication"""
        print("\n🔐 SETTING UP GSC API AUTHENTICATION...")
        creds = None
        
        # Check if credentials file exists
        if not os.path.exists(self.credentials_file):
            print(f"❌ ERROR: Credentials file not found: {self.credentials_file}")
            print("\n💡 TROUBLESHOOTING TIPS:")
            print("   1. Make sure your credentials.json file is in the correct location")
            print("   2. Check the file path and spelling")
            print("   3. For service account: download from Google Cloud Console")
            print("   4. For OAuth2: download from Google Developers Console")
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
        
        print(f"✅ Found credentials file: {self.credentials_file}")
        print(f"📊 File size: {os.path.getsize(self.credentials_file)} bytes")
        
        # Check if it's a service account file
        if self.credentials_file.endswith('.json'):
            try:
                print("🔄 Attempting service account authentication...")
                # Try service account first
                creds = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_file, scopes=self.SCOPES)
                print("✅ Service account authentication successful!")
                self.logger.info("Using service account authentication")
            except Exception as e:
                print(f"⚠️  Service account failed: {str(e)[:100]}...")
                print("🔄 Falling back to OAuth2 flow...")
                # Fall back to OAuth2 flow
                token_file = 'token.json'
                
                if os.path.exists(token_file):
                    print(f"📁 Found existing token file: {token_file}")
                    try:
                        creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
                        print("✅ Loaded existing OAuth2 credentials")
                    except Exception as token_error:
                        print(f"⚠️  Failed to load token: {token_error}")
                        creds = None
                
                if not creds or not creds.valid:
                    print("🔄 Creating new OAuth2 credentials...")
                    if creds and creds.expired and creds.refresh_token:
                        print("🔄 Refreshing expired credentials...")
                        try:
                            creds.refresh(Request())
                            print("✅ Credentials refreshed successfully!")
                        except Exception as refresh_error:
                            print(f"❌ Failed to refresh credentials: {refresh_error}")
                            creds = None
                    
                    if not creds:
                        print("🌐 Starting OAuth2 authorization flow...")
                        print("📱 A browser window should open for authorization")
                        try:
                            flow = InstalledAppFlow.from_client_secrets_file(
                                self.credentials_file, self.SCOPES)
                            creds = flow.run_local_server(port=0)
                            print("✅ OAuth2 authorization completed!")
                        except Exception as oauth_error:
                            print(f"❌ OAuth2 flow failed: {oauth_error}")
                            print("\n💡 TROUBLESHOOTING TIPS:")
                            print("   1. Make sure your credentials.json is a valid OAuth2 client file")
                            print("   2. Enable the Google Search Console API in Google Cloud Console")
                            print("   3. Add your email to the OAuth consent screen test users")
                            raise
                    
                    # Save credentials for future use
                    try:
                        with open(token_file, 'w') as token:
                            token.write(creds.to_json())
                        print(f"💾 Saved credentials to {token_file} for future use")
                    except Exception as save_error:
                        print(f"⚠️  Could not save token file: {save_error}")
        
        if not creds:
            print("❌ FATAL: Could not establish any valid credentials")
            raise Exception("Authentication failed - no valid credentials found")
        
        print("🔄 Building GSC API service...")
        try:
            self.service = build('searchconsole', 'v1', credentials=creds)
            print("✅ GSC API service built successfully!")
            
            # Test the connection
            print("🧪 Testing API connection...")
            try:
                sites_response = self.service.sites().list().execute()
                sites = sites_response.get('siteEntry', [])
                print(f"✅ API connection successful! Found {len(sites)} site(s) in your GSC account:")
                for site in sites[:5]:  # Show first 5 sites
                    permission_level = site.get('permissionLevel', 'Unknown')
                    print(f"   📊 {site.get('siteUrl', 'Unknown')} ({permission_level})")
                if len(sites) > 5:
                    print(f"   ... and {len(sites) - 5} more sites")
            except Exception as test_error:
                print(f"⚠️  API connection test failed: {test_error}")
                print("   API service created but unable to list sites")
                print("   This might still work for URL inspection")
        except Exception as build_error:
            print(f"❌ Failed to build GSC API service: {build_error}")
            print("\n💡 TROUBLESHOOTING TIPS:")
            print("   1. Check your internet connection")
            print("   2. Verify API credentials are valid")
            print("   3. Ensure Search Console API is enabled")
            raise
    
    def extract_urls_from_sitemap(self, sitemap_url: str, depth: int = 0) -> Set[str]:
        """Extract all URLs from a sitemap (handles nested sitemaps)"""
        urls = set()
        indent = "  " * depth
        
        try:
            print(f"{indent}🌐 Fetching sitemap: {sitemap_url}")
            self.logger.info(f"Fetching sitemap at depth {depth}: {sitemap_url}")
            
            # Add headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; GSC-SitemapChecker/1.0)'
            }
            
            start_time = time.time()
            response = requests.get(sitemap_url, timeout=30, allow_redirects=True, headers=headers)
            fetch_time = time.time() - start_time
            
            print(f"{indent}⏱️  Fetch time: {fetch_time:.2f}s")
            print(f"{indent}📊 Status code: {response.status_code}")
            print(f"{indent}📦 Content size: {len(response.content):,} bytes")
            print(f"{indent}📋 Content type: {response.headers.get('content-type', 'Unknown')}")
            
            response.raise_for_status()
            
            # Check if content looks like XML
            content_type = response.headers.get('content-type', '').lower()
            if 'xml' not in content_type and not sitemap_url.endswith('.xml'):
                print(f"{indent}⚠️  Warning: Content type doesn't indicate XML: {content_type}")
            
            print(f"{indent}🔍 Parsing XML content...")
            try:
                root = ET.fromstring(response.content)
                print(f"{indent}✅ XML parsed successfully")
            except ET.ParseError as parse_error:
                print(f"{indent}❌ XML parsing failed: {parse_error}")
                print(f"{indent}📄 First 200 chars of content: {response.text[:200]}...")
                return urls
            
            # Handle sitemap index (contains multiple sitemaps)
            sitemap_namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            # Check if this is a sitemap index
            sitemaps = root.findall('.//sitemap:sitemap', sitemap_namespaces)
            if sitemaps:
                print(f"{indent}📂 Found sitemap index with {len(sitemaps)} nested sitemaps")
                for i, sitemap in enumerate(sitemaps, 1):
                    loc = sitemap.find('sitemap:loc', sitemap_namespaces)
                    lastmod = sitemap.find('sitemap:lastmod', sitemap_namespaces)
                    
                    if loc is not None:
                        nested_sitemap_url = loc.text.strip()
                        lastmod_text = lastmod.text if lastmod is not None else "Unknown"
                        print(f"{indent}  📄 {i}/{len(sitemaps)}: {nested_sitemap_url} (Last modified: {lastmod_text})")
                        
                        # Recursive call with depth tracking
                        if depth < 5:  # Prevent infinite recursion
                            nested_urls = self.extract_urls_from_sitemap(nested_sitemap_url, depth + 1)
                            urls.update(nested_urls)
                            print(f"{indent}  ✅ Added {len(nested_urls)} URLs from nested sitemap")
                        else:
                            print(f"{indent}  ⚠️  Maximum recursion depth reached, skipping nested sitemap")
                    else:
                        print(f"{indent}  ❌ Sitemap entry {i} missing <loc> element")
            else:
                # Regular sitemap with URLs
                url_elements = root.findall('.//sitemap:url', sitemap_namespaces)
                print(f"{indent}📄 Regular sitemap with {len(url_elements)} URL entries")
                
                for i, url_elem in enumerate(url_elements):
                    loc = url_elem.find('sitemap:loc', sitemap_namespaces)
                    lastmod = url_elem.find('sitemap:lastmod', sitemap_namespaces)
                    priority = url_elem.find('sitemap:priority', sitemap_namespaces)
                    changefreq = url_elem.find('sitemap:changefreq', sitemap_namespaces)
                    
                    if loc is not None:
                        url = loc.text.strip()
                        urls.add(url)
                        
                        if self.verbose and i < 5:  # Show first 5 URLs in verbose mode
                            print(f"{indent}  🔗 {url}")
                            if lastmod is not None:
                                print(f"{indent}     📅 Last modified: {lastmod.text}")
                            if priority is not None:
                                print(f"{indent}     ⭐ Priority: {priority.text}")
                            if changefreq is not None:
                                print(f"{indent}     🔄 Change frequency: {changefreq.text}")
                    else:
                        print(f"{indent}  ❌ URL entry {i+1} missing <loc> element")
                
                if len(url_elements) > 5 and self.verbose:
                    print(f"{indent}  ... and {len(url_elements) - 5} more URLs")
                
                print(f"{indent}✅ Extracted {len(url_elements)} URLs from {sitemap_url}")
        
        except requests.exceptions.Timeout:
            print(f"{indent}❌ Timeout error: Sitemap took longer than 30 seconds to fetch")
            print(f"{indent}💡 Try checking if the sitemap URL is correct and accessible")
        except requests.exceptions.ConnectionError:
            print(f"{indent}❌ Connection error: Could not connect to {sitemap_url}")
            print(f"{indent}💡 Check your internet connection and the sitemap URL")
        except requests.exceptions.HTTPError as http_error:
            print(f"{indent}❌ HTTP error {response.status_code}: {http_error}")
            print(f"{indent}💡 The sitemap URL might be incorrect or the server is having issues")
        except Exception as e:
            print(f"{indent}❌ Unexpected error processing sitemap {sitemap_url}: {e}")
            print(f"{indent}💡 Error type: {type(e).__name__}")
            self.logger.error(f"Error processing sitemap {sitemap_url}: {e}", exc_info=True)
        
        return urls
    
    def check_url_indexing(self, site_property: str, urls: List[str]) -> Dict[str, Dict]:
        """Check indexing status for URLs via GSC API"""
        print(f"\n🔍 CHECKING INDEXING STATUS FOR {len(urls)} URLs...")
        print(f"🏠 Site property: {site_property}")
        
        results = {}
        
        # GSC API has rate limits, batch requests
        batch_size = 50  # Reduced batch size for better rate limiting
        total_batches = (len(urls) + batch_size - 1) // batch_size
        
        print(f"📦 Processing in {total_batches} batches of {batch_size} URLs each")
        print(f"⏱️  Estimated time: {total_batches * batch_size * 0.2 / 60:.1f} minutes")
        
        # Test the site property first
        print(f"\n🧪 Testing site property access...")
        try:
            test_url = urls[0] if urls else site_property
            test_request = {
                'inspectionUrl': test_url,
                'siteUrl': site_property
            }
            
            test_response = self.service.urlInspection().index().inspect(
                body=test_request
            ).execute()
            print(f"✅ Site property access confirmed!")
            
            # Show what we got from the test
            inspection_result = test_response.get('inspectionResult', {})
            index_status = inspection_result.get('indexStatusResult', {})
            print(f"   🔍 Test URL: {test_url}")
            print(f"   📊 Coverage state: {index_status.get('coverageState', 'UNKNOWN')}")
            print(f"   🔄 Indexing state: {index_status.get('indexingState', 'UNKNOWN')}")
            
        except Exception as test_error:
            print(f"❌ Site property test failed: {test_error}")
            print("\n💡 TROUBLESHOOTING TIPS:")
            print("   1. Check if the site property exists in your GSC account")
            print("   2. Verify you have permission to access this property")
            print("   3. Try different property formats:")
            print(f"      - https://example.com/ (URL prefix)")
            print(f"      - sc-domain:example.com (Domain property)")
            print("   4. Make sure the URLs belong to this property")
            
            # Ask user if they want to continue
            print("\n⚠️  Continuing despite test failure...")
        
        successful_requests = 0
        failed_requests = 0
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(urls))
            batch = urls[start_idx:end_idx]
            
            print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch)} URLs)")
            batch_start_time = time.time()
            
            # Process URLs in batch with progress tracking
            for url_idx, url in enumerate(batch):
                # Show a simple dot every 5 URLs to indicate activity
                if (url_idx + 1) % 5 == 0:
                    print(".", end="", flush=True)
                
                try:
                    # Use URL inspection API
                    request_body = {
                        'inspectionUrl': url,
                        'siteUrl': site_property
                    }
                    
                    response = self.service.urlInspection().index().inspect(
                        body=request_body
                    ).execute()
                    
                    inspection_result = response.get('inspectionResult', {})
                    index_status = inspection_result.get('indexStatusResult', {})
                    page_fetch_result = inspection_result.get('pageFetchResult', {})
                    
                    coverage_state = index_status.get('coverageState', 'UNKNOWN')
                    indexing_state = index_status.get('indexingState', 'UNKNOWN')
                    
                    results[url] = {
                        'coverage_state': coverage_state,
                        'indexing_state': indexing_state,
                        'last_crawl_time': index_status.get('lastCrawlTime'),
                        'crawled_as': index_status.get('crawledAs'),
                        'verdict': index_status.get('verdict'),
                        'page_fetch_state': page_fetch_result.get('fetchState'),
                        'robots_txt_state': index_status.get('robotsTxtState'),
                        'mobile_usability_verdict': inspection_result.get('mobileUsabilityResult', {}).get('verdict')
                    }
                    
                    successful_requests += 1
                    
                    # Show progress for first few URLs in verbose mode
                    if self.verbose and url_idx < 3:
                        print(f"     🔗 {url}")
                        print(f"       📊 Coverage: {coverage_state}")
                        print(f"       🔄 Indexing: {indexing_state}")
                        if index_status.get('lastCrawlTime'):
                            print(f"       📅 Last crawl: {index_status.get('lastCrawlTime')}")
                    
                    # Show progress every 10 URLs
                    if (url_idx + 1) % 10 == 0:
                        batch_progress = ((url_idx + 1) / len(batch)) * 100
                        overall_processed = (batch_num * batch_size) + (url_idx + 1)
                        overall_progress = (overall_processed / len(urls)) * 100
                        
                        # Count current status
                        indexed_so_far = sum(1 for r in results.values() if r.get('coverage_state') == 'Indexed')
                        errors_so_far = sum(1 for r in results.values() if 'ERROR' in r.get('coverage_state', ''))
                        
                        print(f"     ⏳ Batch Progress: {url_idx + 1}/{len(batch)} ({batch_progress:.1f}%)")
                        print(f"     📊 Overall Progress: {overall_processed:,}/{len(urls):,} ({overall_progress:.1f}%)")
                        print(f"     ✅ Indexed so far: {indexed_so_far:,} | ❌ Errors: {errors_so_far:,}")
                        print(f"     🔗 Current URL: {url[:80]}{'...' if len(url) > 80 else ''}")
                        
                        # Estimate remaining time
                        elapsed_time = time.time() - batch_start_time
                        if url_idx > 0:
                            avg_time_per_url = elapsed_time / (url_idx + 1)
                            remaining_urls_in_batch = len(batch) - (url_idx + 1)
                            remaining_batches = total_batches - batch_num - 1
                            total_remaining_urls = remaining_urls_in_batch + (remaining_batches * batch_size)
                            estimated_remaining = avg_time_per_url * total_remaining_urls
                            print(f"     ⏱️  Estimated time remaining: {estimated_remaining / 60:.1f} minutes")
                        print("     " + "-" * 50)
                    
                    # Rate limiting - be more conservative
                    time.sleep(0.2)
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"\n❌ Error checking {url}: {error_msg[:100]}...")
                    
                    # Categorize errors
                    if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                        print("⏳ Rate limit hit, waiting 60 seconds...")
                        time.sleep(60)
                        # Retry once
                        try:
                            response = self.service.urlInspection().index().inspect(
                                body=request_body
                            ).execute()
                            # Process successful retry...
                            print("✅ Retry successful")
                            successful_requests += 1
                        except:
                            failed_requests += 1
                            results[url] = {
                                'coverage_state': 'ERROR',
                                'error': error_msg
                            }
                    elif "permission" in error_msg.lower() or "access" in error_msg.lower():
                        print("🔒 Permission error - check site property access")
                        failed_requests += 1
                        results[url] = {
                            'coverage_state': 'PERMISSION_ERROR',
                            'error': error_msg
                        }
                    else:
                        failed_requests += 1
                        results[url] = {
                            'coverage_state': 'ERROR',
                            'error': error_msg
                        }
                    
                    time.sleep(1)  # Longer delay on error
            
            batch_time = time.time() - batch_start_time
            remaining_batches = total_batches - batch_num - 1
            estimated_remaining_time = remaining_batches * batch_time
            
            # Batch summary
            batch_successful = len([r for r in results.values() if r.get('coverage_state') not in ['ERROR', 'PERMISSION_ERROR']])
            batch_indexed = len([r for r in results.values() if r.get('coverage_state') == 'Indexed'])
            
            print(f"\n✅ Batch {batch_num + 1}/{total_batches} completed in {batch_time:.1f}s")
            print(f"   📊 Processed: {len(batch)} URLs")
            print(f"   ✅ Successful requests: {successful_requests:,}")
            print(f"   ❌ Failed requests: {failed_requests:,}")
            print(f"   🔍 Currently indexed: {batch_indexed:,}")
            
            if remaining_batches > 0:
                print(f"   ⏱️  Estimated time remaining: {estimated_remaining_time / 60:.1f} minutes")
                print(f"   📦 Batches remaining: {remaining_batches}")
            
            # Brief pause between batches
            if batch_num < total_batches - 1:
                time.sleep(2)
        
        print(f"\n📊 INDEXING CHECK SUMMARY:")
        print(f"   ✅ Successful requests: {successful_requests:,}")
        print(f"   ❌ Failed requests: {failed_requests:,}")
        print(f"   📊 Success rate: {(successful_requests / len(urls) * 100):.1f}%")
        
        return results
    
    def generate_report(self, sitemap_urls: List[str], results: Dict, output_file: str = None):
        """Generate comprehensive report"""
        print(f"\n📋 GENERATING COMPREHENSIVE REPORT...")
        
        # Flatten data for DataFrame
        report_data = []
        
        for url, data in results.items():
            row = {
                'url': url,
                'coverage_state': data.get('coverage_state', 'UNKNOWN'),
                'indexing_state': data.get('indexing_state', 'UNKNOWN'),
                'last_crawl_time': data.get('last_crawl_time', ''),
                'crawled_as': data.get('crawled_as', ''),
                'verdict': data.get('verdict', ''),
                'page_fetch_state': data.get('page_fetch_state', ''),
                'robots_txt_state': data.get('robots_txt_state', ''),
                'mobile_usability_verdict': data.get('mobile_usability_verdict', ''),
                'error': data.get('error', '')
            }
            report_data.append(row)
        
        df = pd.DataFrame(report_data)
        
        # Summary stats
        total_urls = len(df)
        if total_urls == 0:
            print("❌ No URLs to analyze!")
            return df
        
        indexed_urls = len(df[df['coverage_state'] == 'Indexed'])
        not_indexed = len(df[df['coverage_state'] != 'Indexed'])
        errors = len(df[df['coverage_state'].str.contains('ERROR', na=False)])
        
        print(f"\n📊 INDEXING REPORT SUMMARY")
        print(f"=" * 50)
        print(f"📈 Total URLs checked: {total_urls:,}")
        print(f"✅ Indexed: {indexed_urls:,} ({indexed_urls/total_urls*100:.1f}%)")
        print(f"❌ Not indexed: {not_indexed:,} ({not_indexed/total_urls*100:.1f}%)")
        print(f"🚫 Errors: {errors:,} ({errors/total_urls*100:.1f}%)")
        
        # Coverage state breakdown
        print(f"\n📊 DETAILED COVERAGE STATE BREAKDOWN")
        print(f"=" * 50)
        coverage_counts = df['coverage_state'].value_counts()
        for state, count in coverage_counts.items():
            percentage = count/total_urls*100
            status_emoji = {
                'Indexed': '✅',
                'Valid with warning': '⚠️',
                'Error': '❌',
                'Valid but not submitted': '📋',
                'ERROR': '🚫',
                'PERMISSION_ERROR': '🔒',
                'UNKNOWN': '❓'
            }.get(state, '📊')
            print(f"{status_emoji} {state}: {count:,} ({percentage:.1f}%)")
        
        # Indexing state breakdown if available
        if 'indexing_state' in df.columns:
            indexing_counts = df['indexing_state'].value_counts()
            if len(indexing_counts) > 1:  # Only show if there's variety
                print(f"\n🔄 INDEXING STATE BREAKDOWN")
                print(f"=" * 50)
                for state, count in indexing_counts.items():
                    if state and state != 'UNKNOWN':
                        percentage = count/total_urls*100
                        print(f"   {state}: {count:,} ({percentage:.1f}%)")
        
        # Show problematic URLs
        problematic = df[df['coverage_state'].isin(['Error', 'ERROR', 'PERMISSION_ERROR'])]
        if len(problematic) > 0:
            print(f"\n🚨 PROBLEMATIC URLS ({len(problematic)} found)")
            print(f"=" * 50)
            for _, row in problematic.head(10).iterrows():
                print(f"❌ {row['url']}")
                if row['error']:
                    print(f"   Error: {row['error'][:100]}...")
            if len(problematic) > 10:
                print(f"   ... and {len(problematic) - 10} more problematic URLs")
        
        # Show recently crawled URLs
        recent_crawls = df[df['last_crawl_time'].notna() & (df['last_crawl_time'] != '')]
        if len(recent_crawls) > 0:
            print(f"\n🕒 RECENTLY CRAWLED URLS ({len(recent_crawls)} found)")
            print(f"=" * 50)
            # Sort by last crawl time if possible
            try:
                recent_crawls['crawl_datetime'] = pd.to_datetime(recent_crawls['last_crawl_time'])
                recent_crawls = recent_crawls.sort_values('crawl_datetime', ascending=False)
            except:
                pass
            
            for _, row in recent_crawls.head(5).iterrows():
                print(f"🕒 {row['url']}")
                print(f"   Last crawled: {row['last_crawl_time']}")
                print(f"   Status: {row['coverage_state']}")
        
        # Save detailed report
        if output_file:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                df.to_csv(output_file, index=False)
                file_size = os.path.getsize(output_file)
                print(f"\n💾 REPORT SAVED")
                print(f"=" * 50)
                print(f"📁 File: {output_file}")
                print(f"📊 Size: {file_size:,} bytes")
                print(f"📋 Rows: {len(df):,}")
                print(f"📝 Columns: {len(df.columns)}")
                
                # Show column names for reference
                print(f"\n📝 Available columns in the report:")
                for col in df.columns:
                    non_empty = len(df[df[col].notna() & (df[col] != '')])
                    print(f"   • {col}: {non_empty:,}/{total_urls:,} populated")
                    
            except Exception as save_error:
                print(f"❌ Failed to save report: {save_error}")
        
        return df
    
    def run_full_check(self, site_property: str, sitemap_urls: List[str], output_file: str = None):
        """Run complete sitemap + GSC check"""
        
        print("\n" + "=" * 60)
        print("🚀 STARTING SITEMAP + GSC INDEX CHECK")
        print("=" * 60)
        print(f"🏠 Site property: {site_property}")
        print(f"🗂️  Sitemaps to check: {len(sitemap_urls)}")
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # List all sitemaps
        print(f"\n📋 SITEMAP LIST:")
        for i, sitemap_url in enumerate(sitemap_urls, 1):
            print(f"   {i}. {sitemap_url}")
        
        # Extract all URLs from sitemaps
        print(f"\n" + "=" * 60)
        print("📥 EXTRACTING URLS FROM SITEMAPS")
        print("=" * 60)
        
        all_urls = set()
        sitemap_summary = []
        
        for i, sitemap_url in enumerate(sitemap_urls, 1):
            print(f"\n🔄 Processing sitemap {i}/{len(sitemap_urls)}: {sitemap_url}")
            start_time = time.time()
            
            urls = self.extract_urls_from_sitemap(sitemap_url)
            
            processing_time = time.time() - start_time
            urls_before = len(all_urls)
            all_urls.update(urls)
            new_urls_added = len(all_urls) - urls_before
            
            summary = {
                'sitemap': sitemap_url,
                'urls_found': len(urls),
                'new_urls_added': new_urls_added,
                'processing_time': processing_time
            }
            sitemap_summary.append(summary)
            
            print(f"   📊 Found: {len(urls):,} URLs")
            print(f"   ➕ New unique URLs: {new_urls_added:,}")
            print(f"   ⏱️  Processing time: {processing_time:.1f}s")
            print(f"   📈 Total unique URLs so far: {len(all_urls):,}")
        
        print(f"\n" + "=" * 60)
        print("📊 SITEMAP EXTRACTION SUMMARY")
        print("=" * 60)
        total_found = sum(s['urls_found'] for s in sitemap_summary)
        total_time = sum(s['processing_time'] for s in sitemap_summary)
        
        print(f"📈 Total URLs found across all sitemaps: {total_found:,}")
        print(f"🔗 Total unique URLs: {len(all_urls):,}")
        print(f"📊 Duplicate URLs filtered: {total_found - len(all_urls):,}")
        print(f"⏱️  Total extraction time: {total_time:.1f}s")
        
        if len(all_urls) == 0:
            print("\n❌ FATAL ERROR: No URLs found in any sitemap!")
            print("💡 TROUBLESHOOTING:")
            print("   1. Check if sitemap URLs are accessible")
            print("   2. Verify sitemap format is valid XML")
            print("   3. Check for network connectivity issues")
            return None
        
        # Provide URL samples
        sample_urls = list(all_urls)[:5]
        print(f"\n🔍 Sample URLs found:")
        for i, url in enumerate(sample_urls, 1):
            print(f"   {i}. {url}")
        if len(all_urls) > 5:
            print(f"   ... and {len(all_urls) - 5:,} more URLs")
        
        # Check indexing status
        print(f"\n" + "=" * 60)
        print("🔍 CHECKING INDEXING STATUS VIA GSC API")
        print("=" * 60)
        
        indexing_start_time = time.time()
        results = self.check_url_indexing(site_property, list(all_urls))
        indexing_time = time.time() - indexing_start_time
        
        print(f"\n⏱️  Total indexing check time: {indexing_time / 60:.1f} minutes")
        
        # Generate report
        print(f"\n" + "=" * 60)
        print("📋 GENERATING FINAL REPORT")
        print("=" * 60)
        
        report = self.generate_report(sitemap_urls, results, output_file)
        
        total_time = time.time() - indexing_start_time
        print(f"\n🏁 PROCESS COMPLETED")
        print(f"=" * 60)
        print(f"⏱️  Total execution time: {total_time / 60:.1f} minutes")
        print(f"📊 Processing rate: {len(all_urls) / total_time:.1f} URLs/second")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description='Check sitemap URLs indexing status via GSC API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Check single sitemap
  python SitemapIndexStatus.py --site "https://example.com/" --sitemaps "https://example.com/sitemap.xml"
  
  # Check multiple sitemaps
  python SitemapIndexStatus.py --site "https://example.com/" --sitemaps "https://example.com/sitemap.xml" "https://example.com/news-sitemap.xml"
  
  # Domain property format
  python SitemapIndexStatus.py --site "sc-domain:example.com" --sitemaps "https://example.com/sitemap.xml"
  
  # Custom output file
  python SitemapIndexStatus.py --site "https://example.com/" --sitemaps "https://example.com/sitemap.xml" --output "my_report.csv"
  
  # Quiet mode (less verbose)
  python SitemapIndexStatus.py --site "https://example.com/" --sitemaps "https://example.com/sitemap.xml" --quiet"""
    )
    
    parser.add_argument('--site', required=True, 
                       help='GSC site property (e.g., https://example.com/ or sc-domain:example.com)')
    parser.add_argument('--sitemaps', required=True, nargs='+', 
                       help='Sitemap URLs to check (space-separated for multiple)')
    parser.add_argument('--output', 
                       help='Output CSV file path (default: auto-generated with timestamp)')
    parser.add_argument('--credentials', default='credentials.json', 
                       help='GSC API credentials file (default: credentials.json)')
    parser.add_argument('--quiet', action='store_true', 
                       help='Reduce verbose output')
    
    print("🚀 Sitemap + GSC Index Checker v2.0")
    print("📧 Checking sitemap URLs against Google Search Console")
    
    try:
        args = parser.parse_args()
    except SystemExit:
        print("\n💡 QUICK START EXAMPLES:")
        print("   python SitemapIndexStatus.py --site 'https://example.com/' --sitemaps 'https://example.com/sitemap.xml'")
        print("   python SitemapIndexStatus.py --site 'sc-domain:example.com' --sitemaps 'https://example.com/sitemap.xml'")
        return
    
    # Validate inputs
    print(f"\n🔍 VALIDATING INPUTS...")
    
    # Validate site property format
    site = args.site.strip()
    if not (site.startswith('http') or site.startswith('sc-domain:')):
        print(f"⚠️  Warning: Site property '{site}' doesn't look like a standard format")
        print(f"   Expected formats:")
        print(f"   - https://example.com/ (URL prefix property)")
        print(f"   - sc-domain:example.com (Domain property)")
    
    # Validate sitemap URLs
    valid_sitemaps = []
    for sitemap in args.sitemaps:
        sitemap = sitemap.strip()
        if sitemap.startswith('http') and ('.xml' in sitemap or 'sitemap' in sitemap.lower()):
            valid_sitemaps.append(sitemap)
            print(f"✅ Valid sitemap: {sitemap}")
        else:
            print(f"⚠️  Warning: '{sitemap}' doesn't look like a sitemap URL")
            valid_sitemaps.append(sitemap)  # Include anyway, but warn
    
    if not valid_sitemaps:
        print("❌ No valid sitemap URLs provided!")
        return
    
    # Check credentials file
    if not os.path.exists(args.credentials):
        print(f"❌ Credentials file not found: {args.credentials}")
        print(f"\n💡 SETUP INSTRUCTIONS:")
        print(f"   1. Go to Google Cloud Console (console.cloud.google.com)")
        print(f"   2. Enable the Google Search Console API")
        print(f"   3. Create credentials (Service Account or OAuth2)")
        print(f"   4. Download the JSON file and save as '{args.credentials}'")
        return
    
    print(f"✅ Found credentials file: {args.credentials}")
    
    # Initialize checker
    try:
        verbose = not args.quiet
        checker = SitemapGSCChecker(args.credentials, verbose=verbose)
    except Exception as init_error:
        print(f"❌ Failed to initialize GSC checker: {init_error}")
        return
    
    # Generate output filename if not provided
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"sitemap_index_report_{timestamp}.csv"
    
    print(f"📁 Output will be saved to: {output_file}")
    
    # Run the check
    try:
        start_time = time.time()
        report = checker.run_full_check(
            site_property=site,
            sitemap_urls=valid_sitemaps,
            output_file=output_file
        )
        
        if report is not None:
            print(f"\n🎉 SUCCESS! Check completed successfully.")
            print(f"📊 Results available in: {output_file}")
        else:
            print(f"\n❌ Check failed or no data collected.")
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Process interrupted by user")
    except Exception as run_error:
        print(f"\n❌ Unexpected error during execution: {run_error}")
        print(f"💡 Try running with --quiet flag or check your inputs")
        if verbose:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()


# Example usage:
# python SEOTools/SitemapIndexStatus/SitemapIndexStatus.py \
#  --site "sc-domain:example.com" \
#  --sitemaps "https://example.com/sitemap.xml" "https://www.example.com/templates-sitemap.xml" \
#  --credentials "SEOTools/gsc-analyzer/service_account.json" \
#  --output "SEOTools/SitemapIndexStatus/report.csv"
