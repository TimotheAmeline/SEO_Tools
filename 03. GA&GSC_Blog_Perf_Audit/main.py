import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Set
import argparse

# NEW: imports for sitemap handling
import requests
import gzip
import io
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

class BlogPerformanceAnalyzer:
    def __init__(self, credentials_path: str):
        """
        Initialize the blog performance analyzer

        Args:
            credentials_path: Path to service account credentials JSON
        """
        self.gsc_service = None
        self.ga_service = None
        self.credentials_path = credentials_path

        if os.path.exists(credentials_path):
            self.setup_apis()
        else:
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    def setup_apis(self):
        """Setup Google Search Console and GA4 APIs"""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=[
                    'https://www.googleapis.com/auth/webmasters.readonly',
                    'https://www.googleapis.com/auth/analytics.readonly'
                ]
            )

            self.gsc_service = build('searchconsole', 'v1', credentials=credentials)
            self.ga_service = build('analyticsdata', 'v1beta', credentials=credentials)
            print("✓ GSC and GA4 APIs connected")

        except Exception as e:
            print(f"API setup failed: {e}")
            raise

    # --- NEW: sitemap loader -------------------------------------------------
    def load_urls_from_sitemap(
        self,
        site_url: str,
        sitemap_url: str,
        include_filter: str = "/blog/",
        timeout: int = 30,
        max_sitemaps: int = 2000,
        max_urls: int = 500000
    ) -> List[str]:
        """
        Load URLs from a sitemap (supports sitemapindex, nested sitemaps, and gz).

        Args:
            site_url: Base site URL (used to restrict domain)
            sitemap_url: URL of the sitemap or sitemap index
            include_filter: Substring to filter URLs (default '/blog/')
            timeout: HTTP timeout
            max_sitemaps: Safety cap for number of nested sitemaps
            max_urls: Safety cap for total URLs collected

        Returns:
            List of filtered absolute URLs
        """
        print(f"🌐 Loading URLs from sitemap: {sitemap_url}")
        parsed_site = urlparse(site_url)
        site_host = parsed_site.hostname

        headers = {
            "User-Agent": "BlogPerformanceAnalyzer/1.0"
        }

        seen_sitemaps: Set[str] = set()
        collected_urls: Set[str] = set()

        def _fetch(url: str) -> bytes:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            content = resp.content
            # Auto-handle gzip for .gz files or content-encoding
            if url.endswith(".gz") or resp.headers.get("Content-Encoding", "").lower() == "gzip":
                try:
                    content = gzip.decompress(content)
                except OSError:
                    # Not actually gzipped, just return raw
                    pass
                except Exception:
                    # Some servers send gzipped content without header; fallback to BytesIO
                    content = gzip.GzipFile(fileobj=io.BytesIO(resp.content)).read()
            return content

        def _parse_xml(xml_bytes: bytes) -> ET.Element:
            return ET.fromstring(xml_bytes)

        def _is_same_domain(u: str) -> bool:
            h = urlparse(u).hostname
            return (h == site_host) or (h and site_host and h.endswith("." + site_host))

        def _normalize(u: str) -> str:
            # Ensure absolute, strip fragments, keep trailing slash consistency
            pu = urlparse(u)
            if not pu.scheme:
                u = urljoin(site_url, u)
            pu = urlparse(u)
            u = f"{pu.scheme}://{pu.netloc}{pu.path}"
            if pu.query:
                u += f"?{pu.query}"
            return u

        def _walk_sitemap(url: str):
            nonlocal max_sitemaps, max_urls
            if url in seen_sitemaps or len(seen_sitemaps) >= max_sitemaps:
                return
            seen_sitemaps.add(url)

            try:
                xml_bytes = _fetch(url)
                root = _parse_xml(xml_bytes)
            except Exception as e:
                print(f"⚠️  Failed to fetch/parse sitemap {url}: {e}")
                return

            tag = root.tag.lower()
            # strip namespace
            if "}" in tag:
                tag = tag.split("}", 1)[1]

            if tag == "sitemapindex":
                for sm in root.findall(".//{*}sitemap/{*}loc"):
                    sm_url = sm.text.strip()
                    if sm_url:
                        _walk_sitemap(sm_url)
            elif tag == "urlset":
                for loc_el in root.findall(".//{*}url/{*}loc"):
                    loc = loc_el.text.strip()
                    if not loc:
                        continue
                    loc = _normalize(loc)
                    if not _is_same_domain(loc):
                        continue
                    if include_filter and include_filter not in loc:
                        continue
                    collected_urls.add(loc)
                    if len(collected_urls) >= max_urls:
                        print("⚠️  Reached max_urls cap; stopping collection.")
                        return
            else:
                # Some providers return URL list without standard root tag; try generic <loc>
                for loc_el in root.findall(".//{*}loc"):
                    loc = (loc_el.text or "").strip()
                    if not loc:
                        continue
                    loc = _normalize(loc)
                    if not _is_same_domain(loc):
                        continue
                    if include_filter and include_filter not in loc:
                        continue
                    collected_urls.add(loc)
                    if len(collected_urls) >= max_urls:
                        print("⚠️  Reached max_urls cap; stopping collection.")
                        return

        _walk_sitemap(sitemap_url)

        urls = sorted(collected_urls)
        print(f"✓ Loaded {len(urls)} URLs from sitemap (filtered by '{include_filter}')")
        return urls
    # ------------------------------------------------------------------------

    def load_source_urls(self, source_file: str = 'SEOTools/BlogPerformance/Source/Source.csv') -> List[str]:
        """Load blog URLs from source CSV file"""
        try:
            if not os.path.exists(source_file):
                raise FileNotFoundError(f"Source file not found: {source_file}")

            df = pd.read_csv(source_file)

            # Find URL column
            url_columns = ['url', 'URL', 'address', 'Address', 'page_url', 'link']
            url_col = None
            for col in url_columns:
                if col in df.columns:
                    url_col = col
                    break

            if not url_col:
                raise ValueError(f"No URL column found in {source_file}. Expected one of: {url_columns}")

            urls = df[url_col].dropna().tolist()
            print(f"✓ Loaded {len(urls)} URLs from source file")
            return urls

        except Exception as e:
            print(f"Error loading source URLs: {e}")
            return []

    def get_gsc_data(self, site_url: str, start_date: str, end_date: str, urls: List[str]) -> Dict:
        """Get GSC data for specific blog URLs"""
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['page'],
                'rowLimit': 25000
            }

            # Try different property formats
            property_urls = [
                site_url,
                f"sc-domain:{site_url.replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')}"
            ]

            for property_url in property_urls:
                try:
                    response = self.gsc_service.searchanalytics().query(
                        siteUrl=property_url,
                        body=request
                    ).execute()

                    print(f"✓ Using GSC property: {property_url}")
                    break

                except Exception as e:
                    continue
            else:
                print("No valid GSC property found")
                return {}

            gsc_data = {}
            for row in response.get('rows', []):
                url = row['keys'][0]
                if not url.startswith('http'):
                    url = site_url.rstrip('/') + url

                # Only include URLs that are in our source list
                if url in urls:
                    gsc_data[url] = {
                        'clicks': row['clicks'],
                        'impressions': row['impressions'],
                        'ctr': row['ctr'],
                        'position': row['position']
                    }

            print(f"✓ Retrieved GSC data for {len(gsc_data)} blog URLs")
            return gsc_data

        except Exception as e:
            print(f"GSC data retrieval failed: {e}")
            return {}

    def get_ga_data(self, property_ids: List[str], start_date: str, end_date: str, urls: List[str]) -> Dict:
        """Get GA4 data for specific blog URLs, trying multiple properties if needed"""
        try:
            print(f"📈 Fetching GA4 data for blog posts...")

            # Convert URLs to paths for GA4 filtering
            paths = []
            url_to_path = {}
            for url in urls:
                if url.startswith('http'):
                    path = '/' + '/'.join(url.split('/')[3:]) if len(url.split('/')) > 3 else '/'
                else:
                    path = url if url.startswith('/') else '/' + url
                paths.append(path)
                url_to_path[url] = path

            # Track which property was used for each path
            property_usage = {}
            ga_data = {}

            for property_id in property_ids:
                print(f"\nTrying GA4 property: {property_id}")

                # Get all sessions data
                request_body = {
                    'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                    'dimensions': [
                        {'name': 'pagePath'}
                    ],
                    'metrics': [
                        {'name': 'sessions'},
                        {'name': 'screenPageViews'},
                        {'name': 'bounceRate'},
                        {'name': 'averageSessionDuration'}
                    ],
                    'limit': 100000
                }

                try:
                    response = self.ga_service.properties().runReport(
                        property=f'properties/{property_id}',
                        body=request_body
                    ).execute()

                    # Process response and track which paths were found
                    found_paths = set()
                    for row in response.get('rows', []):
                        page_path = row['dimensionValues'][0]['value']
                        if page_path in paths:
                            found_paths.add(page_path)
                            if page_path not in ga_data:  # Only add if not already found in previous property
                                ga_data[page_path] = {
                                    'sessions_total': int(row['metricValues'][0]['value']),
                                    'pageviews': int(row['metricValues'][1]['value']),
                                    'bounce_rate': float(row['metricValues'][2]['value']) if row['metricValues'][2]['value'] != '0' else 0,
                                    'avg_session_duration': float(row['metricValues'][3]['value'])
                                }
                                property_usage[page_path] = property_id

                    print(f"Found data for {len(found_paths)} paths in property {property_id}")

                    # Get organic sessions
                    organic_request = {
                        'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                        'dimensions': [
                            {'name': 'pagePath'}
                        ],
                        'metrics': [
                            {'name': 'sessions'}
                        ],
                        'dimensionFilter': {
                            'filter': {
                                'fieldName': 'sessionDefaultChannelGroup',
                                'stringFilter': {
                                    'matchType': 'EXACT',
                                    'value': 'Organic Search'
                                }
                            }
                        },
                        'limit': 100000
                    }

                    organic_response = self.ga_service.properties().runReport(
                        property=f'properties/{property_id}',
                        body=organic_request
                    ).execute()

                    for row in organic_response.get('rows', []):
                        page_path = row['dimensionValues'][0]['value']
                        if page_path in paths and page_path in found_paths:
                            if page_path in ga_data:
                                ga_data[page_path]['sessions_organic'] = int(row['metricValues'][0]['value'])
                            else:
                                ga_data[page_path] = {'sessions_organic': int(row['metricValues'][0]['value'])}

                    # Get direct sessions
                    direct_request = {
                        'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                        'dimensions': [
                            {'name': 'pagePath'}
                        ],
                        'metrics': [
                            {'name': 'sessions'}
                        ],
                        'dimensionFilter': {
                            'filter': {
                                'fieldName': 'sessionDefaultChannelGroup',
                                'stringFilter': {
                                    'matchType': 'EXACT',
                                    'value': 'Direct'
                                }
                            }
                        },
                        'limit': 100000
                    }

                    direct_response = self.ga_service.properties().runReport(
                        property=f'properties/{property_id}',
                        body=direct_request
                    ).execute()

                    for row in direct_response.get('rows', []):
                        page_path = row['dimensionValues'][0]['value']
                        if page_path in paths and page_path in found_paths:
                            if page_path in ga_data:
                                ga_data[page_path]['sessions_direct'] = int(row['metricValues'][0]['value'])
                            else:
                                ga_data[page_path] = {'sessions_direct': int(row['metricValues'][0]['value'])}

                    # Get paid sessions
                    paid_request = {
                        'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                        'dimensions': [
                            {'name': 'pagePath'}
                        ],
                        'metrics': [
                            {'name': 'sessions'}
                        ],
                        'dimensionFilter': {
                            'filter': {
                                'fieldName': 'sessionDefaultChannelGroup',
                                'stringFilter': {
                                    'matchType': 'EXACT',
                                    'value': 'Paid Search'
                                }
                            }
                        },
                        'limit': 100000
                    }

                    paid_response = self.ga_service.properties().runReport(
                        property=f'properties/{property_id}',
                        body=paid_request
                    ).execute()

                    for row in paid_response.get('rows', []):
                        page_path = row['dimensionValues'][0]['value']
                        if page_path in paths and page_path in found_paths:
                            if page_path in ga_data:
                                ga_data[page_path]['sessions_paid'] = int(row['metricValues'][0]['value'])
                            else:
                                ga_data[page_path] = {'sessions_paid': int(row['metricValues'][0]['value'])}

                except Exception as e:
                    print(f"Error with property {property_id}: {e}")
                    continue

            # Ensure all paths have data entries and fill missing values with 0
            for path in paths:
                if path not in ga_data:
                    ga_data[path] = {}

                ga_data[path].setdefault('sessions_total', 0)
                ga_data[path].setdefault('sessions_organic', 0)
                ga_data[path].setdefault('sessions_direct', 0)
                ga_data[path].setdefault('sessions_paid', 0)
                ga_data[path].setdefault('pageviews', 0)
                ga_data[path].setdefault('bounce_rate', 0)
                ga_data[path].setdefault('avg_session_duration', 0)

            # Print property usage summary
            property_summary = {}
            for path, prop_id in property_usage.items():
                property_summary[prop_id] = property_summary.get(prop_id, 0) + 1

            print("\nGA4 Property Usage Summary:")
            for prop_id, count in property_summary.items():
                print(f"Property {prop_id}: {count} URLs")

            print(f"\n✓ Retrieved GA4 data for {len(ga_data)} blog URLs")
            return ga_data

        except Exception as e:
            print(f"❌ GA data retrieval failed: {e}")
            return {}

    def get_query_data_for_pages(self, site_url: str, start_date: str, end_date: str, urls: List[str]) -> Dict:
        """Get top 3 queries by impressions for specific pages"""
        try:
            query_data = {}

            # Try different property formats
            property_urls = [
                site_url,
                f"sc-domain:{site_url.replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')}"
            ]

            gsc_property = None
            for property_url in property_urls:
                try:
                    # Test with a simple request
                    test_request = {
                        'startDate': start_date,
                        'endDate': end_date,
                        'dimensions': ['page'],
                        'rowLimit': 1
                    }
                    self.gsc_service.searchanalytics().query(
                        siteUrl=property_url,
                        body=test_request
                    ).execute()
                    gsc_property = property_url
                    print(f"✓ Using GSC property: {gsc_property}")
                    break
                except Exception as e:
                    continue

            if not gsc_property:
                print("❌ No valid GSC property found")
                return {}

            print(f"🔍 {len(urls)} total URLs to get queries for. Starting...")
            for url in urls:
                try:
                    # Convert full URL to path for GSC - try multiple formats
                    url_formats = []

                    if url.startswith('http'):
                        # Extract path from full URL
                        url_parts = url.split('/')
                        if len(url_parts) > 3:
                            path = '/' + '/'.join(url_parts[3:])
                            url_formats.extend([
                                path,
                                path.rstrip('/'),
                                path + '/' if not path.endswith('/') else path
                            ])

                        # Also try the full URL
                        url_formats.append(url)
                    else:
                        # Already a path
                        url_formats.extend([
                            url,
                            url.rstrip('/'),
                            url + '/' if not url.endswith('/') else url
                        ])

                    # Remove duplicates while preserving order
                    url_formats = list(dict.fromkeys(url_formats))

                    queries = []
                    for url_format in url_formats:
                        request = {
                            'startDate': start_date,
                            'endDate': end_date,
                            'dimensions': ['query'],
                            'rowLimit': 50,  # Get more initially to sort by impressions
                            'dimensionFilterGroups': [{
                                'filters': [{
                                    'dimension': 'page',
                                    'operator': 'equals',
                                    'expression': url_format
                                }]
                            }]
                        }

                        try:
                            response = self.gsc_service.searchanalytics().query(
                                siteUrl=gsc_property,
                                body=request
                            ).execute()

                            if response.get('rows'):
                                # Found data with this URL format
                                for row in response.get('rows', []):
                                    queries.append({
                                        'query': row['keys'][0],
                                        'clicks': row['clicks'],
                                        'impressions': row['impressions'],
                                        'position': row['position']
                                    })
                                break  # Stop trying other formats

                        except Exception as e:
                            continue

                    # Sort by impressions (descending) and take top 3
                    queries = sorted(queries, key=lambda x: x['impressions'], reverse=True)[:3]
                    query_data[url] = queries

                    if queries:
                        print(f"✓ Found {len(queries)} queries for {url}")

                except Exception as e:
                    print(f"Error getting queries for {url}: {e}")
                    query_data[url] = []

            total_pages_with_queries = sum(1 for queries in query_data.values() if queries)
            print(f"✓ Retrieved query data for {total_pages_with_queries}/{len(urls)} pages")
            return query_data

        except Exception as e:
            print(f"Query data retrieval failed: {e}")
            return {}

    def analyze_blog_performance(
        self,
        site_url: str,
        ga_property_ids: List[str],
        days_back: int = 90,
        source_file: str = 'SEOTools/BlogPerformance/Source/Source.csv',
        output_file: str = 'SEOTools/BlogPerformance/Reports/blog_performance_analysis.xlsx',
        skip_queries: bool = False,
        sitemap_url: Optional[str] = None,
        include_filter: str = "/blog/"
    ) -> pd.DataFrame:
        """Main analysis function"""
        print("🔍 Starting blog performance analysis...")

        # Load URLs from sitemap or CSV
        if sitemap_url:
            print("📂 Loading URLs from sitemap...")
            source_urls = self.load_urls_from_sitemap(
                site_url=site_url,
                sitemap_url=sitemap_url,
                include_filter=include_filter
            )
        else:
            print("📂 Loading source URLs from CSV...")
            source_urls = self.load_source_urls(source_file)

        if not source_urls:
            raise ValueError("No URLs found from sitemap/source file")

        # Date range for API calls
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        print(f"📊 Analyzing {len(source_urls)} blog URLs from {start_date} to {end_date}")

        # Get GSC and GA data
        print("📊 Fetching GSC data...")
        gsc_data = self.get_gsc_data(site_url, start_date, end_date, source_urls)

        print("📈 Fetching GA4 data...")
        ga_data = self.get_ga_data(ga_property_ids, start_date, end_date, source_urls)

        # Create comprehensive dataset using source URLs
        blog_data = []
        for url in source_urls:
            # Extract path for GA data lookup
            if url.startswith('http'):
                path = '/' + '/'.join(url.split('/')[3:]) if len(url.split('/')) > 3 else '/'
            else:
                path = url

            gsc = gsc_data.get(url, {})
            ga = ga_data.get(path, {})

            blog_data.append({
                'url': url,
                'clicks': gsc.get('clicks', 0),
                'impressions': gsc.get('impressions', 0),
                'ctr': gsc.get('ctr', 0),
                'position': gsc.get('position', 0),
                'sessions_total': ga.get('sessions_total', 0),
                'sessions_organic': ga.get('sessions_organic', 0),
                'sessions_direct': ga.get('sessions_direct', 0),
                'sessions_paid': ga.get('sessions_paid', 0),
                'pageviews': ga.get('pageviews', 0),
                'bounce_rate': ga.get('bounce_rate', 0),
                'avg_session_duration': ga.get('avg_session_duration', 0)
            })

        df = pd.DataFrame(blog_data)

        # Sort by clicks (descending)
        df = df.sort_values('clicks', ascending=False)

        # Classify pages
        df['performance_category'] = df.apply(self.classify_page_performance, axis=1)

        # Get query data only if not skipped
        query_data = {}
        if not skip_queries:
            # Get struggling and potential pages for query analysis
            struggling_pages = df[df['performance_category'] == 'struggling']['url'].tolist()
            potential_pages = df[df['performance_category'] == 'potential']['url'].tolist()

            query_pages = struggling_pages + potential_pages

            if query_pages:
                print("🔍 Getting query data for struggling and potential pages...")
                query_data = self.get_query_data_for_pages(site_url, start_date, end_date, query_pages)
        else:
            print("⏭️ Skipping query data extraction as requested")

        # Generate Excel report
        self.generate_excel_report(df, query_data, output_file)

        return df

    def classify_page_performance(self, row: pd.Series) -> str:
        """Classify page performance based on traffic and engagement"""
        clicks = row['clicks']
        impressions = row['impressions']
        sessions_total = row['sessions_total']

        # Pages driving real traffic (last 3 months)
        if clicks >= 50 or sessions_total >= 50:
            return 'performing'

        # Pages with potential (good impressions but low clicks)
        elif impressions >= 500 and clicks < 50:
            return 'potential'

        # Struggling pages (either good impressions OR good sessions)
        elif (impressions >= 50 or sessions_total >= 10) and clicks < 50:
            return 'struggling'

        # Dead weight (minimal to no impressions/traffic)
        else:
            return 'dead'

    def generate_excel_report(self, df: pd.DataFrame, query_data: Dict, output_file: str):
        """Generate comprehensive Excel report with multiple tabs"""
        print(f"📝 Generating Excel report: {output_file}")

        # Create output directory
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Tab 1: All Pages (sorted by clicks)
            df.to_excel(writer, sheet_name='All Pages', index=False)

            # Tab 2: Summary
            summary_data = {
                'Metric': [
                    'Total Blog Pages',
                    'Pages Driving Traffic',
                    'Pages with Potential',
                    'Struggling Pages',
                    'Dead Weight Pages',
                    'Total Clicks (3 months)',
                    'Total Impressions (3 months)',
                    'Total Sessions (3 months)'
                ],
                'Count': [
                    len(df),
                    len(df[df['performance_category'] == 'performing']),
                    len(df[df['performance_category'] == 'potential']),
                    len(df[df['performance_category'] == 'struggling']),
                    len(df[df['performance_category'] == 'dead']),
                    df['clicks'].sum(),
                    df['impressions'].sum(),
                    df['sessions_total'].sum()
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Tab 3: Pages with Potential (with top 3 queries)
            potential_pages = df[df['performance_category'] == 'potential'].copy()
            if not potential_pages.empty:
                # Prepare potential pages with query data
                potential_with_queries = []
                for _, row in potential_pages.iterrows():
                    url = row['url']
                    query_row = {
                        'url': url,
                        'clicks': row['clicks'],
                        'impressions': row['impressions'],
                        'ctr': row['ctr'],
                        'position': row['position'],
                        'sessions_total': row['sessions_total']
                    }

                    # Add query data (top 3 by impressions)
                    queries = query_data.get(url, [])
                    for i, query in enumerate(queries[:3], 1):
                        query_row[f'query_{i}'] = query['query']
                        query_row[f'query_{i}_clicks'] = query['clicks']
                        query_row[f'query_{i}_impressions'] = query['impressions']
                        query_row[f'query_{i}_position'] = query['position']

                    # Fill empty query slots
                    for i in range(len(queries) + 1, 4):
                        query_row[f'query_{i}'] = ''
                        query_row[f'query_{i}_clicks'] = 0
                        query_row[f'query_{i}_impressions'] = 0
                        query_row[f'query_{i}_position'] = 0

                    potential_with_queries.append(query_row)

                potential_queries_df = pd.DataFrame(potential_with_queries)
                potential_queries_df.to_excel(writer, sheet_name='Pages with Potential', index=False)

            # Tab 4: Struggling Pages (with top 3 queries)
            struggling_pages = df[df['performance_category'] == 'struggling'].copy()
            if not struggling_pages.empty:
                # Prepare struggling pages with query data
                struggling_with_queries = []
                for _, row in struggling_pages.iterrows():
                    url = row['url']
                    query_row = {
                        'url': url,
                        'clicks': row['clicks'],
                        'impressions': row['impressions'],
                        'ctr': row['ctr'],
                        'position': row['position'],
                        'sessions_total': row['sessions_total']
                    }

                    # Add query data (top 3 by impressions)
                    queries = query_data.get(url, [])
                    for i, query in enumerate(queries[:3], 1):
                        query_row[f'query_{i}'] = query['query']
                        query_row[f'query_{i}_clicks'] = query['clicks']
                        query_row[f'query_{i}_impressions'] = query['impressions']
                        query_row[f'query_{i}_position'] = query['position']

                    # Fill empty query slots
                    for i in range(len(queries) + 1, 4):
                        query_row[f'query_{i}'] = ''
                        query_row[f'query_{i}_clicks'] = 0
                        query_row[f'query_{i}_impressions'] = 0
                        query_row[f'query_{i}_position'] = 0

                    struggling_with_queries.append(query_row)

                struggling_queries_df = pd.DataFrame(struggling_with_queries)
                struggling_queries_df.to_excel(writer, sheet_name='Struggling Pages', index=False)

            # Tab 5: Dead Pages (without query data)
            dead_pages = df[df['performance_category'] == 'dead'].copy()
            if not dead_pages.empty:
                dead_pages.to_excel(writer, sheet_name='Dead Pages', index=False)

        print(f"✅ Excel report generated: {output_file}")

        # Print summary
        print("\n📊 Blog Performance Summary:")
        print(f"   Total Blog Pages: {len(df):,}")
        print(f"   Pages Driving Traffic: {len(df[df['performance_category'] == 'performing']):,}")
        print(f"   Pages with Potential: {len(df[df['performance_category'] == 'potential']):,}")
        print(f"   Struggling Pages: {len(df[df['performance_category'] == 'struggling']):,}")
        print(f"   Dead Weight Pages: {len(df[df['performance_category'] == 'dead']):,}")


def main():
    parser = argparse.ArgumentParser(description='Blog Performance Analysis Tool')
    parser.add_argument('--site-url', required=True, help='Site URL (e.g., https://www.example.com/)')
    parser.add_argument('--ga-property-ids', required=True, help='Comma-separated list of GA4 Property IDs (e.g., 386754123,386754124)')
    parser.add_argument('--credentials', required=True, help='Path to service account credentials JSON')

    # NEW: sitemap option (takes precedence if provided)
    parser.add_argument('--sitemap', help='Sitemap URL (e.g., https://www.example.com/sitemap.xml)')
    parser.add_argument('--include-filter', default='/blog/', help='Substring filter for sitemap URLs (default: /blog/)')

    # Kept for backward compatibility
    parser.add_argument('--source-file', default='SEOTools/BlogPerformance/Source/Source.csv', help='Path to source CSV file with blog URLs')

    parser.add_argument('--days-back', type=int, default=90, help='Days of historical data to analyze (default: 90)')
    parser.add_argument('--output', default='SEOTools/BlogPerformance/Reports/blog_performance_analysis.xlsx', help='Output Excel file path')
    parser.add_argument('--skip-queries', action='store_true', help='Skip query data extraction to speed up analysis')

    args = parser.parse_args()

    # Parse GA property IDs
    ga_property_ids = [pid.strip() for pid in args.ga_property_ids.split(',')]

    # Initialize analyzer
    analyzer = BlogPerformanceAnalyzer(credentials_path=args.credentials)

    # Run analysis (sitemap takes precedence)
    results = analyzer.analyze_blog_performance(
        site_url=args.site_url,
        ga_property_ids=ga_property_ids,
        source_file=args.source_file,
        days_back=args.days_back,
        output_file=args.output,
        skip_queries=args.skip_queries,
        sitemap_url=args.sitemap,
        include_filter=args.include_filter
    )

    # Show top performing pages
    print("\n🎯 Top 10 Performing Blog Pages:")
    display_cols = ['url', 'clicks', 'impressions', 'sessions_total', 'performance_category']
    print(results[display_cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
