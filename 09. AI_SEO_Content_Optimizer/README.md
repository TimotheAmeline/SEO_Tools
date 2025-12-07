# SEO Content Optimizer

A Python-based tool for analyzing and optimizing website content for SEO.

## Features

- URL content analysis and comparison
- Competitor content analysis
- SERP feature tracking
- GPT-powered content optimization recommendations
- Comprehensive SEO reports
- Caching system for efficient API usage

## Requirements

- Python 3.10+
- OpenAI API key
- Internet connection for web scraping

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

Run the main script:
```bash
python main.py
```

Follow the CLI prompts to:
1. Enter the target URL
2. Input competitor URLs
3. Specify SERP features
4. Select GPT model version
5. Generate optimization report

## Output

The tool generates two types of reports:
- JSON report for programmatic analysis
- Human-readable report with actionable recommendations

## Project Structure

```
SEOContentOptimizer/
├── main.py                 # Main entry point
├── src/
│   ├── content_analyzer.py # Content analysis logic
│   ├── gpt_analyzer.py     # GPT integration
│   ├── scraper.py         # Web scraping utilities
│   ├── reporter.py        # Report generation
│   └── utils.py           # Helper functions
├── cache/                 # Cached API responses
├── reports/              # Generated reports
└── requirements.txt      # Project dependencies
```

## Error Handling

The tool includes comprehensive error handling for:
- Network issues
- Parsing failures
- API limitations
- Invalid URLs
- Rate limiting

## Contributing

Contributions are welcome. Please follow the established coding standards and documentation requirements when contributing.
