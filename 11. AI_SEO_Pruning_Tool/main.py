import pandas as pd
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional, Set
import argparse
import io
import gzip
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

class ContentPruningTool:
    def __init__(self, gsc_credentials_path: str = None, ga_credentials_path: str = None):
        """
        Initialize the content pruning tool

        Args:
            gsc_credentials_path: Path to GSC API credentials JSON
            ga_credentials_path: Path to GA API credentials JSON
        """
        self.gsc_service = None
        self.ga_service = None

        if gsc_credentials_path and os.path.exists(gsc_credentials_path):
            self.setup_gsc(gsc_credentials_path)

        if ga_credentials_path and os.path.exists(ga_credentials_path):
            self.setup_ga(ga_credentials_path)

    def setup_gsc(self, credentials_path: str):
        """Setup Google Search Console API"""
        try:
            from google.oauth2.service_account import Credentials as ServiceCredentials
            credentials = ServiceCredentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
            self.gsc_service = build('searchconsole', 'v1', credentials=credentials)
            print("✓ GSC API connected")
        except Exception as e:
            print(f"GSC setup failed: {e}")

    def setup_ga(self, credentials_path: str):
        """Setup Google Analytics API - GA4 Data API"""
        try:
            from google.oauth2.service_account import Credentials as ServiceCredentials
            credentials = ServiceCredentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/analytics.readonly']
            )
            # Use GA4 Data API (not the old reporting API)
            self.ga_service = build('analyticsdata', 'v1beta', credentials=credentials)
            print("✓ GA4 Data API connected")
        except Exception as e:
            print(f"❌ GA setup failed: {e}")
            self.ga_service = None

    # ---------- NEW: SITEMAP HELPERS ----------
    def _fetch_bytes(self, url: str, timeout: int = 30, headers: Optional[Dict[str, str]] = None) -> bytes:
        """Fetch bytes and robustly handle (mis)gzip content."""
        hdrs = {"User-Agent": "ContentPruningTool/1.0"}
        if headers:
            hdrs.update(headers)
        resp = requests.get(url, headers=hdrs, timeout=timeout)
        resp.raise_for_status()
        content = resp.content

        # Detect gzip by magic bytes (0x1f 0x8b). Only then try to decompress.
        is_gz_ext = url.lower().endswith(".gz")
        looks_gzipped = len(content) >= 2 and content[0] == 0x1F and content[1] == 0x8B

        if is_gz_ext or looks_gzipped:
            try:
                return gzip.decompress(content)
            except OSError:
                # Some servers mislabel; fall back to raw
                return content

        # Some servers incorrectly set Content-Encoding: gzip on plain XML
        enc = resp.headers.get("Content-Encoding", "").lower()
        if enc == "gzip":
            try:
                return gzip.decompress(content)
            except OSError:
                return content

        return content

    def _parse_xml(self, xml_bytes: bytes) -> ET.Element:
        return ET.fromstring(xml_bytes)

    def _discover_sitemap(self, site_url: str, timeout: int = 15) -> Optional[str]:
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
        # Fallback
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
        """
        Load URLs from a sitemap (supports sitemapindex, nested sitemaps, and gz).
        Auto-discovers sitemap if not provided.
        """
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
            # keep path + query, strip fragments
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
                # urlset or generic <loc> collector
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

    def load_crawl_data(self, crawl_file_path: str) -> pd.DataFrame:
        """Load and filter crawl data for indexable 200-status URLs only"""
        if crawl_file_path.endswith('.csv'):
            df = pd.read_csv(crawl_file_path, low_memory=False)
        elif crawl_file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(crawl_file_path)
        else:
            raise ValueError("Crawl file must be CSV or Excel format")

        # Standardize column names
        df.columns = df.columns.str.lower().str.replace(' ', '_')

        # Find URL column
        url_columns = ['url', 'address', 'page_url', 'link', 'source']
        url_col = None
        for col in url_columns:
            if col in df.columns:
                url_col = col
                break

        if not url_col:
            print("Available columns:", list(df.columns))
            raise ValueError(f"No URL column found. Expected one of: {url_columns}")

        df = df.rename(columns={url_col: 'url'})

        # Clean URLs
        df['url_clean'] = df['url'].str.split('#').str[0].str.split('?').str[0]

        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=['url_clean'])
        print(f"✓ Loaded {len(df)} unique URLs (removed {initial_count - len(df)} duplicates)")

        # Filter for 200 status codes only
        status_col = None
        for col in ['status_code', 'response_code', 'http_status']:
            if col in df.columns:
                status_col = col
                break

        if status_col:
            df[status_col] = pd.to_numeric(df[status_col], errors='coerce').fillna(200)
            before_filter = len(df)
            df = df[df[status_col] == 200]
            print(f"✓ Filtered to {len(df)} URLs with 200 status (removed {before_filter - len(df)})")

        # Filter for indexable content only
        indexable_col = None
        for col in ['indexability', 'indexable', 'robots_txt']:
            if col in df.columns:
                indexable_col = col
                break

        if indexable_col:
            before_filter = len(df)
            indexable_values = ['indexable', 'yes', 'true', '1', 'index']
            df = df[df[indexable_col].astype(str).str.lower().isin(indexable_values)]
            print(f"✓ Filtered to {len(df)} indexable URLs (removed {before_filter - len(df)})")

        return df

    def get_gsc_data(self, site_url: str, start_date: str, end_date: str, urls: List[str]) -> Dict:
        """Get GSC data for specific URLs"""
        if not self.gsc_service:
            print("GSC service not available")
            return {}

        try:
            # Try different property formats
            property_urls = [
                site_url,
                f"sc-domain:{site_url.replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')}"
            ]

            for property_url in property_urls:
                try:
                    request = {
                        'startDate': start_date,
                        'endDate': end_date,
                        'dimensions': ['page'],
                        'rowLimit': 25000
                    }

                    response = self.gsc_service.searchanalytics().query(
                        siteUrl=property_url,
                        body=request
                    ).execute()

                    print(f"✓ Using GSC property: {property_url}")
                    break

                except Exception:
                    continue
            else:
                print("No valid GSC property found")
                return {}

            all_data = {}
            for row in response.get('rows', []):
                url = row['keys'][0]
                if not url.startswith('http'):
                    url = site_url.rstrip('/') + url

                all_data[url] = {
                    'clicks': row['clicks'],
                    'impressions': row['impressions'],
                    'ctr': row['ctr'],
                    'position': row['position']
                }

            print(f"✓ Retrieved GSC data for {len(all_data)} URLs")
            return all_data

        except Exception as e:
            print(f"GSC data retrieval failed: {e}")
            return {}

    def get_ga_data(self, property_id: str, start_date: str, end_date: str, urls: List[str]) -> Dict:
        """Get GA4 data for specific URLs"""
        if not self.ga_service:
            print("GA service not available")
            return {}

        try:
            print(f"📈 Fetching GA4 data for property {property_id}...")

            # GA4 Data API request
            request_body = {
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'dimensions': [
                    {'name': 'pagePath'}
                ],
                'metrics': [
                    {'name': 'screenPageViews'},
                    {'name': 'sessions'}
                ],
                'limit': 100000
            }

            response = self.ga_service.properties().runReport(
                property=f'properties/{property_id}',
                body=request_body
            ).execute()

            ga_data = {}
            for row in response.get('rows', []):
                page_path = row['dimensionValues'][0]['value']
                pageviews = int(row['metricValues'][0]['value'])

                ga_data[page_path] = {
                    'pageviews': pageviews,
                    'sessions': int(row['metricValues'][1]['value'])
                }

            print(f"✓ Retrieved GA4 data for {len(ga_data)} URLs")
            return ga_data

        except Exception as e:
            print(f"❌ GA data retrieval failed: {e}")
            return {}

    def calculate_pruning_score(self, row: pd.Series, gsc_data: Dict, ga_data: Dict) -> float:
        """Calculate pruning score (0-100, higher = more likely to prune)"""
        score = 0
        url = row['url']

        # GSC metrics (40% weight)
        gsc = gsc_data.get(url, {})
        if gsc:
            # Low clicks (20%)
            clicks = gsc.get('clicks', 0)
            if clicks == 0:
                score += 20
            elif clicks < 10:
                score += 15
            elif clicks < 50:
                score += 10
            elif clicks < 100:
                score += 5

            # Poor position (10%)
            position = gsc.get('position', 100)
            if position > 50:
                score += 10
            elif position > 20:
                score += 5

            # Low impressions (10%)
            impressions = gsc.get('impressions', 0)
            if impressions < 100:
                score += 10
            elif impressions < 500:
                score += 5
        else:
            score += 25  # No GSC data

        # GA metrics (30% weight)
        ga_path = url.replace(f"https://{url.split('/')[2]}", '') if url.startswith('http') else url
        if ga_path == '':
            ga_path = '/'
        ga = ga_data.get(ga_path, {})
        if ga:
            # Low pageviews (15%)
            pageviews = ga.get('pageviews', 0)
            if pageviews == 0:
                score += 15
            elif pageviews < 10:
                score += 12
            elif pageviews < 50:
                score += 8
            elif pageviews < 100:
                score += 4
        else:
            score += 15  # No GA data

        # Content quality indicators (30% weight)
        # Only penalize if data is present; sitemap runs won't be unfairly penalized.
        word_count = row.get('word_count', None)
        if isinstance(word_count, (int, float)) and word_count > 0:
            if word_count < 300:
                score += 15
            elif word_count < 500:
                score += 10
            elif word_count < 800:
                score += 5

        meta_desc = row.get('meta_description') if 'meta_description' in row else None
        if isinstance(meta_desc, str) and meta_desc.strip() == "":
            score += 8

        return min(score, 100)  # Cap at 100

    def analyze_content(
        self,
        crawl_file: Optional[str],
        site_url: str = None,
        ga_property_id: str = None,
        days_back: int = 90,
        output_file: str = 'Reports/content_pruning_analysis.csv',
        sitemap: Optional[str] = None,
        include_filter: str = "/blog/"
    ) -> pd.DataFrame:
        """Main analysis function"""
        print("🔍 Starting content pruning analysis...")

        # Source URLs either from crawl file OR sitemap (sitemap takes precedence)
        if sitemap or (not crawl_file):
            if not site_url:
                raise ValueError("--site-url is required when using sitemap mode.")
            urls = self.load_urls_from_sitemap(site_url=site_url, sitemap_url=sitemap, include_filter=include_filter)
            if not urls:
                raise ValueError("No URLs found from sitemap.")
            df = pd.DataFrame({"url": urls})
            # Create neutral placeholders so sitemap runs don't get penalized
            df["word_count"] = None
            df["meta_description"] = None
            print(f"📂 Using {len(df)} URLs from sitemap (filter='{include_filter}')")
        else:
            df = self.load_crawl_data(crawl_file)

        # Date range for API calls
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # Get API data
        gsc_data = {}
        ga_data = {}

        if site_url and self.gsc_service:
            print(f"📊 Fetching GSC data ({start_date} to {end_date})...")
            gsc_data = self.get_gsc_data(site_url, start_date, end_date, df['url'].tolist())

        if ga_property_id and self.ga_service:
            print(f"📈 Fetching GA data ({start_date} to {end_date})...")
            ga_data = self.get_ga_data(ga_property_id, start_date, end_date, df['url'].tolist())

        # Calculate pruning scores
        print("🎯 Calculating pruning scores...")
        df['pruning_score'] = df.apply(lambda row: self.calculate_pruning_score(row, gsc_data, ga_data), axis=1)

        # Add API data to dataframe efficiently
        df['gsc_clicks'] = df['url'].map(lambda x: gsc_data.get(x, {}).get('clicks', 0))
        df['gsc_impressions'] = df['url'].map(lambda x: gsc_data.get(x, {}).get('impressions', 0))
        df['gsc_ctr'] = df['url'].map(lambda x: gsc_data.get(x, {}).get('ctr', 0))
        df['gsc_position'] = df['url'].map(lambda x: gsc_data.get(x, {}).get('position', 0))

        # Fix GA data mapping
        def get_ga_pageviews(url):
            path = url.replace(f"https://{url.split('/')[2]}", '') if url.startswith('http') else url
            if path == '':
                path = '/'
            return ga_data.get(path, {}).get('pageviews', 0)

        df['ga_pageviews'] = df['url'].map(get_ga_pageviews)
        df['ga_sessions'] = df['url'].map(
            lambda x: ga_data.get(
                x.replace(f"https://{x.split('/')[2]}", '') if x.startswith('http') else ('/' if x.replace(f"https://{x.split('/')[2]}", '') == '' else x.replace(f"https://{x.split('/')[2]}", '')),
                {}
            ).get('sessions', 0)
        )

        # Sort by pruning score (highest first)
        df = df.sort_values('pruning_score', ascending=False)

        # Add recommendations
        def get_recommendation(score):
            if score >= 80:
                return "PRUNE - Strong candidate for removal"
            elif score >= 60:
                return "REVIEW - Consider pruning or major improvement"
            elif score >= 40:
                return "IMPROVE - Optimize content and SEO"
            elif score >= 20:
                return "MONITOR - Minor improvements needed"
            else:
                return "KEEP - Good performing content"

        df['recommendation'] = df['pruning_score'].apply(get_recommendation)

        # Create summary stats
        summary_data = {
            'Total URLs': len(df),
            'Prune Candidates (80+)': len(df[df['pruning_score'] >= 80]),
            'Review Candidates (60-79)': len(df[(df['pruning_score'] >= 60) & (df['pruning_score'] < 80)]),
            'Improve Candidates (40-59)': len(df[(df['pruning_score'] >= 40) & (df['pruning_score'] < 60)]),
            'Monitor (20-39)': len(df[(df['pruning_score'] >= 20) & (df['pruning_score'] < 40)]),
            'Keep (<20)': len(df[df['pruning_score'] < 20])
        }

        # Create output directory
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Save results as CSV
        print(f"💾 Saving results to {output_file}...")
        output_cols = ['url', 'pruning_score', 'recommendation', 'gsc_clicks', 'gsc_impressions',
                       'gsc_ctr', 'gsc_position', 'ga_pageviews', 'ga_sessions']

        # Add crawl data columns if available
        for col in ['title', 'meta_description', 'word_count', 'status_code']:
            if col in df.columns:
                output_cols.append(col)

        df[output_cols].to_csv(output_file, index=False)

        # Save summary
        summary_file = output_file.replace('.csv', '_summary.csv')
        summary_df = pd.DataFrame(list(summary_data.items()), columns=['Metric', 'Count'])
        summary_df.to_csv(summary_file, index=False)

        print(f"✅ Analysis complete! Results saved to {output_file}")
        print(f"📊 Summary:")
        for metric, count in summary_data.items():
            print(f"   {metric}: {count:,}")

        return df

def main():
    parser = argparse.ArgumentParser(description='Content Pruning Tool')
    # Now optional; sitemap can be used instead
    parser.add_argument('--crawl-file', help='Path to crawl data CSV/Excel file')
    parser.add_argument('--site-url', help='GSC site URL (e.g., https://www.example.com/)', required=False)
    parser.add_argument('--ga-property-id', help='GA4 Property ID (numbers only, e.g., 386754123)')
    parser.add_argument('--gsc-credentials', help='Path to GSC API credentials JSON')
    parser.add_argument('--ga-credentials', help='Path to GA API credentials JSON')
    parser.add_argument('--days-back', type=int, default=90, help='Days of historical data to analyze')
    parser.add_argument('--output', default='Reports/content_pruning_analysis.csv', help='Output file path')

    # NEW: sitemap-first flow
    parser.add_argument('--sitemap', help='Sitemap URL (if omitted, auto-discover via robots.txt then /sitemap.xml)')
    parser.add_argument('--include-filter', default='/blog/', help='Substring filter for sitemap URLs (default: /blog/)')

    args = parser.parse_args()

    # Require site-url when using sitemap mode (or for GSC)
    if (args.sitemap or not args.crawl_file) and not args.site_url:
        parser.error("--site-url is required when using --sitemap or when --crawl-file is not provided.")

    # Initialize tool
    tool = ContentPruningTool(
        gsc_credentials_path=args.gsc_credentials,
        ga_credentials_path=args.ga_credentials
    )

    # Run analysis
    results = tool.analyze_content(
        crawl_file=args.crawl_file,
        site_url=args.site_url,
        ga_property_id=args.ga_property_id,
        days_back=args.days_back,
        output_file=args.output,
        sitemap=args.sitemap,
        include_filter=args.include_filter
    )

    # Show top pruning candidates
    print("\n🎯 Top 10 Pruning Candidates:")
    display_cols = ['url', 'pruning_score', 'recommendation', 'gsc_clicks', 'ga_pageviews']
    print(results[display_cols].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
