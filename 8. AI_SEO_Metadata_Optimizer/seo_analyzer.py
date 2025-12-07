import pandas as pd
import requests
import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np

# DeepSeek API configuration
DEEPSEEK_API_KEY = "your_api_key_here"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # Replace with actual endpoint

# SEO Guidelines
SEO_GUIDELINES = {
    "title": {
        "max_length": 60,
        "min_optimal_length": 45,  # Changed from 30 to 45
        "keyword_position": "first 30 characters",
        "brand_inclusion": "only if under 45 chars and fits naturally",  # Updated
        "special_chars": "hyphens, commas, ampersands only",
        "ending": "complete word/thought"
    },
    "description": {
        "max_length": 160,
        "min_optimal_length": 140,  # Changed from 80 to 140
        "secondary_keywords": "1-2 synonyms or related terms",
        "value_prop": "must contain clear value proposition",
        "cta": "only when relevant and not repetitive",  # Updated
        "duplication": "avoid duplicate phrases from title"
    },
    "h1": {
        "max_length": 55,  # Changed from 50 to 55
        "focus": "keyword-focused version of title",
        "brand": "not required unless it's the keyword",
        "intent": "directly addresses user intent"
    },
    "url": {
        "structure": "keep existing if possible",
        "terms": "2-5 terms maximum in slug",
        "format": "hyphen-separated keywords only",
        "words": "remove articles and prepositions"
    }
}

# Predefined fallback titles for specific cases
FALLBACK_TITLES = {
    "homepage": "Professional Business Software",
    "presentation": "Create Professional Content Online",
    "templates": "Professional Templates for Business",
    "sales": "Sales Tools Software",
    "marketing": "Marketing Tools Software",
}

class SEOAnalyzer:
    def __init__(self, spreadsheet_path: str):
        self.spreadsheet_path = spreadsheet_path
        self.data = None
        self.results = []

    def load_data(self) -> None:
        """Load the SEO data from the spreadsheet (Excel or CSV)."""
        try:
            # Check if the file is CSV or Excel based on extension
            if self.spreadsheet_path.lower().endswith('.csv'):
                self.data = pd.read_csv(self.spreadsheet_path)
                print(f"Loaded {len(self.data)} rows from CSV file: {self.spreadsheet_path}")
            else:
                self.data = pd.read_excel(self.spreadsheet_path)
                print(f"Loaded {len(self.data)} rows from Excel file: {self.spreadsheet_path}")
            
            # Replace NaN values with empty strings for text columns
            text_columns = ['URL', 'Title', 'H1', 'Description']
            for col in text_columns:
                if col in self.data.columns:
                    self.data[col] = self.data[col].fillna('').astype(str)
                    
        except Exception as e:
            print(f"Error loading data file: {e}")
            raise

    def analyze_all_urls(self, resume=False) -> None:
        """Analyze all URLs with checkpoint capability."""
        if self.data is None:
            raise ValueError("Data not loaded. Call load_data() first.")
    
        # Checkpoint file path
        checkpoint_file = "seo_analyzer_checkpoint.json"
        processed_urls = set()
    
        # Check if resuming from checkpoint
        if resume and os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                    self.results = checkpoint_data.get('results', [])
                    processed_urls = set(checkpoint_data.get('processed_urls', []))
                    print(f"Resuming from checkpoint: {len(processed_urls)} URLs already processed")
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
                print("Starting fresh...")
        else:
            # Remove old checkpoint if not resuming
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
                print("Starting fresh (removed old checkpoint)")
    
        # Real-time CSV output
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.incremental_output = f"incremental_results_{timestamp}.csv"
    
        # Write header row for CSV
        csv_fields = ['URL', 'Original Title', 'Original H1', 'Original Description', 
                    'Needs Improvement', 'Significant Issues', 'Issue Count',
                    'Optimized Title', 'Optimized H1', 'Optimized Description', 
                    'Optimization Reasoning', 'Issues']
    
        with open(self.incremental_output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(csv_fields)
        
        # Process all URLs
        total_urls = len(self.data)
        for index, row in self.data.iterrows():
            url = row.get('URL', '')
            
            # Skip empty rows
            if not url or url.lower() == 'nan' or url.strip() == '':
                print(f"Skipping row {index + 1}/{total_urls} - empty URL")
                continue
            
            # Skip already processed URLs
            if url in processed_urls:
                print(f"Skipping already processed URL {index + 1}/{total_urls}: {url}")
                continue
                
            print(f"Analyzing URL {index + 1}/{total_urls}: {url}")
            
            # Extract relevant SEO data (handle missing columns gracefully)
            # Convert all values to strings and handle NaN/None values
            title = str(row.get('Title', '')) if 'Title' in row and not pd.isna(row['Title']) else ''
            h1 = str(row.get('H1', '')) if 'H1' in row and not pd.isna(row['H1']) else ''
            description = str(row.get('Description', '')) if 'Description' in row and not pd.isna(row['Description']) else ''
            
            # Replace 'nan' string that might come from pandas
            title = '' if title.lower() == 'nan' else title
            h1 = '' if h1.lower() == 'nan' else h1
            description = '' if description.lower() == 'nan' else description
                
            # Analyze the current SEO elements
            analysis_result = self.analyze_seo_elements(url, title, h1, description)
            
            # Log summary of issues found
            if analysis_result['needs_improvement']:
                print(f"  Found {len(analysis_result['issues'])} issues")
                # Log up to 3 issues as a preview
                for issue in analysis_result['issues'][:3]:
                    print(f"  - {issue}")
                if len(analysis_result['issues']) > 3:
                    print(f"  - ... and {len(analysis_result['issues']) - 3} more issues")
            else:
                print("  No issues found - SEO elements are optimal")
            
            # Determine if there are significant issues that warrant optimization
            significant_issues = self.has_significant_issues(analysis_result, title, h1, description)
            
            # Special case for very short titles
            if title and len(title) < 40:
                # For homepage or very short titles, always consider it a significant issue
                significant_issues = True
            
            # If significant improvements needed, generate optimized versions using DeepSeek
            optimized_elements = None
            if analysis_result['needs_improvement'] and significant_issues:
                print("  Generating optimized versions with DeepSeek...")
                optimized_elements = self.generate_optimized_versions(
                    url, title, h1, description, analysis_result['issues']
                )
                
                # Check if homepage or very short title didn't get optimized properly
                is_homepage = "/" not in url.replace("://", "").split("/", 1)[1] if "://" in url else True
                
                # Handle homepage or short title fallback
                if optimized_elements and 'title' in optimized_elements:
                    title_needed_fix = False
                    
                    # Check if title is the same as original (API didn't change it)
                    if optimized_elements['title'] == title and len(title) < 40:
                        title_needed_fix = True
                    
                    # Check if title exceeds length limit
                    if len(optimized_elements['title']) > SEO_GUIDELINES['title']['max_length']:
                        title_needed_fix = True
                    
                    # Check for problematic ending
                    if isinstance(optimized_elements['title'], str) and (optimized_elements['title'].endswith(" Www") or optimized_elements['title'].endswith(" Com")):
                        title_needed_fix = True
                        
                    # Apply fallback if needed
                    if title_needed_fix:
                        # Create a fallback optimized title
                        fallback_title = self._get_fallback_title(url, title, is_homepage)
                        
                        # Use the new title
                        optimized_elements['title'] = fallback_title
                        
                        # Ensure reasoning is a string
                        if 'reasoning' in optimized_elements:
                            if isinstance(optimized_elements['reasoning'], str):
                                optimized_elements['reasoning'] += " [Title replaced with fallback due to optimization issues]"
                            else:
                                optimized_elements['reasoning'] = str(optimized_elements['reasoning']) + " [Title replaced with fallback due to optimization issues]"
                        else:
                            optimized_elements['reasoning'] = "Title replaced with fallback due to optimization issues"
                
                print("  Optimization complete")
            elif analysis_result['needs_improvement'] and not significant_issues:
                print("  Issues detected are minor - skipping optimization")
            
            # Store the results
            result_entry = {
                'url': url,
                'original': {
                    'title': title,
                    'h1': h1,
                    'description': description
                },
                'analysis': {
                    'needs_improvement': analysis_result['needs_improvement'],
                    'significant_issues': significant_issues,
                    'issues': analysis_result['issues'],
                    'element_issues': analysis_result['element_issues']
                }
            }
            
            if optimized_elements:
                result_entry['optimized'] = optimized_elements
            
            self.results.append(result_entry)
            
            # Update processed URLs and save checkpoint
            processed_urls.add(url)
            
            # Save checkpoint after each URL
            try:
                with open(checkpoint_file, 'w') as f:
                    json.dump({
                        'results': self.results,
                        'processed_urls': list(processed_urls)
                    }, f)
            except Exception as e:
                print(f"Warning: Could not save checkpoint: {e}")
            
            # Write to real-time CSV
            result_row = {
                'URL': url,
                'Original Title': title,
                'Original H1': h1,
                'Original Description': description,
                'Needs Improvement': analysis_result['needs_improvement'],
                'Significant Issues': significant_issues,
                'Issue Count': len(analysis_result['issues']),
                'Issues': '; '.join(analysis_result['issues'])
            }
            
            if optimized_elements:
                result_row.update({
                    'Optimized Title': optimized_elements.get('title', 'N/A'),
                    'Optimized H1': optimized_elements.get('h1', 'N/A'),
                    'Optimized Description': optimized_elements.get('description', 'N/A'),
                    'Optimization Reasoning': optimized_elements.get('reasoning', 'N/A')
                })
            else:
                result_row.update({
                    'Optimized Title': 'N/A',
                    'Optimized H1': 'N/A',
                    'Optimized Description': 'N/A',
                    'Optimization Reasoning': 'Not optimized'
                })
            
            with open(self.incremental_output, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=csv_fields)
                writer.writerow(result_row)
                
            # Optional: add a small delay between API calls if processing many URLs
            # to avoid hitting rate limits
            if analysis_result['needs_improvement'] and significant_issues and index < total_urls - 1:
                import time
                time.sleep(1)  # 1 second delay

    def _get_fallback_title(self, url: str, original_title: str, is_homepage: bool) -> str:
        """Generate a reliable fallback title that meets SEO guidelines."""
        # If this is the homepage, use the homepage fallback title
        if is_homepage:
            return FALLBACK_TITLES["homepage"]
        
        # Otherwise, try to extract keywords from the URL path
        path_parts = url.split('/')
        last_part = path_parts[-1] if len(path_parts) > 2 else ""
        
        # Remove any query parameters
        if '?' in last_part:
            last_part = last_part.split('?')[0]
            
        # Convert hyphens to spaces and capitalize
        keywords = last_part.replace('-', ' ').title() if last_part else ""
        
        # Check if any predefined fallback applies
        for key, fallback in FALLBACK_TITLES.items():
            if key in url.lower():
                return fallback
        
        # If we have keywords, create a custom title
        if keywords:
            # Ensure it's not too long
            if len(keywords) > 30:
                keywords = ' '.join(keywords.split()[:3])

            return f"{keywords} | Business Software"

        # Default fallback for any other case
        return "Professional Business Software"

    def has_significant_issues(self, analysis_result, title, h1, description) -> bool:
        """
        Determine if the issues found are significant enough to warrant optimization.
        Minor issues like missing brand name or call to action don't justify an API call.
        """
        # If no issues, return False
        if not analysis_result['needs_improvement']:
            return False
        
        # Check each issue to see if it's significant
        for issue in analysis_result['issues']:
            issue_lower = issue.lower()
            
            # Ignored minor issues
            minor_issues = [
                "no clear call to action"
            ]
            
            # Check if issue is a minor one
            is_minor = any(minor in issue_lower for minor in minor_issues)
            
            # Short title/description is only a minor issue if it's close to optimal length
            if "is too short" in issue_lower:
                if issue.startswith("Title:") and len(title) >= SEO_GUIDELINES['title']['min_optimal_length']:
                    is_minor = True
                elif issue.startswith("Description:") and len(description) >= SEO_GUIDELINES['description']['min_optimal_length']:
                    is_minor = True
            
            # If we found any significant issue, return True
            if not is_minor:
                return True
        
        # If all issues were minor, return False
        return False

    def analyze_seo_elements(self, url: str, title: str, h1: str, description: str) -> Dict:
        """
        Analyze SEO elements against guidelines.
        Returns a dict with analysis results and issues found.
        """
        issues = []
        element_issues = {
            'title': [],
            'h1': [],
            'description': [],
            'url': []
        }
        
        # Extract main keyword from URL for comparison
        url_path = url.split('/')[-1] if '/' in url else url
        url_keywords = [term for term in url_path.split('-') if term.strip()]
        main_keyword = url_keywords[0] if url_keywords else ""
        
        # ----- Title Analysis -----
        # Check title length
        if not title:
            element_issues['title'].append("Title is missing")
        elif len(title) > SEO_GUIDELINES['title']['max_length']:
            element_issues['title'].append(f"Title exceeds {SEO_GUIDELINES['title']['max_length']} characters ({len(title)})")
        elif len(title) < 45:  # Changed from 30 to 45
            element_issues['title'].append(f"Title is too short ({len(title)} characters)")
        
        # Check for keyword in title
        if main_keyword and title and main_keyword.lower() not in title.lower():
            element_issues['title'].append(f"Main keyword '{main_keyword}' not found in title")
        
        # Check for keyword position in title
        if main_keyword and title and main_keyword.lower() in title.lower():
            if title.lower().find(main_keyword.lower()) > 30:
                element_issues['title'].append(f"Main keyword appears too late in title (after char 30)")
        

        
        # ----- Description Analysis -----
        # Check description length
        if not description:
            element_issues['description'].append("Description is missing")
        elif len(description) > SEO_GUIDELINES['description']['max_length']:
            element_issues['description'].append(f"Description exceeds {SEO_GUIDELINES['description']['max_length']} characters ({len(description)})")
        elif len(description) < 140:  # Changed from 80 to 140
            element_issues['description'].append(f"Description is too short ({len(description)} characters)")
        
        # Check for keyword in description
        if main_keyword and description and main_keyword.lower() not in description.lower():
            element_issues['description'].append(f"Main keyword '{main_keyword}' not found in description")
        
        # Check for call to action - only if description is long enough to have room for it
        if description and len(description) < 140:  # Only check CTA for shorter descriptions
            cta_phrases = ["try", "get", "learn", "discover", "start", "see", "find", "explore"]
            has_cta = any(phrase in description.lower() for phrase in cta_phrases)
            if not has_cta:
                element_issues['description'].append("No clear call to action in description")
        
        # ----- H1 Analysis -----
        # Check H1 length
        if not h1:
            element_issues['h1'].append("H1 is missing")
        elif len(h1) > SEO_GUIDELINES['h1']['max_length']:
            element_issues['h1'].append(f"H1 exceeds {SEO_GUIDELINES['h1']['max_length']} characters ({len(h1)})")
        
        # Check for keyword in H1
        if main_keyword and h1 and main_keyword.lower() not in h1.lower():
            element_issues['h1'].append(f"Main keyword '{main_keyword}' not found in H1")
        
        # ----- URL Analysis -----
        # Check URL format
        if len(url_keywords) > 5:
            element_issues['url'].append(f"URL contains too many terms ({len(url_keywords)}, max 5)")
        
        # Check for filler words in URL
        filler_words = ["a", "an", "the", "in", "on", "at", "for", "to", "with", "by", "of"]
        has_fillers = any(word in filler_words for word in url_keywords)
        if has_fillers:
            element_issues['url'].append("URL contains filler words (articles or prepositions)")
            
        # ----- Cross-element Analysis -----
        # Check for title with fluff while being identical to H1
        title_contains_brand = False
        title_contains_separator = "|" in title or "-" in title or ":" in title
        
        # FIXED: Only flag as issue if title has fluff elements but is identical to H1
        if title and h1 and title == h1 and (title_contains_brand or title_contains_separator):
            issues.append("H1 is identical to title but should be more focused (without brand name/separators)")
        
        # Check for title in description
        if title and description and title.lower() in description.lower():
            issues.append("Title is fully contained in description - redundant")
        
        # Combine all element-specific issues into the main issues list
        for element, element_issue_list in element_issues.items():
            if element_issue_list:
                issues.extend([f"{element.capitalize()}: {issue}" for issue in element_issue_list])
        
        # Determine if any elements need improvement
        needs_improvement = {
            'title': len(element_issues['title']) > 0,
            'h1': len(element_issues['h1']) > 0,
            'description': len(element_issues['description']) > 0,
            'url': len(element_issues['url']) > 0,
            'any': len(issues) > 0
        }
        
        return {
            'needs_improvement': needs_improvement['any'],
            'element_needs_improvement': needs_improvement,
            'issues': issues,
            'element_issues': element_issues
        }

    def generate_optimized_versions(self, url: str, title: str, h1: str, description: str, issues: List[str]) -> Dict:
        """
        Generate optimized versions of SEO elements using DeepSeek API.
        Returns a dict with optimized elements.
        """
        # Craft prompt for DeepSeek
        prompt = self._create_deepseek_prompt(url, title, h1, description, issues)
        
        # Call DeepSeek API
        optimized = self._call_deepseek_api(prompt)
        
        # Verify that optimized versions don't exceed max lengths
        optimized = self._validate_optimized_elements(optimized, title, h1, description)
        
        return optimized

    def _validate_optimized_elements(self, optimized: Dict, original_title: str, original_h1: str, original_description: str) -> Dict:
        """
        Validate that optimized elements follow our guidelines, especially length constraints.
        If not, fall back to original values or truncate.
        """
        # Ensure the reasoning field is a string
        if 'reasoning' in optimized:
            if not isinstance(optimized['reasoning'], str):
                optimized['reasoning'] = str(optimized['reasoning'])
        else:
            optimized['reasoning'] = ""
        # Check title length
        if 'title' in optimized and len(optimized.get('title', '')) > SEO_GUIDELINES['title']['max_length']:
            print(f"  Warning: Optimized title exceeds max length ({len(optimized['title'])} chars)")
            # Fall back to original if it's within limits, otherwise truncate
            if len(original_title) <= SEO_GUIDELINES['title']['max_length']:
                optimized['title'] = original_title
                optimized['reasoning'] += " [Original title used due to length constraints]"
            else:
                # Try to find a good truncation point (after a word)
                truncated = optimized['title'][:SEO_GUIDELINES['title']['max_length']]
                # Find last space to avoid cutting words
                last_space = truncated.rfind(' ')
                if last_space > 0:
                    truncated = truncated[:last_space]
                optimized['title'] = truncated
                optimized['reasoning'] += " [Optimized title truncated to fit length constraints]"
        
        # Check H1 length
        if 'h1' in optimized and len(optimized.get('h1', '')) > SEO_GUIDELINES['h1']['max_length']:
            print(f"  Warning: Optimized H1 exceeds max length ({len(optimized['h1'])} chars)")
            # Fall back to original if it's within limits, otherwise truncate
            if len(original_h1) <= SEO_GUIDELINES['h1']['max_length']:
                optimized['h1'] = original_h1
                optimized['reasoning'] += " [Original H1 used due to length constraints]"
            else:
                # Try to find a good truncation point (after a word)
                truncated = optimized['h1'][:SEO_GUIDELINES['h1']['max_length']]
                # Find last space to avoid cutting words
                last_space = truncated.rfind(' ')
                if last_space > 0:
                    truncated = truncated[:last_space]
                optimized['h1'] = truncated
                optimized['reasoning'] += " [Optimized H1 truncated to fit length constraints]"
        
        # Check description length
        if 'description' in optimized and len(optimized.get('description', '')) > SEO_GUIDELINES['description']['max_length']:
            print(f"  Warning: Optimized description exceeds max length ({len(optimized['description'])} chars)")
            # Fall back to original if it's within limits, otherwise truncate
            if len(original_description) <= SEO_GUIDELINES['description']['max_length']:
                optimized['description'] = original_description
                optimized['reasoning'] += " [Original description used due to length constraints]"
            else:
                # Try to find a good truncation point (after a sentence or punctuation)
                truncated = optimized['description'][:SEO_GUIDELINES['description']['max_length']]
                # Find last sentence end to avoid cutting sentences
                for punct in ['. ', '! ', '? ']:
                    last_punct = truncated.rfind(punct)
                    if last_punct > 0:
                        truncated = truncated[:last_punct+1]  # Include the punctuation
                        break
                # If no sentence end found, try to find last space
                if truncated == optimized['description'][:SEO_GUIDELINES['description']['max_length']]:
                    last_space = truncated.rfind(' ')
                    if last_space > 0:
                        truncated = truncated[:last_space]
                optimized['description'] = truncated
                optimized['reasoning'] += " [Optimized description truncated to fit length constraints]"
        
        return optimized

    def _create_deepseek_prompt(self, url: str, title: str, h1: str, description: str, issues: List[str]) -> str:
        """Create a detailed prompt for DeepSeek API to optimize SEO elements."""
        # Extract the main topic/keyword from URL for reference
        url_path = url.split('/')[-1] if '/' in url else url
        url_keywords = url_path.split('-')
        main_keyword = url_keywords[0] if url_keywords else ""
        
        # Check if this is a homepage (root URL)
        is_homepage = "/" not in url.replace("://", "").split("/", 1)[1] if "://" in url else True
        
        # Group issues by element type
        title_issues = [issue for issue in issues if issue.startswith("Title:")]
        h1_issues = [issue for issue in issues if issue.startswith("H1:")]
        description_issues = [issue for issue in issues if issue.startswith("Description:")]
        url_issues = [issue for issue in issues if issue.startswith("URL:")]
        other_issues = [issue for issue in issues if not (issue.startswith(("Title:", "H1:", "Description:", "URL:")))]
        
        # Determine which elements need optimization
        optimize_title = len(title_issues) > 0
        optimize_h1 = len(h1_issues) > 0
        optimize_description = len(description_issues) > 0
        optimize_url = len(url_issues) > 0
        
        # Special case for short title
        very_short_title = title and len(title) < 40
        
        prompt = f"""
        As an SEO optimization expert, I need to improve the following webpage elements:

        URL: {url}
        Current Title: {title} (Length: {len(title)})
        Current H1: {h1} (Length: {len(h1)})
        Current Description: {description} (Length: {len(description)})

        Main topic/keyword identified: {main_keyword}
        Is homepage: {"Yes" if is_homepage else "No"}

        Elements needing optimization:
        - Title: {"YES" if optimize_title else "No"}
        - H1: {"YES" if optimize_h1 else "No"}
        - Description: {"YES" if optimize_description else "No"}
        - URL: {"YES" if optimize_url else "No"}
        """
        
        # Add special instructions for homepage or very short titles
        if is_homepage or very_short_title:
            prompt += f"""
            SPECIAL CASE - {"HOMEPAGE" if is_homepage else "VERY SHORT TITLE"}:
            This is a {"homepage" if is_homepage else "page with a very short title"} which requires special attention:
            - Title MUST be simple and straightforward
            - Do NOT include more than one | symbol in the title
            - NEVER include "www" or ".com" or any domain parts in the title
            - Keep titles strictly under 60 characters
            - Must emphasize the company's main offering
            - Should include the brand name at the end if appropriate
            - MUST REPLACE the current title with a completely new optimized version
            """
        
        prompt += "\nSPECIFIC ISSUES:"
        
        if title_issues:
            prompt += "\nTitle issues:\n" + "\n".join([f"- {issue.replace('Title: ', '')}" for issue in title_issues])
        
        if h1_issues:
            prompt += "\nH1 issues:\n" + "\n".join([f"- {issue.replace('H1: ', '')}" for issue in h1_issues])
        
        if description_issues:
            prompt += "\nDescription issues:\n" + "\n".join([f"- {issue.replace('Description: ', '')}" for issue in description_issues])
        
        if url_issues:
            prompt += "\nURL issues:\n" + "\n".join([f"- {issue.replace('URL: ', '')}" for issue in url_issues])
        
        if other_issues:
            prompt += "\nCross-element issues:\n" + "\n".join([f"- {issue}" for issue in other_issues])
        
        prompt += f"""

        SEO GUIDELINES:
        - Title: Max {SEO_GUIDELINES['title']['max_length']} chars, primary keyword in first 30 chars, include brand name only if room permits
        - H1: Max {SEO_GUIDELINES['h1']['max_length']} chars, keyword-focused version of title, directly addresses user intent
        - Description: Max {SEO_GUIDELINES['description']['max_length']} chars, include 1-2 secondary keywords, clear value proposition
        - URL: 2-5 hyphen-separated keywords, no articles or prepositions, directly relevant to user intent

        CRITICAL RULES:
        1. NEVER exceed max character limits - Title must be 60 characters or less!
        2. Do NOT use more than one pipe (|) symbol in titles
        3. NEVER EVER include "www", "com", domain names, or TLDs in titles
        4. For homepage titles, use simple format like "Primary Keyword | Brand Name"
        5. Only add brand name if it fits naturally, typically at the end
        6. Only include CTA in description if it fits the context naturally
        7. Prioritize keyword optimization over brand inclusion or CTA
        8. If the original is already good and close to max length, make minimal changes
        9. Don't force the brand name if it makes content unnatural or too long
        10. Ensure the optimized version is better than the original by focusing on proper keyword usage
        11. YOU MUST PROVIDE COMPLETELY NEW VALUES FOR EACH ELEMENT that needs optimization - DO NOT RETURN THE SAME TEXT AS THE ORIGINAL
        12. If Title is too short (under 40 chars), you MUST create a completely new title that:
           - Includes relevant keywords from the URL or content
           - Has a length between 45-55 characters (not longer!)
           - Includes the brand name appropriately
           - Is significantly different from the original title

        Respond in THIS EXACT JSON format:
        {{
            "title": "optimized title here - MUST BE DIFFERENT from original if optimization is needed",
            "h1": "optimized h1 here - MUST BE DIFFERENT from original if optimization is needed",
            "description": "optimized description here - MUST BE DIFFERENT from original if optimization is needed",
            "url": "UNCHANGED or optimized-url-slug-here",
            "reasoning": "brief explanation of improvements made to each element"
        }}
        """
        return prompt

    def _call_deepseek_api(self, prompt: str) -> Dict:
        """
        Call DeepSeek API with the given prompt.
        Returns parsed response with optimized SEO elements.
        """
        if DEEPSEEK_API_KEY == "your_api_key_here":
            print("Warning: Using placeholder API response. Set your actual API key.")
            # Placeholder response for testing
            return {
                "title": "Optimized title would be returned here",
                "h1": "Optimized H1 would be returned here",
                "description": "Optimized description would be returned here",
                "url": "UNCHANGED",
                "reasoning": "Explanation of improvements would be here"
            }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        payload = {
            "model": "deepseek-chat",  # Update with appropriate model name
            "messages": [
                {"role": "system", "content": "You are an SEO optimization expert specialized in creating optimized webpage titles, descriptions, and headers."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Lower temperature for more consistent results
            "max_tokens": 500
        }
        
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            
            result = response.json()
            
            # Extract the generated content from DeepSeek response
            # The exact path will depend on DeepSeek's API response structure
            # This is an example - adjust based on actual API response format
            ai_message = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse the JSON from the response
            try:
                # Find JSON in the response (in case there's any additional text)
                import re
                json_match = re.search(r'{.*}', ai_message, re.DOTALL)
                if json_match:
                    ai_message = json_match.group(0)
                
                optimized_data = json.loads(ai_message)
                
                # Ensure all expected fields are present
                required_fields = ["title", "h1", "description", "url", "reasoning"]
                for field in required_fields:
                    if field not in optimized_data:
                        optimized_data[field] = "NOT PROVIDED"
                
                return optimized_data
                
            except json.JSONDecodeError:
                print(f"Error parsing JSON from DeepSeek response: {ai_message[:200]}...")
                return {
                    "title": "ERROR: Could not parse response",
                    "h1": "ERROR: Could not parse response",
                    "description": "ERROR: Could not parse response",
                    "url": "UNCHANGED",
                    "reasoning": f"API response was not in expected format: {ai_message[:100]}..."
                }
                
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {
                "title": "ERROR: API request failed",
                "h1": "ERROR: API request failed",
                "description": "ERROR: API request failed",
                "url": "UNCHANGED",
                "reasoning": f"API request failed: {str(e)}"
            }

    def save_results(self, output_path: str) -> None:
        """Save the analysis results to a CSV file with detailed information."""
        if not self.results:
            print("No results to save.")
            return
        
        # Convert results to DataFrame
        results_rows = []
        for result in self.results:
            # Basic row with original data and analysis results
            row = {
                'URL': result['url'],
                'Original Title': result['original']['title'],
                'Original H1': result['original']['h1'],
                'Original Description': result['original']['description'],
                'Needs Improvement': result['analysis']['needs_improvement'],
                'Significant Issues': result['analysis'].get('significant_issues', False),
                'Issue Count': len(result['analysis']['issues']),
                'Issues': '; '.join(result['analysis']['issues'])  # Use semicolons for CSV
            }
            
            # Add optimized versions if available
            if 'optimized' in result:
                optimized = result['optimized']
                row.update({
                    'Optimized Title': optimized.get('title', 'N/A'),
                    'Optimized H1': optimized.get('h1', 'N/A'),
                    'Optimized Description': optimized.get('description', 'N/A'),
                    'Optimized URL': optimized.get('url', 'UNCHANGED'),
                    'Optimization Reasoning': optimized.get('reasoning', 'N/A')
                })
            else:
                # If significant issues but no optimization (e.g., API error)
                if result['analysis'].get('significant_issues', False):
                    status = "Error or Skipped"
                # If needs improvement but not significant
                elif result['analysis']['needs_improvement']:
                    status = "Minor Issues Only - No Optimization Needed"
                # If no issues
                else:
                    status = "No Issues - Already Optimal"
                
                # Add empty columns for consistency
                row.update({
                    'Optimized Title': 'N/A',
                    'Optimized H1': 'N/A',
                    'Optimized Description': 'N/A',
                    'Optimized URL': 'N/A',
                    'Optimization Reasoning': status
                })
            
            # Add specific issue counts by element
            if 'element_issues' in result['analysis']:
                element_issues = result['analysis']['element_issues']
                row.update({
                    'Title Issues': len(element_issues['title']),
                    'H1 Issues': len(element_issues['h1']),
                    'Description Issues': len(element_issues['description']),
                    'URL Issues': len(element_issues['url'])
                })
            
            results_rows.append(row)
        
        # Create DataFrame and save to CSV
        results_df = pd.DataFrame(results_rows)
        
        # Reorder columns for better readability
        column_order = [
            'URL', 'Needs Improvement', 'Significant Issues', 'Issue Count',
            'Original Title', 'Title Issues', 'Optimized Title',
            'Original H1', 'H1 Issues', 'Optimized H1',
            'Original Description', 'Description Issues', 'Optimized Description',
            'URL Issues', 'Optimized URL',
            'Optimization Reasoning', 'Issues'
        ]
        
        # Only include columns that actually exist in the DataFrame
        ordered_columns = [col for col in column_order if col in results_df.columns]
        
        # Add any columns that weren't in our ordered list
        for col in results_df.columns:
            if col not in ordered_columns:
                ordered_columns.append(col)
        
        # Reorder and save
        results_df = results_df[ordered_columns]
        
        # Save as CSV 
        results_df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")
        
        # Print summary statistics
        total_analyzed = len(results_df)
        total_needing_improvement = sum(1 for x in results_df['Needs Improvement'] if x)
        total_significant_issues = sum(1 for x in results_df['Significant Issues'] if x)
        
        improvement_percentage = (total_needing_improvement / total_analyzed * 100) if total_analyzed > 0 else 0
        significant_percentage = (total_significant_issues / total_analyzed * 100) if total_analyzed > 0 else 0
        
        print(f"\nAnalysis Summary:")
        print(f"  Total URLs analyzed: {total_analyzed}")
        print(f"  URLs needing improvement: {total_needing_improvement} ({improvement_percentage:.1f}%)")
        print(f"  URLs with significant issues: {total_significant_issues} ({significant_percentage:.1f}%)")
        
        # Element-specific statistics if available
        if 'Title Issues' in results_df.columns:
            title_issues = sum(1 for x in results_df['Title Issues'] if x > 0)
            h1_issues = sum(1 for x in results_df['H1 Issues'] if x > 0)
            desc_issues = sum(1 for x in results_df['Description Issues'] if x > 0)
            url_issues = sum(1 for x in results_df['URL Issues'] if x > 0)
            
            print(f"  URLs with title issues: {title_issues} ({title_issues/total_analyzed*100:.1f}%)")
            print(f"  URLs with H1 issues: {h1_issues} ({h1_issues/total_analyzed*100:.1f}%)")
            print(f"  URLs with description issues: {desc_issues} ({desc_issues/total_analyzed*100:.1f}%)")
            print(f"  URLs with URL issues: {url_issues} ({url_issues/total_analyzed*100:.1f}%)")
                

def generate_sample_data(output_path="sample_seo_data.csv"):
    """Generate a sample CSV with SEO data for testing."""
    import pandas as pd
    import os
    
    print(f"Generating sample SEO data CSV at {output_path}...")
    
    # Sample SEO data with various issues
    sample_data = [
        {
            "URL": "https://example.com/features/presentation-software",
            "Title": "Best Presentation Software for Business | YourBrand",
            "H1": "Best Presentation Software for Business | YourBrand",
            "Description": "Create stunning presentations with YourBrand's presentation software. Free templates, easy to use, perfect for sales and marketing teams."
        },
        {
            "URL": "https://example.com/templates/sales-deck",
            "Title": "Sales Deck Templates - Create Winning Presentations Fast",
            "H1": "Sales Deck Templates",
            "Description": "Our sales deck templates help you close more deals. Choose from 50+ professionally designed templates."
        },
        {
            "URL": "https://example.com/blog/powerpoint-alternatives",
            "Title": "Top 15 PowerPoint Alternatives in 2025 - Complete Guide",
            "H1": "PowerPoint Alternatives: The Ultimate List",
            "Description": "Looking for PowerPoint alternatives? We've compiled the 15 best options for creating professional presentations in 2025. Compare features, pricing, and more!"
        },
        {
            "URL": "https://example.com/pricing",
            "Title": "Simple and transparent pricing for all your needs",
            "H1": "Pricing",
            "Description": "Choose the plan that works for you and your team. All plans include all features, unlimited presentations, and great support."
        },
        {
            "URL": "https://example.com/about-us",
            "Title": "About YourBrand - Our Mission and Team",
            "H1": "About Us",
            "Description": "Learn more about YourBrand and our mission to revolutionize the way businesses create and share presentations."
        },
        {
            "URL": "https://example.com/features/templates-and-designs",
            "Title": "Beautiful Presentation Templates and Designs for Every Occasion - Easily Customizable",
            "H1": "Templates & Designs",
            "Description": "Explore our library of professionally designed presentation templates. No design skills required. Just pick a template and customize it to make it your own in minutes."
        },
        {
            "URL": "https://example.com/help-center/getting-started-guide",
            "Title": "Getting Started with YourBrand - Step by Step Guide",
            "H1": "Getting Started with YourBrand",
            "Description": "New to YourBrand? This guide will walk you through everything you need to know to create your first stunning presentation."
        },
        {
            "URL": "https://example.com/blog/presentation-software-comparison",
            "Title": "Comparing the Best Presentation Software in 2025",
            "H1": "2025 Presentation Software Comparison",
            "Description": "We compare the top presentation software tools of 2025. See how YourBrand stacks up against PowerPoint, Google Slides, Prezi, and others."
        },
        {
            "URL": "https://example.com/features/analytics-and-insights",
            "Title": "Track Presentation Performance with Advanced Analytics",
            "H1": "Analytics & Insights",
            "Description": "See who viewed your presentation, how long they spent on each slide, and what content resonated most with real-time analytics and insights."
        },
        {
            "URL": "https://example.com/use-cases/sales-presentations",
            "Title": "Create Sales Presentations That Convert - YourBrand",
            "H1": "Create Sales Presentations That Convert",
            "Description": "Turn prospects into customers with high-converting sales presentations. Learn how YourBrand helps sales teams close more deals."
        },
        # Adding examples with various specific SEO issues
        {
            "URL": "https://example.com/example/too-short-title",
            "Title": "Short Title",
            "H1": "This is a properly sized H1 with good keyword usage",
            "Description": "This is a properly sized description that contains all the necessary keywords and information for users to understand what the page is about, with a clear call to action."
        },
        {
            "URL": "https://example.com/example/title-with-good-length-but-no-brand",
            "Title": "This Title Has Good Length But No YourBrand Brand Reference",
            "H1": "Title Without Brand",
            "Description": "A good description with appropriate length discussing the topic in detail with relevant keywords but missing a clear call to action element."
        },
        {
            "URL": "https://example.com/example/already-optimized-title-and-description",
            "Title": "This Title Is Already Perfectly Optimized | YourBrand (55 chars)",
            "H1": "This H1 Is Also Perfectly Sized",
            "Description": "This description is already the perfect length at about 150 characters with good keyword usage and a clear call to action to try YourBrand today!"
        },
        {
            "URL": "https://example.com/example/too-long-title-needs-fixing",
            "Title": "This Title Is Way Too Long And Exceeds The Maximum Character Count Significantly Which Will Cause SEO Issues | YourBrand Platform",
            "H1": "Too Long Title Example",
            "Description": "Good description."
        },
        {
            "URL": "https://example.com",
            "Title": "YourBrand: Present. Engage. Win.",
            "H1": "Interactive presentation software",
            "Description": "Create interactive presentations that engage your audience and drive results. Try YourBrand now to transform your static slides into interactive experiences."
        }
    ]
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(sample_data)
    df.to_csv(output_path, index=False)
    
    print(f"Sample data created successfully with {len(sample_data)} rows!")
    print(f"Run the analyzer with: python seo_analyzer.py --input {output_path}")
    
    return output_path


def run_demo():
    """Run a complete demo of the SEO analyzer with sample data."""
    import tempfile
    import os
    
    print("="*80)
    print("RUNNING SEO ANALYZER DEMO")
    print("="*80)
    
    # Create a temp directory for our files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate sample data
        sample_file = os.path.join(temp_dir, "sample_seo_data.csv")
        generate_sample_data(sample_file)
        
        # Create output file path
        output_file = os.path.join(temp_dir, "sample_seo_results.csv")
        
        # Run analysis in test mode (no API calls)
        print("\nRunning analysis in test mode (no API calls)...")
        analyzer = SEOAnalyzer(sample_file)
        analyzer.load_data()
        
        # Mock API calls
        def mock_api_call(self, prompt):
            url_in_prompt = ""
            for line in prompt.split("\n"):
                if line.strip().startswith("URL:"):
                    url_in_prompt = line.strip()[4:].strip()
                    break
            
            # Specially handle the homepage to address the issue
            if url_in_prompt == "https://example.com":
                return {
                    "title": "Interactive Presentation Software | YourBrand",
                    "h1": "Create Interactive Presentations That Drive Results",
                    "description": "Transform static slides into engaging interactive presentations that capture attention and drive results. Try YourBrand's presentation software today!",
                    "url": "UNCHANGED",
                    "reasoning": "Completely replaced the short title with a keyword-rich version that focuses on the core offering. Removed unnecessary elements and kept it simple but effective."
                }
            # Generate different responses based on URL to simulate real API behavior
            elif "too-short-title" in url_in_prompt:
                return {
                    "title": "Expanded Title with More SEO Keywords | YourBrand",
                    "h1": "Expanded H1 with Better Keyword Usage",
                    "description": "This description remains largely the same since it was already well-optimized with good length and a clear call to action.",
                    "url": "UNCHANGED",
                    "reasoning": "Significantly expanded the title to include more relevant keywords and context. H1 was also improved with better keyword usage."
                }
            else:
                return {
                    "title": "DEMO Optimized Title - More Focused and Keyword-Rich",
                    "h1": "DEMO Optimized H1 - Concise and Clear",
                    "description": "DEMO Optimized Description with better keywords and a clear call to action. Try YourBrand today!",
                    "url": "UNCHANGED",
                    "reasoning": "Made title more focused on keywords, shortened H1 for clarity, and added call-to-action to description."
                }
        
        # Replace actual API call with mock
        original_api_call = SEOAnalyzer._call_deepseek_api
        SEOAnalyzer._call_deepseek_api = mock_api_call
        
        try:
            # Run analysis
            analyzer.analyze_all_urls()
            analyzer.save_results(output_file)
            
            print("\nDemo completed successfully!")
            print("Sample data and results were created in a temporary directory.")
            
            # Copy files to current directory for easy access
            import shutil
            current_dir_sample = "demo_sample_data.csv"
            current_dir_results = "demo_results.csv"
            
            shutil.copy(sample_file, current_dir_sample)
            shutil.copy(output_file, current_dir_results)
            
            print("\nFor your convenience, files have been copied to your current directory:")
            print(f"  Sample data: {os.path.abspath(current_dir_sample)}")
            print(f"  Results: {os.path.abspath(current_dir_results)}")
            print("\nYou can use these files to experiment with the script.")
            
        finally:
            # Restore original API call method
            SEOAnalyzer._call_deepseek_api = original_api_call


def main():
    """Main entry point with command-line argument handling."""
    import argparse
    import os
    from datetime import datetime
    
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='SEO Analyzer and Optimizer')
    parser.add_argument('--input', '-i', required=True, help='Path to input file (CSV or Excel)')
    parser.add_argument('--output', '-o', help='Path to output file (defaults to CSV)')
    parser.add_argument('--api-key', '-k', help='DeepSeek API key')
    parser.add_argument('--limit', '-l', type=int, help='Limit analysis to first N rows')
    parser.add_argument('--skip-api', '-s', action='store_true', help='Skip API calls (for testing)')
    parser.add_argument('--resume', '-r', action='store_true', help='Resume from last checkpoint')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        return 1
    
    # Set API key if provided
    if args.api_key:
        global DEEPSEEK_API_KEY
        DEEPSEEK_API_KEY = args.api_key
    
    # Generate default output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_base = os.path.splitext(os.path.basename(args.input))[0]
        args.output = f"{input_base}_seo_analysis_{timestamp}.csv"  # Default to CSV output
    
    # Initialize analyzer
    print(f"Initializing SEO Analyzer...")
    analyzer = SEOAnalyzer(args.input)
    
    try:
        # Load data
        analyzer.load_data()
        
        # Apply row limit if specified
        if args.limit and args.limit > 0:
            print(f"Limiting analysis to first {args.limit} rows")
            analyzer.data = analyzer.data.head(args.limit)
        
        # Skip API calls if requested
        if args.skip_api:
            print("API calls will be skipped (test mode)")
            # Create a mock method that overrides the real API call method
            def mock_api_call(self, prompt):
                print("MOCK API CALL")
                # Special handling for very short titles
                url_in_prompt = ""
                for line in prompt.split("\n"):
                    if line.strip().startswith("URL:"):
                        url_in_prompt = line.strip()[4:].strip()
                        break
                
                # Check if we need special handling for the homepage
                is_homepage = "/" not in url_in_prompt.replace("://", "").split("/", 1)[1] if "://" in url_in_prompt else True
                
                # Check if title needs special handling based on prompt
                needs_title_fix = False
                for line in prompt.split("\n"):
                    if "Title is too short" in line or "VERY SHORT TITLE" in line:
                        needs_title_fix = True
                        break
                
                if is_homepage or needs_title_fix:
                    try:
                        domain_name = url_in_prompt.split('/')[2] if '://' in url_in_prompt else url_in_prompt.split('/')[0]
                        if domain_name.startswith('www.'):
                            domain_name = domain_name[4:]
                        brand = domain_name.split('.')[0].capitalize()
                    except (IndexError, AttributeError):
                        brand = "YourBrand"  # Default fallback

                    return {
                        "title": f"Professional Business Software | {brand}",
                        "h1": "Create Professional Solutions That Drive Results",
                        "description": "Transform your business with engaging professional solutions that capture attention and drive results. Try our software today!",
                        "url": "UNCHANGED",
                        "reasoning": "MOCK: Replaced short title with keyword-rich version focused on core offering. H1 emphasizes main value proposition."
                    }
                else:
                    return {
                        "title": "MOCK Optimized Title - Keyword Enhanced for SEO",
                        "h1": "MOCK Optimized H1 - Concise and Clear",
                        "description": "MOCK Optimized Description with enhanced keywords and clear value proposition. Includes a natural call to action.",
                        "url": "UNCHANGED",
                        "reasoning": "MOCK: This is a generic mock optimization response for testing."
                    }
            # Replace the real method with our mock
            SEOAnalyzer._call_deepseek_api = mock_api_call
        
        # Run analysis with resume option
        print(f"Starting SEO analysis of {len(analyzer.data)} URLs...")
        analyzer.analyze_all_urls(resume=args.resume)
        
        # Save complete results
        analyzer.save_results(args.output)
        
        print("\nSEO analysis complete!")
        print(f"Final results saved to: {os.path.abspath(args.output)}")
        print(f"Incremental results saved to: {os.path.abspath(analyzer.incremental_output)}")
        
        return 0
    
    except Exception as e:
        if args.debug:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        return 1
    
if __name__ == "__main__":
    import sys

    # Check if "demo" argument was passed
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo()
    else:
        exit_code = main()
        sys.exit(exit_code)
