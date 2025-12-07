#!/usr/bin/env python3

import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.scraper import ContentScraper
from src.gpt_analyzer import GPTAnalyzer
from src.utils import save_report

def main():
    parser = argparse.ArgumentParser(description='SEO Content Optimizer')
    parser.add_argument('--api-key', help='OpenAI API key')
    parser.add_argument('--target-url', help='Target URL to analyze')
    parser.add_argument('--competitor-url', help='Competitor URL')
    parser.add_argument('--featured-snippet', action='store_true', help='SERP has featured snippet')
    parser.add_argument('--paa', action='store_true', help='SERP has People Also Ask')
    parser.add_argument('--brand-present', action='store_true', help='Brand present in SERP')
    args = parser.parse_args()

    load_dotenv()
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        print('Error: OpenAI API key required (--api-key)')
        return

    target_url = args.target_url or input('Enter the target URL: ').strip()
    if not target_url:
        print('Error: Target URL is required.')
        return

    competitor_url = args.competitor_url or input('Enter the competitor URL: ').strip()
    if not competitor_url:
        print('Error: Competitor URL is required.')
        return

    featured_snippets = 'yes' if args.featured_snippet else 'no'
    paa = 'yes' if args.paa else 'no'
    brand_presence = 'yes' if args.brand_present else 'no'

    serp_features = {
        "featured_snippets": "Yes" if featured_snippets == 'yes' else 'No',
        "people_also_ask": "Yes" if paa == 'yes' else 'No',
        "brand_presence": "Yes" if brand_presence == 'yes' else 'No'
    }

    # Run the analysis
    scraper = ContentScraper()
    gpt_analyzer = GPTAnalyzer()

    print("\nScraping target URL...")
    target_content = scraper.analyze_url(target_url)
    print("Scraping competitor URL...")
    competitor_content = scraper.analyze_url(competitor_url)
    print("Analyzing content with GPT...")
    recommendations = gpt_analyzer.analyze_content(
        target_content,
        [competitor_content],
        serp_features
    )

    # Save the report
    report_data = {
        "target_url": target_url,
        "competitor_urls": [competitor_url],
        "serp_features": serp_features,
        "content_analysis": target_content,
        "recommendations": recommendations
    }
    save_report(report_data, target_url)
    print("\nReport saved successfully!")

if __name__ == '__main__':
    main() 
