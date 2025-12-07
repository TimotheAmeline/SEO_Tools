# SEO Analyzer & Optimizer

## Overview
This tool analyzes and optimizes SEO elements (titles, meta descriptions, H1s, URLs) for multiple pages using AI-powered optimization. It identifies SEO issues based on established guidelines and uses the DeepSeek API to generate improved versions of problematic elements.

## What It Does
- **Batch SEO Analysis**: Processes hundreds of URLs from CSV/Excel files
- **Issue Detection**: Identifies length problems, keyword placement issues, and guideline violations
- **AI-Powered Optimization**: Uses DeepSeek API to generate optimized titles, descriptions, and H1s
- **Smart Filtering**: Only optimizes pages with significant issues to save API costs
- **Real-time Output**: Provides incremental CSV results as analysis progresses
- **Checkpoint System**: Resume interrupted analyses from where they left off
- **Comprehensive Reporting**: Detailed issue breakdown and optimization rationale

## Key Features
- **Length Validation**: Ensures titles ≤60 chars, descriptions ≤160 chars, H1s ≤55 chars
- **Keyword Optimization**: Places primary keywords in optimal positions
- **Brand Guidelines**: Intelligent brand name inclusion based on available space
- **Fallback System**: Provides reliable fallbacks when AI optimization fails
- **Issue Prioritization**: Distinguishes between minor and significant SEO problems
- **Cross-element Analysis**: Detects redundancy between titles, H1s, and descriptions

## Requirements
- Python 3.x
- Required packages: pandas, requests, beautifulsoup4, numpy
- DeepSeek API key (for optimization features)

## Setup
1. Install dependencies: `pip install pandas requests beautifulsoup4 numpy`
2. Get DeepSeek API key from their platform
3. Prepare CSV/Excel file with columns: URL, Title, H1, Description

## Usage
**Basic analysis with optimization:**
```bash
python seo_analyzer.py --input your_data.csv --api-key YOUR_API_KEY
```

**Test mode (no API calls):**
```bash
python seo_analyzer.py --input your_data.csv --skip-api
```

**Resume interrupted analysis:**
```bash
python seo_analyzer.py --input your_data.csv --api-key YOUR_API_KEY --resume
```

**Run demo with sample data:**
```bash
python seo_analyzer.py demo
```

**Limit analysis to first 100 rows:**
```bash
python seo_analyzer.py --input data.csv --api-key KEY --limit 100
```

## Command Line Options
- `--input, -i`: Input CSV/Excel file (required)
- `--output, -o`: Output file path (defaults to timestamped CSV)
- `--api-key, -k`: DeepSeek API key for optimization
- `--limit, -l`: Limit analysis to first N rows
- `--skip-api, -s`: Skip API calls for testing
- `--resume, -r`: Resume from checkpoint
- `--debug, -d`: Enable debug mode with full error traces

## Input File Format
CSV or Excel file with columns:
- **URL**: Full page URL
- **Title**: Current page title
- **H1**: Current H1 tag content
- **Description**: Current meta description

Missing values are handled gracefully (treated as empty strings).

## SEO Guidelines Applied
**Title Optimization:**
- Maximum 60 characters
- Primary keyword in first 30 characters
- Brand name only if space permits
- Complete words/thoughts at endings

**Description Optimization:**
- Maximum 160 characters
- Include 1-2 secondary keywords
- Clear value proposition
- Natural call-to-action when relevant

**H1 Optimization:**
- Maximum 55 characters
- Keyword-focused version of title
- Directly addresses user intent
- No brand name unless it's the keyword

**URL Analysis:**
- 2-5 terms maximum in slug
- Hyphen-separated keywords only
- Remove articles and prepositions

## Output Files
- **Main Results**: Comprehensive analysis with optimizations
- **Incremental Results**: Real-time CSV updates during processing
- **Checkpoint File**: JSON file for resuming interrupted runs

## Issue Detection Categories
**Significant Issues (trigger optimization):**
- Titles/descriptions exceeding max length
- Missing primary keywords
- Very short content (titles <40 chars, descriptions <140 chars)
- Poor keyword positioning

**Minor Issues (analysis only):**
- Missing brand name when space permits
- Missing call-to-action in short descriptions
- Minor length optimizations

## AI Optimization Process
1. **Issue Analysis**: Identifies specific problems with each element
2. **Context Building**: Creates detailed prompts with URL context and guidelines
3. **API Optimization**: Generates improved versions using DeepSeek
4. **Validation**: Ensures optimized versions meet length constraints
5. **Fallback Handling**: Applies reliable fallbacks for problematic responses

## Use Cases
- **Site-wide SEO Audits**: Analyze entire website SEO performance
- **Content Migration**: Optimize SEO during site rebuilds or migrations
- **Competitive Analysis**: Compare and improve against competitor SEO
- **Quality Assurance**: Ensure new content meets SEO guidelines
- **Bulk Optimization**: Efficiently improve hundreds of pages at once

## Cost Management
- Only optimizes pages with significant issues
- Configurable row limits for testing
- Test mode for development without API costs
- Checkpoint system prevents duplicate API calls

## Special Handling
- **Homepage Detection**: Special optimization rules for root URLs
- **Length Constraints**: Strict validation prevents guideline violations
- **Brand Integration**: Smart brand name inclusion based on context
- **Keyword Extraction**: Automatic keyword detection from URLs
- **Error Recovery**: Graceful handling of API failures or malformed responses

## Best Practices
- Test with a small sample first using `--limit 50`
- Use `--skip-api` for initial testing and validation
- Review significant issues before running full optimization
- Monitor API usage and costs during large batch operations
- Keep checkpoint files for resuming long-running analyses