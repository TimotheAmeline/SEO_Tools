# Iframe Checker

A Python tool to validate iframe response codes across blog pages using sitemap-based crawling with Brave browser automation.

## Overview

This tool automatically:
1. Fetches your sitemap.xml
2. Filters for blog pages (`/blog/` URLs)
3. Identifies pages with template preview iframes
4. Uses Brave browser to properly trigger lazy loading
5. Detects broken iframes that fail to load content
6. Reports problematic iframes in CSV format

## Features

- **Sitemap-based crawling**: Uses your sitemap as source of truth instead of recursive crawling
- **Smart page filtering**: Only uses browser automation on pages that actually have iframes
- **Proper lazy loading detection**: Uses real browser (Brave) to trigger lazy loading mechanisms
- **Minimized window operation**: Runs Brave in minimized window to avoid disrupting workflow
- **Conservative detection**: Only flags iframes that definitively fail to load after extended waiting
- **Progress tracking**: Real-time progress updates with count and percentage
- **Selective reporting**: Only reports iframes that fail to load content
- **Crash recovery**: Automatically recreates browser session if it crashes

## Requirements

- Python 3.6+
- Brave browser installed
- Required packages:
  ```bash
  pip install requests beautifulsoup4 selenium webdriver-manager
  ```

## Installation

1. **Install Brave browser** (if not already installed):
   - Download from: https://brave.com/
   - Or via Homebrew: `brew install --cask brave-browser`

2. **Install Python dependencies**:
   ```bash
   pip install requests beautifulsoup4 selenium webdriver-manager
   ```

3. **Download the script**:
   ```bash
   # Save brave_checker.py to your project folder
   ```

## Usage

### Basic Usage
```bash
python brave_checker.py
```

### What It Does

1. **Fetches sitemap**: Downloads `https://www.example.com/sitemap.xml`
2. **Filters URLs**: Keeps only URLs containing `/blog/`
3. **Quick filtering**: Uses HTTP requests to identify pages with iframe content
4. **Browser automation**: Uses Brave browser only for pages that have iframes in `preview__main-wrapper` divs
5. **Lazy loading trigger**: Scrolls to each iframe and waits up to 15 seconds for content to load
6. **Progress updates**: Shows completion status like `125/400 URLs checked, 31.3% complete`
7. **Generates report**: Creates CSV with iframes that fail to load after extended waiting

## Output

### Console Output
```
Brave Background Iframe Checker
Checking iframe content with Brave browser (windowed but minimized)
============================================================
🔧 Setting up Brave browser in background mode...
✅ Found Brave at: /Applications/Brave Browser.app/Contents/MacOS/Brave Browser
🚀 Starting Brave in background mode (windowed but minimized)...
✅ Brave WebDriver ready (should be minimized but not headless)

🔍 Fetching sitemap: https://www.example.com/sitemap.xml
✅ Found 399 total URLs in sitemap
📝 Filtered to 318 blog URLs

🚀 Starting optimized iframe checking on 318 blog pages
Strategy: HTTP check first, Brave headless only for pages with iframes
============================================================

📄 125/318 URLs checked, 39.3% complete
Checking: https://www.example.com/blog/pitch-deck-examples/
    ℹ️  No main-wrapper divs found - skipping Brave

📄 126/318 URLs checked, 39.6% complete
Checking: https://www.example.com/blog/sales-presentation-examples/
    🎯 Found main-wrapper(s) with iframe(s) - using Brave headless to check content
    🌐 Loading page with Brave (headless)...
    🎯 Finding all main-wrapper iframes...
    Found 12 main-wrapper div(s)
    🎯 Processing iframe 1/12...
        ⏳ Waiting up to 15s for iframe to load...
        📝 Src changed to: 'https://www.example.com/496ff67598d650ed/biotech...'
        ✅ Loaded after 3.2s
        ✅ WORKING: Iframe loaded successfully
    ✅ All iframes loaded successfully
```

### CSV Output
File: `SEOTools/iframes_crawler/output.csv`

| From URL | Iframe Position | Src Attribute | Data-Src Attribute | Reason | Iframe URL After Loading | Content Length |
|----------|-----------------|---------------|---------------------|--------|--------------------------|----------------|
| https://www.example.com/blog/broken-example/ | Main-wrapper 1 | EMPTY | EMPTY | No src or data-src after 15.3s of waiting | N/A | N/A |

## How It Works

### Two-Phase Approach

**Phase 1: HTTP Pre-filtering (Fast)**
- Downloads page HTML via HTTP requests
- Checks for presence of `div.preview__main-wrapper` elements with iframes
- Skips pages without iframe content (majority of blog pages)

**Phase 2: Browser Automation (Accurate)**
- Uses Brave browser for pages that have iframes
- Loads page in minimized window (allows lazy loading to work)
- Scrolls to each iframe individually to trigger loading
- Waits up to 15 seconds per iframe for src attribute to populate
- Only flags as broken if no src/data-src after extended waiting

### Why Brave Browser?

- **Chromium-based**: Same engine as Chrome, excellent web compatibility
- **Lazy loading support**: Real browser window allows lazy loading to trigger properly
- **Minimized operation**: Runs in background without disrupting workflow
- **Headless limitations**: True headless mode breaks many lazy loading systems
- **No Safari focus stealing**: Unlike Safari WebDriver, doesn't constantly bring window to foreground

## Configuration

### Customizing Wait Times
Edit the script to adjust iframe loading timeouts:
```python
max_wait = 20  # Wait up to 20 seconds per iframe
```

### Custom Sitemap URL
```python
checker = BraveBackgroundIframeChecker(sitemap_url="https://example.com/sitemap.xml")
```

### Delay Between Pages
```python
checker = BraveBackgroundIframeChecker(delay=1.0)  # 1 second between pages
```

## Exit Codes

- `0`: All iframes loaded successfully
- `1`: Broken iframes found or process failed
- `130`: Process interrupted by user (Ctrl+C)

## Troubleshooting

### Common Issues

**Brave browser not found**
```bash
# Install Brave browser
brew install --cask brave-browser
# Or download from https://brave.com/
```

**ChromeDriver version mismatch**
```bash
# Clear webdriver cache and update
rm -rf ~/.wdm
pip install --upgrade webdriver-manager

# Or install ChromeDriver manually
brew install --cask chromedriver
xattr -d com.apple.quarantine $(which chromedriver)
```

**Brave window keeps appearing**
- This is normal - the window opens minimized
- The tool needs a real window for lazy loading to work properly
- The window should stay minimized and not interfere with your work

**No iframes found (false negatives)**
- Some pages may use different div classes for iframe containers
- The tool specifically looks for `div.preview__main-wrapper` elements
- Check page HTML structure if expected iframes aren't detected

**Too many false positives**
- Increase the wait time per iframe in the script
- Some very slow-loading templates may need more than 15 seconds
- Check your internet connection speed

### Debug Mode
To see more details about what's happening:
- Watch the console output for detailed per-iframe status
- Check Brave browser window manually to see loading behavior
- Use developer tools in Brave to debug specific iframe loading issues

## Performance

### Efficiency Optimization
- **HTTP pre-filtering**: ~95% of blog pages have no iframes and are skipped
- **Browser automation**: Only used on pages that actually need checking (~5% of pages)
- **Parallel optimization**: Could be enhanced for faster processing

### Typical Performance
- **318 blog pages**: ~10-15 minutes total processing time
- **Pages without iframes**: <1 second each (HTTP only)
- **Pages with iframes**: ~15-30 seconds each (browser automation)
- **Speed bottleneck**: Waiting for lazy loading (necessary for accuracy)

## File Structure
```
SEOTools/
└── iframes_crawler/
    ├── brave_checker.py
    ├── output.csv
    └── README.md
```

## Advanced Usage

### Running in CI/CD
```bash
#!/bin/bash
python brave_checker.py
if [ $? -eq 0 ]; then
    echo "✅ All iframes healthy"
else
    echo "❌ Broken iframes found - check output.csv"
    exit 1
fi
```

### Automated Scheduling
Add to crontab for weekly checks:
```bash
# Run every Monday at 9 AM
0 9 * * 1 cd /path/to/project && python brave_checker.py
```

### Filtering Results
The CSV can be filtered for specific issues:
```bash
# Show only completely empty iframes
grep "No src or data-src" output.csv

# Count broken iframes by type
cut -d',' -f5 output.csv | sort | uniq -c
```

## Limitations

- Only checks iframes within `div.preview__main-wrapper` elements
- Requires Brave browser installation
- Limited to blog pages containing `/blog/` in URL
- Does not check iframe content quality, only loading success
- Requires real browser window (minimized) - cannot run completely headless
- Processing time scales with number of pages containing iframes

## Technical Details

### Browser Automation
- Uses Selenium WebDriver with Brave browser
- Runs in windowed mode (minimized) to enable lazy loading
- Automatically downloads compatible ChromeDriver version
- Handles browser crashes with automatic session recreation

### Detection Logic
- **Working iframe**: Has populated `src` attribute with a valid URL after waiting
- **Broken iframe**: No `src` or `data-src` attributes after 15+ seconds of waiting
- **Conservative approach**: When in doubt, assumes iframe is working to minimize false positives

### Error Recovery
- Automatic browser session recreation on crashes
- Graceful handling of network timeouts
- Continues processing other pages if individual pages fail
- Saves partial results if process is interrupted

## Contributing

Potential enhancements:
- Support for other iframe container classes
- Parallel processing for faster scanning
- Content quality checking (beyond just loading)
- Integration with monitoring systems
- Support for other browsers (Firefox, Chrome)

## License

Internal tool for generic SEO analysis.
