#!/usr/bin/env python3
"""
SEO Meta Description Generator using Ollama
Processes CSV with URL, Existing Title, Top 5 Keywords to generate optimized meta descriptions
"""

import pandas as pd
import requests
import json
import sys
import time
from urllib.parse import urlparse
import re

class SEOMetaGenerator:
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
    
    def generate_meta_descriptions(self, url, existing_title, top_keywords):
        """Generate 5 SEO-optimized meta descriptions using Ollama"""
        
        # Extract additional context from URL
        url_keywords = self.extract_domain_keywords(url)
        
        prompt = f"""TASK: Write exactly 5 meta descriptions. No explanations. No preambles. Just descriptions.

URL: {url}
Title: {existing_title}
Keywords: {top_keywords}

RULES:
- 130-160 characters each
- Include main keywords naturally
- Maximum CTR focus (benefits, action words, urgency)
- Include call-to-action
- Focus on user benefits and outcomes
- Use power words (free, best, ultimate, proven, instant)

OUTPUT FORMAT: Description1\nDescription2\nDescription3\nDescription4\nDescription5

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
                                "temperature": 0.4,  # Slightly higher for more creative CTR copy
                                "top_p": 0.8,
                                "num_predict": 500,  # More tokens for longer descriptions
                                "stop": ["\n\n", "EXPLANATION:", "Note:", "Remember:", "Here are"]
                            }
                        },
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        break
                        
                except requests.exceptions.Timeout:
                    if attempt < max_retries:
                        print(f"  Timeout on attempt {attempt + 1}, retrying...")
                        time.sleep(2)
                        continue
                    else:
                        # Generate fallback descriptions
                        base_keywords = top_keywords.split(',')[0].strip() if top_keywords else "solutions"
                        return [
                            f"Discover the best {base_keywords} tools and software. Get started free today and boost your productivity with proven solutions.",
                            f"Compare top-rated {base_keywords} platforms. Find the perfect solution for your business needs. Free trial available now!",
                            f"Expert {base_keywords} guide with tips, templates, and tools. Learn proven strategies to improve results fast. Start free today.",
                            f"Get instant access to professional {base_keywords} resources. Download templates, guides, and tools. Free signup required.",
                            f"Join thousands using our {base_keywords} platform. Increase efficiency by 10x with automated tools. Try it free now!"
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
                        'here are', 'meta description', 'optimized', 'options', 
                        'webpage', 'follow', 'requirements', 'characters', 
                        'seo', 'generate', 'description', 'task:'
                    ]
                    
                    line_lower = line.lower()
                    if any(pattern in line_lower for pattern in skip_patterns):
                        continue
                    
                    # Remove numbering and bullets
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = re.sub(r'^[\-\*\•]\s*', '', line)
                    
                    # Skip if too short or too long for meta descriptions
                    if len(line) < 100 or len(line) > 180:
                        continue
                    
                    # Truncate if ends with ... and try to fix
                    if line.endswith('...'):
                        line = line[:-3].strip()
                        if len(line) < 120:
                            continue
                    
                    # Ensure proper ending (period or exclamation)
                    if not line.endswith(('.', '!', '?')):
                        line += '.'
                    
                    clean_lines.append(line)
                
                # If we have good descriptions, return them
                if len(clean_lines) >= 3:
                    return clean_lines[:5]
                
                # Fallback: try to extract anything that looks like a meta description
                all_lines = result.split('\n')
                fallback_descriptions = []
                
                for line in all_lines:
                    line = line.strip()
                    if 100 <= len(line) <= 180 and not any(word in line.lower() for word in ['here are', 'meta', 'description', 'option']):
                        line = re.sub(r'^\d+[\.\)]\s*', '', line)
                        line = re.sub(r'^[\-\*\•]\s*', '', line)
                        if line.endswith('...'):
                            line = line[:-3].strip()
                        if not line.endswith(('.', '!', '?')):
                            line += '.'
                        if len(line) >= 120:
                            fallback_descriptions.append(line)
                
                if fallback_descriptions:
                    return fallback_descriptions[:5]
                
                # Last resort: generate basic meta descriptions
                base_keywords = top_keywords.split(',')[0].strip() if top_keywords else "tools"
                return [
                    f"Discover the best {base_keywords} software and tools for your business. Get started with our free trial and boost productivity today!",
                    f"Compare top-rated {base_keywords} platforms and find the perfect solution. Expert reviews, pricing, and free trials available now.",
                    f"Ultimate {base_keywords} guide with proven strategies, templates, and tools. Learn from experts and improve your results fast.",
                    f"Get instant access to professional {base_keywords} resources and templates. Join thousands of satisfied users. Start free today!",
                    f"Transform your business with our powerful {base_keywords} platform. Increase efficiency and save time. Try it free for 14 days!"
                ]
                
            else:
                return [f"HTTP Error {response.status_code}"] * 5
                
        except Exception as e:
            return [f"Error: {str(e)}"] * 5
    
    def process_csv(self, input_file, output_file):
        """Process CSV file and generate meta descriptions for each row"""
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
            
            # Add new column for generated meta descriptions
            generated_descriptions = []
            
            for index, row in df.iterrows():
                print(f"Processing row {index + 1}/{len(df)}: {row[column_mapping['url']]}")
                
                descriptions = self.generate_meta_descriptions(
                    row[column_mapping['url']], 
                    row[column_mapping['title']], 
                    row[column_mapping['keywords']]
                )
                
                # Join descriptions with line breaks
                descriptions_text = '\n'.join(descriptions)
                generated_descriptions.append(descriptions_text)
                
                # Add small delay to avoid overwhelming the model
                time.sleep(0.5)
            
            # Add generated descriptions to dataframe
            df['Generated Meta Descriptions'] = generated_descriptions
            
            # Save to output file
            df.to_csv(output_file, index=False)
            print(f"✓ Results saved to {output_file}")
            return True
            
        except Exception as e:
            print(f"✗ Error processing CSV: {e}")
            return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python seo_meta_generator.py <input_csv> <output_csv>")
        print("Example: python seo_meta_generator.py input.csv meta_output.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Initialize generator
    generator = SEOMetaGenerator()
    
    # Test connection
    if not generator.test_connection():
        print("Please ensure Ollama is running and the model is available.")
        print("Run: ollama serve")
        print("Then: ollama pull llama3.1:8b-instruct-q4_K_M")
        sys.exit(1)
    
    # Process CSV
    success = generator.process_csv(input_file, output_file)
    
    if success:
        print("✓ Meta description generation completed successfully!")
    else:
        print("✗ Meta description generation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()

# python SEOTools/ollamaDescriptionOptimizer/ollamaDescriptionOptimizer.py SEOTools/ollamaDescriptionOptimizer/source.csv SEOTools/ollamaDescriptionOptimizer/output.csv