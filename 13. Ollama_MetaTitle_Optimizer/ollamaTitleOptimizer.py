#!/usr/bin/env python3
"""
SEO Title Generator using Ollama
Processes CSV with URL, Existing Title, Top 5 Keywords to generate optimized titles
"""

import pandas as pd
import requests
import json
import sys
import time
from urllib.parse import urlparse
import re

class SEOTitleGenerator:
    def __init__(self, model_name="llama3.1:8b-instruct-q4_K_M", ollama_url="http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.session = requests.Session()
        
    def test_connection(self):
        """Test if Ollama is running and model is available"""
        try:
            response = self.session.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = [model['name'] for model in response.json()['models']]
                if self.model_name in models:
                    print(f"✓ Connected to Ollama. Using model: {self.model_name}")
                    
                    # Pre-warm the model with a simple request
                    print("Warming up model...")
                    try:
                        warm_response = self.session.post(
                            f"{self.ollama_url}/api/generate",
                            json={
                                "model": self.model_name,
                                "prompt": "Hi",
                                "stream": False,
                                "options": {"num_predict": 5}
                            },
                            timeout=60
                        )
                        if warm_response.status_code == 200:
                            print("✓ Model warmed up successfully")
                        else:
                            print("⚠ Model warm-up failed, but continuing...")
                    except:
                        print("⚠ Model warm-up timed out, but continuing...")
                    
                    return True
                else:
                    print(f"✗ Model {self.model_name} not found. Available models: {models}")
                    return False
            else:
                print(f"✗ Cannot connect to Ollama at {self.ollama_url}")
                return False
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def extract_domain_keywords(self, url):
        """Extract potential keywords from URL structure"""
        try:
            parsed = urlparse(url)
            domain_parts = parsed.netloc.replace('www.', '').split('.')
            path_parts = parsed.path.strip('/').split('/')
            
            # Clean and filter meaningful parts
            keywords = []
            for part in domain_parts + path_parts:
                if part and len(part) > 2 and part not in ['com', 'org', 'net', 'html', 'php']:
                    # Split on hyphens/underscores and camelCase
                    words = re.split(r'[-_]|(?=[A-Z])', part.lower())
                    keywords.extend([w for w in words if len(w) > 2])
            
            return list(set(keywords))[:3]  # Return top 3 unique keywords
        except:
            return []
    
    def generate_titles(self, url, existing_title, top_keywords):
        """Generate 5 SEO-optimized titles using Ollama"""
        
        # Extract additional context from URL
        url_keywords = self.extract_domain_keywords(url)
        
        prompt = f"""TASK: Write exactly 5 SEO titles. No explanations. No preambles. Just titles.

URL: {url}
Current: {existing_title}
Keywords: {top_keywords}

CRITICAL RULES:
- EXACTLY 45-60 characters each (count carefully!)
- Include main keywords
- High CTR focus
- No fluff words
- No numbering or bullets

OUTPUT FORMAT (one per line):
Title1
Title2
Title3
Title4
Title5

START:"""

        try:
            # Try with retry logic
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    response = self.session.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": self.model_name,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.3,
                                "top_p": 0.8,
                                "num_predict": 400,
                                "stop": ["\n\n", "EXPLANATION:", "Note:", "Remember:"]
                            }
                        },
                        timeout=120  # Increased timeout
                    )
                    
                    if response.status_code == 200:
                        break
                        
                except requests.exceptions.Timeout:
                    if attempt < max_retries:
                        print(f"  Timeout on attempt {attempt + 1}, retrying...")
                        time.sleep(2)
                        continue
                    else:
                        # Generate fallback titles
                        base_keywords = top_keywords.split(',')[0].strip() if top_keywords else "Tools"
                        return [
                            f"Best {base_keywords} Software for Teams in 2024",
                            f"How to Choose the Right {base_keywords} Platform",
                            f"Top 10 {base_keywords} Features You Need",
                            f"Ultimate {base_keywords} Guide for Business",
                            f"Why {base_keywords} Matters: Complete Guide"
                        ]
            
            if response.status_code == 200:
                result = response.json()['response'].strip()
                
                # Aggressive cleaning - remove any preamble text
                lines = result.split('\n')
                clean_lines = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Skip obvious preamble/explanation lines
                    skip_patterns = [
                        'here are', 'optimized title', 'meet the requi', 
                        'five title', 'options', 'webpage', 'follow',
                        'requirements', 'characters', 'seo', 'generate'
                    ]
                    
                    line_lower = line.lower()
                    if any(pattern in line_lower for pattern in skip_patterns):
                        continue
                    
                    # Remove numbering and bullets
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = re.sub(r'^[\-\*\•]\s*', '', line)
                    
                    # Try to fix length issues
                    if len(line) > 60:
                        # Truncate at word boundary
                        line = line[:57].rsplit(' ', 1)[0] + '...'
                        if len(line) < 45:
                            continue
                    elif len(line) < 45:
                        # Skip if too short and can't be easily expanded
                        continue
                    
                    # Final check
                    if len(line) < 45 or len(line) > 60:
                        continue
                    
                    # Truncate if ends with ... and try to fix
                    if line.endswith('...'):
                        line = line[:-3].strip()
                        if len(line) < 45:
                            continue
                    
                    clean_lines.append(line)
                
                # If we have good titles, pad to 5 if needed
                if len(clean_lines) >= 3:
                    # Pad with fallback titles if we don't have 5
                    while len(clean_lines) < 5:
                        base_keyword = top_keywords.split(',')[0].strip() if top_keywords else "Guide"
                        fallback = f"Complete {base_keyword} Guide for Business Success"
                        if len(fallback) >= 45 and len(fallback) <= 60:
                            clean_lines.append(fallback)
                        else:
                            clean_lines.append(f"Best {base_keyword} Solutions for 2024")
                    return clean_lines[:5]
                
                # Fallback: try to extract anything that looks like a title
                all_lines = result.split('\n')
                fallback_titles = []
                
                for line in all_lines:
                    line = line.strip()
                    if 45 <= len(line) <= 60 and not any(word in line.lower() for word in ['here are', 'title', 'option', 'webpage']):
                        line = re.sub(r'^\d+[\.\)]\s*', '', line)
                        line = re.sub(r'^[\-\*\•]\s*', '', line)
                        if line.endswith('...'):
                            line = line[:-3].strip()
                        if len(line) >= 40:
                            fallback_titles.append(line)
                
                if fallback_titles:
                    return fallback_titles[:5]
                
                # Last resort: generate basic titles
                base_keywords = top_keywords.split(',')[0].strip() if top_keywords else "Solutions"
                return [
                    f"Best {base_keywords} Tools & Software for 2024",
                    f"How to Choose the Right {base_keywords} Platform",
                    f"Top 10 {base_keywords} Features You Need to Know",
                    f"Ultimate {base_keywords} Guide for Businesses",
                    f"Why {base_keywords} Matters: Complete Overview"
                ]
                
            else:
                return [f"HTTP Error {response.status_code}"] * 5
                
        except Exception as e:
            return [f"Error: {str(e)}"] * 5
    
    def process_csv(self, input_file, output_file):
        """Process CSV file and generate titles for each row"""
        try:
            # Read CSV
            df = pd.read_csv(input_file)
            
            # Map column names flexibly
            column_mapping = {}
            for col in df.columns:
                col_lower = col.lower()
                if 'url' in col_lower:
                    column_mapping['url'] = col
                elif 'title' in col_lower:
                    column_mapping['title'] = col
                elif 'keyword' in col_lower:
                    column_mapping['keywords'] = col
            
            # Validate we found the required columns
            required = ['url', 'title', 'keywords']
            missing = [req for req in required if req not in column_mapping]
            
            if missing:
                print(f"✗ Could not find columns for: {missing}")
                print(f"Found columns: {list(df.columns)}")
                print("CSV should contain columns with 'URL', 'Title', and 'Keywords' in their names")
                return False
            
            print(f"Mapped columns: URL='{column_mapping['url']}', Title='{column_mapping['title']}', Keywords='{column_mapping['keywords']}')")
            
            print(f"Processing {len(df)} rows...")
            
            # Add new column for generated titles
            generated_titles = []
            
            for index, row in df.iterrows():
                print(f"Processing row {index + 1}/{len(df)}: {row[column_mapping['url']]}")
                
                titles = self.generate_titles(
                    row[column_mapping['url']], 
                    row[column_mapping['title']], 
                    row[column_mapping['keywords']]
                )
                
                # Join titles with line breaks
                titles_text = '\n'.join(titles)
                generated_titles.append(titles_text)
                
                # Add small delay to avoid overwhelming the model
                time.sleep(0.5)
            
            # Add generated titles to dataframe
            df['Generated Titles'] = generated_titles
            
            # Save to output file
            df.to_csv(output_file, index=False)
            print(f"✓ Results saved to {output_file}")
            return True
            
        except Exception as e:
            print(f"✗ Error processing CSV: {e}")
            return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python seo_title_generator.py <input_csv> <output_csv>")
        print("Example: python seo_title_generator.py input.csv output.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Initialize generator
    generator = SEOTitleGenerator()
    
    # Test connection
    if not generator.test_connection():
        print("Please ensure Ollama is running and the model is available.")
        print("Run: ollama serve")
        print("Then: ollama pull llama3.1:8b-instruct-q4_K_M")
        sys.exit(1)
    
    # Process CSV
    success = generator.process_csv(input_file, output_file)
    
    if success:
        print("✓ Title generation completed successfully!")
    else:
        print("✗ Title generation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
# python SEOTools/ollamaTitleOptimizer/ollamaTitleOptimizer.py SEOTools/ollamaTitleOptimizer/source.csv SEOTools/ollamaTitleOptimizer/output.csv