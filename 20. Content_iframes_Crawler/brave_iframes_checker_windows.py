"""
Brave Headless Iframe Checker - Windows Compatible Version
Uses Brave browser in headless mode to check iframe content after lazy loading
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import csv
import os
import time
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

class BraveHeadlessIframeChecker:
    def __init__(self, sitemap_url="https://www.example.com/sitemap.xml", delay=0.5):
        self.sitemap_url = sitemap_url
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        self.blog_urls = []
        self.broken_iframes = []
        self.driver = None
        
    def setup_brave_driver(self):
        """Setup Brave browser in background mode (windowed but minimized)"""
        print("🔧 Setting up Brave browser in background mode...")
        
        try:
            # Brave browser options
            options = Options()
            
            # Don't use headless - use windowed but try to keep it hidden
            # options.add_argument("--headless")  # Commented out - this breaks lazy loading
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage") 
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-logging")
            options.add_argument("--log-level=3")
            options.add_argument("--silent")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            
            # Options to try to keep window in background
            options.add_argument("--start-minimized")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-backgrounding-occluded-windows")
            
            # Point to Brave browser executable - Windows-focused paths
            brave_paths = []
            
            if platform.system() == "Windows":
                # Windows-specific paths (prioritized)
                brave_paths = [
                    "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",  # Windows 64-bit
                    "C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",  # Windows 32-bit
                    os.path.expanduser("~\\AppData\\Local\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"),  # Windows user install
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "BraveSoftware\\Brave-Browser\\Application\\brave.exe"),  # Alternative user install
                ]
            else:
                # Fallback paths for other systems
                brave_paths = [
                    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",  # macOS
                    "/usr/bin/brave-browser",  # Linux
                    "/opt/brave.com/brave/brave-browser",  # Linux alternative
                ]
            
            brave_found = False
            for path in brave_paths:
                if os.path.exists(path):
                    options.binary_location = path
                    brave_found = True
                    print(f"✅ Found Brave at: {path}")
                    break
            
            if not brave_found:
                print("❌ Brave browser not found in standard locations")
                print("💡 Please install Brave browser from: https://brave.com/")
                if platform.system() == "Windows":
                    print("   Expected locations:")
                    for path in brave_paths:
                        print(f"     {path}")
                return False
            
            # Setup ChromeDriver with version matching
            service = None
            
            if WEBDRIVER_MANAGER_AVAILABLE:
                print("📱 Getting ChromeDriver compatible with Brave...")
                try:
                    # Try to get the latest ChromeDriver
                    service = Service(ChromeDriverManager().install())
                    print("✅ Downloaded ChromeDriver")
                except Exception as download_error:
                    print(f"⚠️  ChromeDriver download failed: {download_error}")
                    service = None
            
            if service is None:
                print("📱 Trying system ChromeDriver...")
                try:
                    service = Service()  # Will use chromedriver from PATH
                    # Test if system chromedriver works
                    temp_driver = webdriver.Chrome(service=service, options=options)
                    temp_driver.quit()
                    print("✅ System ChromeDriver works")
                except Exception as system_error:
                    print(f"❌ System ChromeDriver failed: {system_error}")
                    print("💡 Please install ChromeDriver:")
                    if platform.system() == "Windows":
                        print("   1. Download ChromeDriver from: https://chromedriver.chromium.org/")
                        print("   2. Extract chromedriver.exe to a folder in your PATH")
                        print("   3. Or install via: choco install chromedriver")
                    else:
                        print("   brew install --cask chromedriver")
                        print("   xattr -d com.apple.quarantine $(which chromedriver)")
                    return False
            
            print("🚀 Starting Brave in background mode (windowed but minimized)...")
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Test that it's working
            print("🧪 Testing Brave WebDriver...")
            self.driver.get("about:blank")
            
            # Try to minimize the window after creation
            try:
                self.driver.minimize_window()
                print("🔽 Minimized Brave window")
            except Exception as min_error:
                print(f"⚠️  Could not minimize window: {min_error}")
            
            print("✅ Brave WebDriver ready (should be minimized but not headless)")
            print("💡 This allows lazy loading to work properly")
            return True
            
        except Exception as e:
            print(f"❌ Brave WebDriver failed: {str(e)}")
            print("💡 Troubleshooting:")
            if not WEBDRIVER_MANAGER_AVAILABLE:
                print("   - Install webdriver-manager: pip install webdriver-manager")
            print("   - Install Brave browser from: https://brave.com/")
            if platform.system() == "Windows":
                print("   - Or install ChromeDriver from: https://chromedriver.chromium.org/")
                print("   - Or via Chocolatey: choco install chromedriver")
            else:
                print("   - Or install ChromeDriver manually: brew install chromedriver")
            self.driver = None
            return False

    def ensure_driver_working(self):
        """Ensure Brave driver is working, recreate if needed"""
        try:
            # Test if driver is still responsive
            if self.driver:
                self.driver.current_url  # Simple test
                return True
        except:
            print("    🔄 Brave session crashed, recreating driver...")
            
        # Cleanup old driver
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
            
        # Create new driver
        return self.setup_brave_driver()
    
    def get_sitemap_urls(self):
        """Fetch and parse sitemap.xml to get all URLs"""
        print(f"🔍 Fetching sitemap: {self.sitemap_url}")
        
        try:
            response = self.session.get(self.sitemap_url, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []
            
            for url_elem in root.findall('.//ns:url', namespace):
                loc_elem = url_elem.find('ns:loc', namespace)
                if loc_elem is not None:
                    urls.append(loc_elem.text)
            
            print(f"✅ Found {len(urls)} total URLs in sitemap")
            return urls
            
        except Exception as e:
            print(f"❌ Error fetching sitemap: {str(e)}")
            return []
    
    def filter_blog_urls(self, all_urls):
        """Filter URLs to only include blog pages"""
        blog_urls = [url for url in all_urls if '/blog/' in url]
        print(f"📝 Filtered to {len(blog_urls)} blog URLs")
        return blog_urls
    
    def has_main_wrapper_iframes(self, page_url):
        """Quick HTTP check to see if page has main-wrapper divs with iframes"""
        try:
            response = self.session.get(page_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            main_wrappers = soup.find_all('div', class_='preview__main-wrapper')
            
            # Check if any main-wrapper has an iframe
            for wrapper in main_wrappers:
                if wrapper.find('iframe'):
                    return True, len(main_wrappers)
            
            return False, len(main_wrappers)
            
        except requests.RequestException as e:
            print(f"    ⚠️  Error checking page structure: {str(e)}")
            return False, 0

    def check_page_iframes_with_brave(self, page_url):
        """Load page with Brave and wait properly for each iframe to load"""
        try:
            print(f"    🌐 Loading page with Brave...")
            self.driver.get(page_url)
            time.sleep(5)  # Initial wait
            
            print(f"    🎯 Finding all main-wrapper iframes...")
            main_wrappers = self.driver.find_elements(By.CLASS_NAME, "preview__main-wrapper")
            print(f"    Found {len(main_wrappers)} main-wrapper div(s)")
            
            if not main_wrappers:
                return []
            
            broken_iframes = []
            
            # Check each iframe with extended waiting
            for i, wrapper in enumerate(main_wrappers, 1):
                try:
                    print(f"    🎯 Processing iframe {i}/{len(main_wrappers)}...")
                    
                    # Scroll to this iframe to trigger lazy loading
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", wrapper)
                    time.sleep(3)
                    
                    # Wait and check for loading over time
                    iframe = wrapper.find_element(By.TAG_NAME, "iframe")
                    max_wait = 15
                    start_time = time.time()
                    last_src = ""
                    
                    print(f"        ⏳ Waiting up to {max_wait}s for iframe to load...")
                    
                    while time.time() - start_time < max_wait:
                        src = iframe.get_attribute('src') or ''
                        data_src = iframe.get_attribute('data-src') or ''
                        
                        # Check if src has changed (sign of loading)
                        if src != last_src:
                            print(f"        📝 Src changed to: '{src[:50]}{'...' if len(src) > 50 else ''}'")
                            last_src = src
                        
                        # If we have a real src URL, it's loaded
                        if src and src not in ['', 'about:blank'] and 'example.com' in src:
                            elapsed = time.time() - start_time
                            print(f"        ✅ Loaded after {elapsed:.1f}s")
                            break
                        
                        time.sleep(2)
                    
                    # Final check after waiting
                    final_src = iframe.get_attribute('src') or ''
                    final_data_src = iframe.get_attribute('data-src') or ''
                    elapsed = time.time() - start_time
                    
                    print(f"        📋 Final state after {elapsed:.1f}s:")
                    print(f"            src: '{final_src}'")
                    print(f"            data-src: '{final_data_src}'")
                    
                    # Only flag as broken if definitely no URLs
                    if not final_src and not final_data_src:
                        print(f"        ❌ BROKEN: No src or data-src after {elapsed:.1f}s")
                        broken_iframes.append({
                            'position': i,
                            'src': final_src,
                            'data_src': final_data_src,
                            'reason': f'No src or data-src after {elapsed:.1f}s of waiting'
                        })
                    elif final_src and 'example.com' in final_src:
                        print(f"        ✅ WORKING: Has valid iframe URL")
                    else:
                        print(f"        🤔 UNCLEAR: Has data-src but no src (not flagging as broken)")
                    
                except Exception as e:
                    print(f"        ❌ Error processing iframe {i}: {e}")
            
            return broken_iframes
            
        except Exception as e:
            print(f"    ❌ Error loading page: {str(e)}")
            return []
    
    def crawl_blog_pages(self):
        """Main crawling function using Brave only when needed"""
        total_pages = len(self.blog_urls)
        print(f"\n🚀 Starting optimized iframe checking on {total_pages} blog pages")
        print("Strategy: HTTP check first, Brave only for pages with iframes")
        print("=" * 60)
        
        pages_with_iframes = 0
        pages_without_iframes = 0
        
        for i, page_url in enumerate(self.blog_urls, 1):
            # Progress update
            percentage = (i / total_pages) * 100
            print(f"\n📄 {i}/{total_pages} URLs checked, {percentage:.1f}% complete")
            print(f"Checking: {page_url}")
            
            # Step 1: Quick HTTP check for main-wrapper iframes
            has_iframes, wrapper_count = self.has_main_wrapper_iframes(page_url)
            
            if not has_iframes:
                pages_without_iframes += 1
                if wrapper_count > 0:
                    print(f"    ℹ️  Found {wrapper_count} main-wrapper(s) but no iframes - skipping Brave")
                else:
                    print(f"    ℹ️  No main-wrapper divs found - skipping Brave")
                continue
            
            # Step 2: Use Brave for pages that have iframes
            pages_with_iframes += 1
            print(f"    🎯 Found main-wrapper(s) with iframe(s) - using Brave to check content")
            
            # Ensure Brave driver is working
            if not self.ensure_driver_working():
                print(f"    ❌ Could not recreate Brave driver - skipping this page")
                continue
            
            broken_iframes = self.check_page_iframes_with_brave(page_url)
            
            if not broken_iframes:
                print(f"    ✅ All iframes loaded successfully")
            else:
                print(f"    ❌ Found {len(broken_iframes)} broken iframe(s)")
                
                for broken in broken_iframes:
                    issue = {
                        'from_url': page_url,
                        'iframe_position': f"Main-wrapper {broken['position']}",
                        'src': broken.get('src', 'EMPTY'),
                        'data_src': broken.get('data_src', 'EMPTY'),
                        'reason': broken['reason'],
                        'iframe_url': broken.get('iframe_url', 'N/A'),
                        'content_length': broken.get('content_length', 'N/A')
                    }
                    self.broken_iframes.append(issue)
            
            time.sleep(self.delay)
        
        print(f"\n📊 Scanning efficiency:")
        print(f"    Pages with iframes (Brave used): {pages_with_iframes}")
        print(f"    Pages without iframes (skipped): {pages_without_iframes}")
        print(f"    Speed improvement: {pages_without_iframes}/{total_pages} pages skipped")
    
    def create_output_directory(self):
        """Create output directory if it doesn't exist - Windows compatible"""
        if platform.system() == "Windows":
            # Use current directory for Windows to avoid permission issues
            output_dir = os.path.join(os.getcwd(), "iframes_crawler_output")
        else:
            output_dir = os.path.join(os.path.expanduser("~"), "iframes_crawler")
        
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def save_results_to_csv(self):
        """Save broken iframe results to CSV"""
        output_dir = self.create_output_directory()
        output_path = os.path.join(output_dir, "output.csv")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'From URL', 
                'Iframe Position',
                'Src Attribute',
                'Data-Src Attribute',
                'Reason',
                'Iframe URL After Loading',
                'Content Length'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.broken_iframes:
                writer.writerow({
                    'From URL': result['from_url'],
                    'Iframe Position': result['iframe_position'],
                    'Src Attribute': result['src'],
                    'Data-Src Attribute': result['data_src'],
                    'Reason': result['reason'],
                    'Iframe URL After Loading': result.get('iframe_url', 'N/A'),
                    'Content Length': result.get('content_length', 'N/A')
                })
        
        print(f"💾 Results saved to: {output_path}")
        return output_path
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 60)
        print("📊 FINAL SUMMARY")
        print("=" * 60)
        
        total_pages = len(self.blog_urls)
        total_broken = len(self.broken_iframes)
        
        print(f"Blog pages checked: {total_pages}")
        print(f"Broken iframes found: {total_broken}")
        
        if total_broken > 0:
            print(f"\n❌ Broken iframe details:")
            for result in self.broken_iframes:
                print(f"  Page: {result['from_url']}")
                print(f"  Position: {result['iframe_position']}")
                print(f"  Issue: {result['reason']}")
                print(f"  Src: {result['src']}")
                print(f"  Data-Src: {result['data_src']}")
                print()
        else:
            print(f"\n🎉 All iframes loaded content successfully after lazy loading!")
    
    def cleanup(self):
        """Clean up Brave WebDriver"""
        if self.driver:
            self.driver.quit()
            print("🧹 Brave WebDriver closed")
    
    def run(self):
        """Main execution function"""
        print("Brave Background Iframe Checker - Windows Compatible")
        print("Checking iframe content with Brave browser (windowed but minimized)")
        print("Note: Brave window will open but should stay minimized")
        print(f"Running on: {platform.system()} {platform.release()}")
        print("=" * 60)
        
        try:
            # Setup Brave
            if not self.setup_brave_driver():
                return False
            
            # Step 1: Get sitemap URLs
            all_urls = self.get_sitemap_urls()
            if not all_urls:
                return False
            
            # Step 2: Filter blog URLs
            self.blog_urls = self.filter_blog_urls(all_urls)
            if not self.blog_urls:
                return False
            
            # Step 3: Check pages with Brave
            self.crawl_blog_pages()
            
            # Step 4: Save results and print summary
            if self.broken_iframes:
                self.save_results_to_csv()
            
            self.print_summary()
            
            return len(self.broken_iframes) == 0
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Process interrupted by user")
            if self.broken_iframes:
                self.save_results_to_csv()
            self.print_summary()
            return False
        except Exception as e:
            print(f"\n💥 Unexpected error: {str(e)}")
            return False
        finally:
            self.cleanup()

def main():
    checker = BraveHeadlessIframeChecker(delay=0.5)
    success = checker.run()
    
    if success:
        print("\n✅ All iframe checks passed!")
        exit(0)
    else:
        print("\n❌ Broken iframes found")
        exit(1)

if __name__ == "__main__":
    main()