import pandas as pd
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
import argparse
import io
import gzip
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional, Set

class GSCComparisonTool:
    def __init__(self, credentials_path: str):
        """Initialize GSC and GA4 API connections"""
        self.gsc_service = None
        self.ga_service = None
        self.setup_apis(credentials_path)
    
    def setup_apis(self, credentials_path: str):
        """Setup Google Search Console and GA4 APIs"""
        try:
            credentials = Credentials.from_service_account_file(
                credentials_path, 
                scopes=[
                    'https://www.googleapis.com/auth/webmasters.readonly',
                    'https://www.googleapis.com/auth/analytics.readonly'
                ]
            )
            self.gsc_service = build('searchconsole', 'v1', credentials=credentials)
            print("✓ GSC API connected")
            self.ga_service = build('analyticsdata', 'v1beta', credentials=credentials)
            print("✓ GA4 API connected")
        except Exception as e:
            print(f"❌ API setup failed: {e}")
            raise

    # ---------- NEW: SITEMAP HELPERS ----------
    def _fetch_bytes(self, url: str, timeout: int = 30, headers: Optional[Dict[str, str]] = None) -> bytes:
        """Fetch bytes and robustly handle (mis)gzip content."""
        hdrs = {"User-Agent": "URLComparison/1.0"}
        if headers:
            hdrs.update(headers)
        resp = requests.get(url, headers=hdrs, timeout=timeout)
        resp.raise_for_status()
        content = resp.content

        # sniff by magic bytes or .gz extension
        is_gz_ext = url.lower().endswith(".gz")
        looks_gzipped = len(content) >= 2 and content[0] == 0x1F and content[1] == 0x8B
        if is_gz_ext or looks_gzipped:
            try:
                return gzip.decompress(content)
            except OSError:
                return content

        # some servers set gzip header on plain XML
        if resp.headers.get("Content-Encoding", "").lower() == "gzip":
            try:
                return gzip.decompress(content)
            except OSError:
                return content

        return content

    def _parse_xml(self, xml_bytes: bytes) -> ET.Element:
        return ET.fromstring(xml_bytes)

    def _discover_sitemap(self, site_url: str, timeout: int = 15) -> str:
        """Try robots.txt first, then /sitemap.xml."""
        try:
            robots = urljoin(site_url, "/robots.txt")
            b = self._fetch_bytes(robots, timeout=timeout)
            text = b.decode("utf-8", errors="ignore")
            for line in text.splitlines():
                if line.strip().lower().startswith("sitemap:"):
                    return line.split(":", 1)[1].strip()
        except Exception:
            pass
        return urljoin(site_url, "/sitemap.xml")

    def load_urls_from_sitemap(
        self,
        site_url: str,
        sitemap_url: Optional[str] = None,
        include_filter: str = "/blog/",
        timeout: int = 30,
        max_sitemaps: int = 2000,
        max_urls: int = 500000
    ) -> List[str]:
        """Load URLs from a sitemap (supports sitemapindex, nested sitemaps, and gz)."""
        if not sitemap_url:
            sitemap_url = self._discover_sitemap(site_url)
            print(f"🔎 Auto-discovered sitemap: {sitemap_url}")

        parsed_site = urlparse(site_url)
        site_host = parsed_site.hostname
        seen_sitemaps: Set[str] = set()
        collected: Set[str] = set()

        def same_domain(u: str) -> bool:
            h = urlparse(u).hostname
            return (h == site_host) or (h and site_host and h.endswith("." + site_host))

        def normalize(u: str) -> str:
            pu = urlparse(u)
            if not pu.scheme:
                u = urljoin(site_url, u)
                pu = urlparse(u)
            out = f"{pu.scheme}://{pu.netloc}{pu.path}"
            if pu.query:
                out += f"?{pu.query}"
            return out

        def walk(sm_url: str):
            nonlocal max_sitemaps, max_urls
            if sm_url in seen_sitemaps or len(seen_sitemaps) >= max_sitemaps:
                return
            seen_sitemaps.add(sm_url)

            try:
                print(f"🌐 Loading URLs from sitemap: {sm_url}")
                xml_bytes = self._fetch_bytes(sm_url, timeout=timeout)
                root = self._parse_xml(xml_bytes)
            except Exception as e:
                print(f"⚠️  Failed to fetch/parse sitemap {sm_url}: {e}")
                return

            tag = root.tag.lower()
            if "}" in tag:
                tag = tag.split("}", 1)[1]

            if tag == "sitemapindex":
                for loc_el in root.findall(".//{*}sitemap/{*}loc"):
                    loc = (loc_el.text or "").strip()
                    if loc:
                        walk(loc)
            else:
                loc_els = root.findall(".//{*}url/{*}loc")
                if not loc_els:
                    loc_els = root.findall(".//{*}loc")
                for loc_el in loc_els:
                    loc = (loc_el.text or "").strip()
                    if not loc:
                        continue
                    u = normalize(loc)
                    if not same_domain(u):
                        continue
                    if include_filter and include_filter not in u:
                        continue
                    collected.add(u)
                    if len(collected) >= max_urls:
                        print("⚠️  Reached max_urls cap; stopping collection.")
                        return

        walk(sitemap_url)
        urls = sorted(collected)
        print(f"✓ Loaded {len(urls)} URLs from sitemap (filtered by '{include_filter}')")
        return urls
    # ---------- END SITEMAP HELPERS ----------

    def load_urls(self, csv_file: str) -> list:
        """Load URLs from CSV file (single column, no header)"""
        df = pd.read_csv(csv_file, header=None, names=['url'])
        urls = df['url'].dropna().tolist()
        print(f"✓ Loaded {len(urls)} URLs")
        return urls
    
    def get_gsc_data_for_period(self, site_url: str, start_date: str, end_date: str, urls: list) -> dict:
        """Get GSC data for specific date range"""
        print(f"📊 Fetching GSC data ({start_date} to {end_date})...")
        try:
            property_urls = [
                site_url,
                f"sc-domain:{site_url.replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')}"
            ]
            gsc_data = {}
            for property_url in property_urls:
                try:
                    all_rows = []
                    start_row = 0
                    while True:
                        request = {
                            'startDate': start_date,
                            'endDate': end_date,
                            'dimensions': ['page'],
                            'rowLimit': 25000,
                            'startRow': start_row
                        }
                        response = self.gsc_service.searchanalytics().query(
                            siteUrl=property_url, 
                            body=request
                        ).execute()
                        rows = response.get('rows', [])
                        if not rows:
                            break
                        all_rows.extend(rows)
                        if len(rows) < 25000:
                            break
                        start_row += 25000
                        if start_row >= 100000:
                            break
                    print(f"✓ Using GSC property: {property_url}")
                    print(f"✓ Retrieved {len(all_rows)} total URLs from GSC")
                    for row in all_rows:
                        page_url = row['keys'][0]
                        if not page_url.startswith('http'):
                            page_url = site_url.rstrip('/') + page_url
                        gsc_data[page_url] = {
                            'clicks': row['clicks'],
                            'impressions': row['impressions'],
                            'ctr': round(row['ctr'] * 100, 2),
                            'position': round(row['position'], 1)
                        }
                    break
                except Exception as e:
                    print(f"⚠️  Failed with property {property_url}: {str(e)[:100]}...")
                    continue
            else:
                print("❌ No valid GSC property found")
                return {}
            return gsc_data
        except Exception as e:
            print(f"❌ GSC data retrieval failed: {e}")
            return {}
    
    def get_ga4_data_for_period(self, property_id: str, start_date: str, end_date: str, urls: list) -> dict:
        """Get GA4 sessions data for specific date range, broken down by traffic source"""
        print(f"📈 Fetching GA4 data ({start_date} to {end_date})...")
        try:
            total_request = {
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'dimensions': [{'name': 'pagePath'}],
                'metrics': [{'name': 'sessions'}],
                'limit': 100000
            }
            total_response = self.ga_service.properties().runReport(
                property=f'properties/{property_id}',
                body=total_request
            ).execute()
            source_request = {
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'dimensions': [
                    {'name': 'pagePath'},
                    {'name': 'sessionDefaultChannelGroup'}
                ],
                'metrics': [{'name': 'sessions'}],
                'limit': 100000
            }
            source_response = self.ga_service.properties().runReport(
                property=f'properties/{property_id}',
                body=source_request
            ).execute()
            ga_data = {}
            for row in total_response.get('rows', []):
                page_path = row['dimensionValues'][0]['value']
                sessions = int(row['metricValues'][0]['value'])
                ga_data[page_path] = {
                    'total_sessions': sessions,
                    'organic_sessions': 0,
                    'paid_sessions': 0,
                    'direct_sessions': 0
                }
            for row in source_response.get('rows', []):
                page_path = row['dimensionValues'][0]['value']
                channel = row['dimensionValues'][1]['value']
                sessions = int(row['metricValues'][0]['value'])
                if page_path not in ga_data:
                    ga_data[page_path] = {
                        'total_sessions': 0,
                        'organic_sessions': 0,
                        'paid_sessions': 0,
                        'direct_sessions': 0
                    }
                cl = channel.lower()
                if cl in ['organic search', 'organic_search']:
                    ga_data[page_path]['organic_sessions'] = sessions
                elif cl in ['paid search', 'paid_search', 'paid social', 'display', 'video']:
                    ga_data[page_path]['paid_sessions'] += sessions
                elif cl in ['direct', '(direct)']:
                    ga_data[page_path]['direct_sessions'] = sessions
            print(f"✓ Retrieved GA4 data for {len(ga_data)} URLs")
            return ga_data
        except Exception as e:
            print(f"❌ GA4 data retrieval failed: {e}")
            return {}

    def calculate_percentage_change(self, old_value: float, new_value: float) -> float:
        """Calculate percentage change between two values"""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        return round(((new_value - old_value) / old_value) * 100, 2)
    
    def compare_periods(self, urls: list, site_url: str, ga_property_id: str,
                        period1_start: str, period1_end: str,
                        period2_start: str, period2_end: str,
                        output_file: str = 'Reports/gsc_comparison.csv',
                        ga_output_file: str = 'Reports/ga4_comparison.csv'):
        """Main comparison function"""
        print("🔍 Starting GSC and GA4 period comparison...")

        # Get GSC data for both periods
        gsc_period1_data = self.get_gsc_data_for_period(site_url, period1_start, period1_end, urls)
        gsc_period2_data = self.get_gsc_data_for_period(site_url, period2_start, period2_end, urls)
        
        # Get GA4 data for both periods
        ga_period1_data = self.get_ga4_data_for_period(ga_property_id, period1_start, period1_end, urls)
        ga_period2_data = self.get_ga4_data_for_period(ga_property_id, period2_start, period2_end, urls)
        
        # Process GSC results
        gsc_results = []
        print("📊 Processing GSC comparison data...")
        for url in urls:
            gsc_p1 = gsc_period1_data.get(url, {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0})
            gsc_p2 = gsc_period2_data.get(url, {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0})
            clicks_change = self.calculate_percentage_change(gsc_p1['clicks'], gsc_p2['clicks'])
            impressions_change = self.calculate_percentage_change(gsc_p1['impressions'], gsc_p2['impressions'])
            ctr_change = self.calculate_percentage_change(gsc_p1['ctr'], gsc_p2['ctr'])
            position_change = self.calculate_percentage_change(gsc_p1['position'], gsc_p2['position']) * -1
            gsc_results.append({
                'url': url,
                f'clicks_period1_{period1_start}_to_{period1_end}': gsc_p1['clicks'],
                f'impressions_period1_{period1_start}_to_{period1_end}': gsc_p1['impressions'],
                f'ctr_period1_{period1_start}_to_{period1_end}': gsc_p1['ctr'],
                f'position_period1_{period1_start}_to_{period1_end}': gsc_p1['position'],
                f'clicks_period2_{period2_start}_to_{period2_end}': gsc_p2['clicks'],
                f'impressions_period2_{period2_start}_to_{period2_end}': gsc_p2['impressions'],
                f'ctr_period2_{period2_start}_to_{period2_end}': gsc_p2['ctr'],
                f'position_period2_{period2_start}_to_{period2_end}': gsc_p2['position'],
                'clicks_change_percent': clicks_change,
                'impressions_change_percent': impressions_change,
                'ctr_change_percent': ctr_change,
                'position_change_percent': position_change
            })
        
        # Process GA4 results
        ga_results = []
        print("📊 Processing GA4 comparison data...")
        for url in urls:
            # Convert URL to page path for GA4 matching
            if url.startswith('http'):
                page_path = '/' + '/'.join(url.split('/')[3:]) if len(url.split('/')) > 3 else '/'
            else:
                page_path = url if url.startswith('/') else '/' + url
            page_path = page_path.rstrip('/') or '/'
            ga_p1 = ga_period1_data.get(page_path, {'total_sessions': 0, 'organic_sessions': 0, 'paid_sessions': 0, 'direct_sessions': 0})
            ga_p2 = ga_period2_data.get(page_path, {'total_sessions': 0, 'organic_sessions': 0, 'paid_sessions': 0, 'direct_sessions': 0})
            total_sessions_change = self.calculate_percentage_change(ga_p1['total_sessions'], ga_p2['total_sessions'])
            organic_sessions_change = self.calculate_percentage_change(ga_p1['organic_sessions'], ga_p2['organic_sessions'])
            paid_sessions_change = self.calculate_percentage_change(ga_p1['paid_sessions'], ga_p2['paid_sessions'])
            direct_sessions_change = self.calculate_percentage_change(ga_p1['direct_sessions'], ga_p2['direct_sessions'])
            ga_results.append({
                'url': url,
                f'total_sessions_period1_{period1_start}_to_{period1_end}': ga_p1['total_sessions'],
                f'organic_sessions_period1_{period1_start}_to_{period1_end}': ga_p1['organic_sessions'],
                f'paid_sessions_period1_{period1_start}_to_{period1_end}': ga_p1['paid_sessions'],
                f'direct_sessions_period1_{period1_start}_to_{period1_end}': ga_p1['direct_sessions'],
                f'total_sessions_period2_{period2_start}_to_{period2_end}': ga_p2['total_sessions'],
                f'organic_sessions_period2_{period2_start}_to_{period2_end}': ga_p2['organic_sessions'],
                f'paid_sessions_period2_{period2_start}_to_{period2_end}': ga_p2['paid_sessions'],
                f'direct_sessions_period2_{period2_start}_to_{period2_end}': ga_p2['direct_sessions'],
                'total_sessions_change_percent': total_sessions_change,
                'organic_sessions_change_percent': organic_sessions_change,
                'paid_sessions_change_percent': paid_sessions_change,
                'direct_sessions_change_percent': direct_sessions_change
            })
        
        # Create DataFrames and save
        gsc_df = pd.DataFrame(gsc_results).sort_values('clicks_change_percent', ascending=False)
        ga_df = pd.DataFrame(ga_results).sort_values('total_sessions_change_percent', ascending=False)
        
        # Create output directory
        if os.path.dirname(output_file):
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        if os.path.dirname(ga_output_file):
            os.makedirs(os.path.dirname(ga_output_file), exist_ok=True)
        
        # Save results
        gsc_df.to_csv(output_file, index=False)
        ga_df.to_csv(ga_output_file, index=False)
        
        print(f"✅ GSC comparison saved to {output_file}")
        print(f"✅ GA4 comparison saved to {ga_output_file}")
        
        # Summary
        total_urls = len(gsc_df)
        urls_with_gsc_clicks_p1 = len(gsc_df[gsc_df[f'clicks_period1_{period1_start}_to_{period1_end}'] > 0])
        urls_with_gsc_clicks_p2 = len(gsc_df[gsc_df[f'clicks_period2_{period2_start}_to_{period2_end}'] > 0])
        urls_with_ga_sessions_p1 = len(ga_df[ga_df[f'total_sessions_period1_{period1_start}_to_{period1_end}'] > 0])
        urls_with_ga_sessions_p2 = len(ga_df[ga_df[f'total_sessions_period2_{period2_start}_to_{period2_end}'] > 0])
        
        print(f"\n📊 Summary:")
        print(f"   Total URLs analyzed: {total_urls:,}")
        print(f"   URLs with GSC clicks in Period 1: {urls_with_gsc_clicks_p1:,}")
        print(f"   URLs with GSC clicks in Period 2: {urls_with_gsc_clicks_p2:,}")
        print(f"   URLs with GA4 sessions in Period 1: {urls_with_ga_sessions_p1:,}")
        print(f"   URLs with GA4 sessions in Period 2: {urls_with_ga_sessions_p2:,}")
        
        print(f"\n🚀 Top 5 Click Gainers (GSC):")
        for _, row in gsc_df.head(5)[['url', 'clicks_change_percent']].iterrows():
            print(f"   {row['clicks_change_percent']:+.1f}% - {row['url']}")
        
        print(f"\n🚀 Top 5 Session Gainers (GA4):")
        for _, row in ga_df.head(5)[['url', 'total_sessions_change_percent']].iterrows():
            print(f"   {row['total_sessions_change_percent']:+.1f}% - {row['url']}")

        return gsc_df, ga_df

def main():
    parser = argparse.ArgumentParser(description='GSC and GA4 Period Comparison Tool')
    # Either provide a CSV OR use sitemap mode
    parser.add_argument('--urls-file', help='CSV file with URLs (single column, no header)')
    parser.add_argument('--sitemap', help='Sitemap URL (optional; if omitted, auto-discover via robots.txt)')
    parser.add_argument('--include-filter', default='/blog/', help='Substring filter for sitemap URLs (default: /blog/)')
    parser.add_argument('--site-url', required=True, help='GSC site URL (e.g., https://www.example.com/)')
    parser.add_argument('--ga-property-id', required=True, help='GA4 Property ID (numbers only)')
    parser.add_argument('--credentials', required=True, help='Path to service account credentials JSON')
    parser.add_argument('--period1-start', required=True, help='Period 1 start date (YYYY-MM-DD)')
    parser.add_argument('--period1-end', required=True, help='Period 1 end date (YYYY-MM-DD)')
    parser.add_argument('--period2-start', required=True, help='Period 2 start date (YYYY-MM-DD)')
    parser.add_argument('--period2-end', required=True, help='Period 2 end date (YYYY-MM-DD)')
    parser.add_argument('--gsc-output', default='Reports/gsc_comparison.csv', help='GSC output file path')
    parser.add_argument('--ga-output', default='Reports/ga4_comparison.csv', help='GA4 output file path')
    
    args = parser.parse_args()

    # Load URLs: sitemap takes precedence; if none provided and no CSV, auto-discover
    tool = GSCComparisonTool(credentials_path=args.credentials)
    if args.sitemap or not args.urls_file:
        urls = tool.load_urls_from_sitemap(site_url=args.site_url, sitemap_url=args.sitemap, include_filter=args.include_filter)
        if not urls:
            raise ValueError("No URLs found from sitemap mode.")
    else:
        urls = tool.load_urls(args.urls_file)

    # Run comparison
    tool.compare_periods(
        urls=urls,
        site_url=args.site_url,
        ga_property_id=args.ga_property_id,
        period1_start=args.period1_start,
        period1_end=args.period1_end,
        period2_start=args.period2_start,
        period2_end=args.period2_end,
        output_file=args.gsc_output,
        ga_output_file=args.ga_output
    )

if __name__ == "__main__":
    main()
