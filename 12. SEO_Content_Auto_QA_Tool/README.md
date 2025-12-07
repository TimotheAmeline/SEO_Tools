# SEO Auto QA

An automated SEO quality assurance testing tool that detects and alerts on critical SEO changes between website versions. The tool tracks historical changes, analyzes rendering, and provides intelligent alerts about SEO-impacting modifications.

## Features

- Baseline capture of SEO elements from specified URLs
- Comparison between baseline and current state
- Historical tracking of changes over time
- Intelligent alerting based on change significance
- Core Web Vitals monitoring
- Email and Slack notifications
- HTML and JSON report generation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/seo-auto-qa.git
cd seo-auto-qa
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

## Configuration

The tool uses a YAML configuration file (`config.yaml`) for settings. You can create a default configuration by running:

```bash
python -m seo_auto_qa init
```

Key configuration sections:

### Crawler Settings
```yaml
crawler:
  max_pages: 100
  timeout: 30000
  user_agent: "SEO Auto QA Bot/1.0"
  javascript_enabled: true
  wait_for_network_idle: true
  viewport:
    width: 1920
    height: 1080
```

### Storage Settings
```yaml
storage:
  database_url: "sqlite:///seo_qa.db"
  history_retention_days: 90
```

### Monitoring Settings
```yaml
monitoring:
  urls:
    - "https://example.com"
  crawl_frequency: "daily"
  alert_thresholds:
    critical:
      title_change: true
      meta_description_change: true
      h1_change: true
      canonical_change: true
```

### Notification Settings
```yaml
notifications:
  email:
    enabled: false
    smtp_server: ""
    smtp_port: 587
    sender_email: ""
    recipient_emails: []
  slack:
    enabled: false
    webhook_url: ""
```

## Usage

### Initialize
Create a new configuration file:
```bash
python -m seo_auto_qa init
```

### Capture Baseline
Capture baseline SEO data for configured URLs:
```bash
python -m seo_auto_qa baseline
```

Or for a specific URL:
```bash
python -m seo_auto_qa baseline --url https://example.com
```

### Compare
Compare current state against baseline:
```bash
python -m seo_auto_qa compare
```

Generate HTML report:
```bash
python -m seo_auto_qa compare --format html
```

### View History
View historical changes:
```bash
python -m seo_auto_qa history
```

View last 7 days of history:
```bash
python -m seo_auto_qa history --days 7
```

### Cleanup
Remove old data based on retention period:
```bash
python -m seo_auto_qa cleanup
```

## Tracked SEO Elements

The tool monitors the following SEO elements:

1. Meta Tags
   - Title
   - Description
   - Robots
   - Canonical

2. Header Tags
   - H1-H6 hierarchy
   - Content and structure

3. Structured Data
   - Schema markup
   - JSON-LD implementation

4. Images
   - Alt attributes
   - Title attributes
   - Presence/removal

5. Links
   - Internal linking structure
   - External links
   - Broken links

6. Performance
   - Core Web Vitals
     - Largest Contentful Paint (LCP)
     - Cumulative Layout Shift (CLS)
     - First Input Delay (FID)

## Change Classification

Changes are classified into three categories:

1. Critical
   - Title tag modifications
   - Meta description changes
   - H1 tag changes
   - Canonical URL changes
   - Performance degradation

2. Warning
   - H2 tag modifications
   - Image alt text changes
   - Internal link structure changes
   - Schema markup modifications

3. Info
   - H3+ tag changes
   - Minor content updates
   - Performance improvements

## Reports

The tool generates detailed reports in both JSON and HTML formats, including:

- Change summary
- Detailed change log
- Performance metrics
- Impact scores
- Historical trends

## Notifications

Configure email and/or Slack notifications to receive alerts about:

- Critical changes
- Performance issues
- Baseline updates
- Error conditions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Playwright for browser automation
- BeautifulSoup for HTML parsing
- SQLAlchemy for database management
- Click for CLI interface
- Rich for terminal formatting 