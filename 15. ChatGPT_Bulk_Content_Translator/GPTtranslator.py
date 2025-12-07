import os
import requests
from bs4 import BeautifulSoup
import csv
import openai
import time
import re
from urllib.parse import urlparse
import json

# Get API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    print("Please set your API key: export OPENAI_API_KEY='your-api-key-here'")
    exit(1)

def log(message, level="INFO"):
    """Enhanced logging with colors and levels"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    colors = {
        "INFO": "\033[92m",    # Green
        "WARN": "\033[93m",    # Yellow
        "ERROR": "\033[91m",   # Red
        "SUCCESS": "\033[96m"  # Cyan
    }
    reset = "\033[0m"
    color = colors.get(level, "")
    print(f"{color}[{timestamp}] {level}: {message}{reset}")

def get_csv_filename(url):
    """Generate CSV filename from URL in the same directory as this script"""
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '').replace('.', '_')
    path = re.sub(r'[^\w\-_]', '_', parsed.path.strip('/'))
    if path:
        filename = f"{domain}_{path}.csv"
    else:
        filename = f"{domain}.csv"
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, filename)

def prompt_language():
    """Prompt user for target language"""
    print("\n🌐 Language Selection")
    print("Enter the 2-letter language code (e.g., 'fr' for French, 'es' for Spanish, 'de' for German)")
    while True:
        lang = input("Target language code: ").strip().lower()
        if len(lang) == 2 and lang.isalpha():
            return lang
        print("❌ Please enter a valid 2-letter language code")

def check_existing_csv(csv_path):
    """Check if CSV exists and return its structure"""
    if not os.path.exists(csv_path):
        return None, []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
            if rows:
                return rows, rows[0] if rows else []
            return None, []
    except Exception as e:
        log(f"Error reading existing CSV: {e}", "ERROR")
        return None, []

def prompt_refresh_content(csv_path):
    """Ask user if they want to refresh page content or use existing"""
    if not os.path.exists(csv_path):
        return True  # Must crawl if no CSV exists
    
    print(f"\n📁 Found existing CSV file: {csv_path}")
    print("Do you want to:")
    print("1. Refresh page content (re-crawl the page)")
    print("2. Use existing content (go straight to translation)")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == "1":
            return True
        elif choice == "2":
            return False
        print("❌ Please enter 1 or 2")

def fetch_and_parse_url(url):
    """Fetches and parses the content of the URL."""
    log(f"Fetching content from {url}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove the nav and footer sections to avoid irrelevant content
        for tag in soup.find_all(['nav', 'footer', 'script', 'style']):
            tag.decompose()

        log("Content fetched and parsed successfully.", "SUCCESS")
        return soup
    except Exception as e:
        log(f"Error fetching URL: {e}", "ERROR")
        return None

def get_unique_key(element):
    """Generates a unique identifier for a given BeautifulSoup element using tag, id, and class."""
    tag_name = element.name
    element_id = element.get('id', '')
    element_class = ' '.join(element.get('class', []))
    
    unique_key = f"{tag_name}#{element_id} {element_class}".strip()
    
    if not unique_key:
        unique_key = tag_name
    
    return unique_key

def save_to_csv(elements, csv_path, target_language):
    """Saves the extracted elements and their content to a CSV file."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    log(f"Saving {len(elements)} elements to {csv_path}...")

    existing_data, header = check_existing_csv(csv_path)
    
    if not header:
        # Create new CSV file
        header = ['Unique Key', 'Content', target_language]
        with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            for unique_key, content in elements:
                writer.writerow([unique_key, content, ""])
    else:
        # Update existing CSV
        if target_language not in header:
            header.append(target_language)
        
        # Create a mapping of existing unique keys to rows
        existing_keys = {}
        if existing_data:
            for i, row in enumerate(existing_data[1:], 1):  # Skip header
                if len(row) > 0:
                    existing_keys[row[0]] = i
        
        # Prepare new data
        new_data = [header]
        if existing_data:
            new_data.extend(existing_data[1:])
        
        # Add or update elements
        for unique_key, content in elements:
            if unique_key in existing_keys:
                # Update existing row
                row_idx = existing_keys[unique_key]
                if row_idx < len(new_data):
                    # Extend row to match header length
                    while len(new_data[row_idx]) < len(header):
                        new_data[row_idx].append("")
                    # Update content if it's different
                    new_data[row_idx][1] = content
            else:
                # Add new row
                new_row = [unique_key, content] + [""] * (len(header) - 2)
                new_data.append(new_row)
        
        # Ensure all rows have the same length as header
        for i in range(1, len(new_data)):
            while len(new_data[i]) < len(header):
                new_data[i].append("")
        
        # Write updated data
        with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(new_data)

    log(f"Elements saved successfully to {csv_path}", "SUCCESS")

def translate_content(content, target_language):
    """Translates content using OpenAI's GPT-4 with retry logic"""
    if not content.strip():
        return ""
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Using 3.5-turbo for cost efficiency
                messages=[
                    {"role": "system", "content": f"Translate the following text to {target_language}. Keep the same formatting and tone. Only return the translation, no explanations."},
                    {"role": "user", "content": content}
                ],
                max_tokens=2000,
                temperature=0.1,  # Low temperature for consistent translations
                timeout=60
            )
            translation = response['choices'][0]['message']['content'].strip()
            if translation:
                return translation
        except openai.error.RateLimitError:
            wait_time = (attempt + 1) * 10
            log(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}", "WARN")
            time.sleep(wait_time)
        except openai.error.APIError as e:
            log(f"API error on attempt {attempt + 1}: {e}", "WARN")
            if attempt < max_retries - 1:
                time.sleep(5)
        except Exception as e:
            log(f"Translation error on attempt {attempt + 1}: {e}", "WARN")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    log(f"Failed to translate after {max_retries} attempts: {content[:50]}...", "ERROR")
    return ""


def is_visible_element(element):
    """Check if an element is likely visible (not hidden by CSS or attributes)"""
    # Skip elements with display:none or visibility:hidden
    style = element.get('style', '')
    if 'display:none' in style.replace(' ', '') or 'visibility:hidden' in style.replace(' ', ''):
        return False
    
    # Skip hidden inputs and other hidden elements
    if element.get('type') == 'hidden' or element.get('hidden'):
        return False
    
    # Skip elements with common hidden classes
    classes = element.get('class', [])
    hidden_classes = ['hidden', 'sr-only', 'visually-hidden', 'd-none', 'invisible']
    if any(hidden_class in classes for hidden_class in hidden_classes):
        return False
    
    return True

def is_leaf_text_element(element):
    """Check if element is a leaf node with meaningful text content"""
    # Get direct text content (not from children)
    direct_text = element.get_text(strip=True)
    if not direct_text or len(direct_text) < 5:  # Skip very short text
        return False
    
    # Check if this element has child elements with significant text
    for child in element.find_all(recursive=False):
        if child.name and child.get_text(strip=True):
            child_text = child.get_text(strip=True)
            # If child contains substantial portion of parent's text, prefer child
            if len(child_text) > len(direct_text) * 0.7:
                return False
    
    return True

def split_concatenated_text(text):
    """Split concatenated text into meaningful chunks"""
    # Common patterns that indicate text boundaries
    patterns = [
        r'([.!?])\s*([A-Z][^.!?]*)',  # Sentence boundaries
        r'([a-z])([A-Z][a-z]+)',      # camelCase boundaries  
        r'(\w)([A-Z][A-Z][A-Z]+)',    # Word followed by acronym
        r'([^.!?])(\s*Create\s+free|\s*Book\s+a\s+demo|\s*Learn\s+more|\s*Get\s+started|\s*Sign\s+up|\s*Try\s+now)',  # CTA boundaries
    ]
    
    chunks = [text]
    for pattern in patterns:
        new_chunks = []
        for chunk in chunks:
            parts = re.split(pattern, chunk)
            if len(parts) > 1:
                # Reconstruct meaningful chunks
                for i in range(0, len(parts), 3):
                    if i + 2 < len(parts):
                        new_chunks.append((parts[i] + parts[i+1]).strip())
                        new_chunks.append(parts[i+2].strip())
                    else:
                        new_chunks.append(''.join(parts[i:]).strip())
            else:
                new_chunks.append(chunk)
        chunks = [c for c in new_chunks if c and len(c) > 3]
    
    # Filter out very short or empty chunks
    return [chunk for chunk in chunks if chunk and len(chunk.strip()) >= 5]

def extract_specific_buttons(soup):
    """Extract button elements and button-like links separately"""
    button_elements = []
    seen_buttons = set()
    
    # Look for actual button elements
    for button in soup.find_all('button'):
        if not is_visible_element(button):
            continue
        
        text = button.get_text(strip=True)
        if text and len(text) >= 2 and text not in seen_buttons:
            button_elements.append((f"button#{button.get('id', '')} {' '.join(button.get('class', []))}", text))
            seen_buttons.add(text)
    
    # Look for button-like links (CTAs)
    cta_classes = ['btn', 'button', 'cta', 'primary', 'secondary', 'action']
    for link in soup.find_all('a'):
        if not is_visible_element(link):
            continue
        
        classes = link.get('class', [])
        text = link.get_text(strip=True)
        
        # Check if it looks like a button/CTA
        is_button_like = any(cta_class in ' '.join(classes).lower() for cta_class in cta_classes)
        is_short_cta = len(text) <= 20 and any(keyword in text.lower() for keyword in 
                                              ['create', 'book', 'try', 'get', 'start', 'sign', 'learn', 'demo', 'free'])
        
        if (is_button_like or is_short_cta) and text and text not in seen_buttons:
            button_elements.append((f"a#{link.get('id', '')} {' '.join(classes)}", text))
            seen_buttons.add(text)
    
    return button_elements

def extract_text_elements(soup):
    """Extracts unique, visible text elements with better separation and button detection"""
    elements = []
    seen_content = set()  # Track content to avoid duplicates
    
    # First, extract buttons separately to ensure they're captured
    button_elements = extract_specific_buttons(soup)
    for unique_key, text in button_elements:
        elements.append((unique_key.strip(), text))
        seen_content.add(text)
    
    # Define target elements in order of preference (most specific first)
    target_elements = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'span', 'div']
    
    for tag in target_elements:
        for element in soup.find_all(tag):
            if not is_visible_element(element):
                continue
            
            text_content = element.get_text(strip=True)
            
            # Skip very short text, numbers only, or whitespace
            if len(text_content) < 5 or text_content.isdigit() or not text_content.replace(' ', ''):
                continue
            
            # For div and span, only include if they're leaf elements
            if tag in ['div', 'span']:
                if not is_leaf_text_element(element):
                    continue
            
            # Try to split concatenated text for better granularity
            text_chunks = split_concatenated_text(text_content)
            
            # If we got multiple meaningful chunks, use them instead of the whole text
            if len(text_chunks) > 1:
                for i, chunk in enumerate(text_chunks):
                    if chunk not in seen_content and len(chunk) >= 5:
                        # Check if this chunk is not a substring of existing content
                        is_duplicate = any(chunk in existing for existing in seen_content 
                                         if len(chunk) < len(existing) * 0.8)
                        if not is_duplicate:
                            unique_key = f"{tag}#{element.get('id', '')} {' '.join(element.get('class', []))} chunk-{i+1}"
                            elements.append((unique_key.strip(), chunk))
                            seen_content.add(chunk)
            else:
                # Use the original text if splitting didn't help
                if text_content not in seen_content:
                    # Skip if this text is contained within another element we've already processed
                    is_duplicate = False
                    for existing_content in seen_content:
                        if text_content in existing_content and len(text_content) < len(existing_content) * 0.9:
                            is_duplicate = True
                            break
                        # Also check reverse - if existing content is contained in current
                        elif existing_content in text_content and len(existing_content) < len(text_content) * 0.9:
                            # Remove the shorter content and use the longer one
                            seen_content.discard(existing_content)
                            # Remove from elements list
                            elements = [(key, content) for key, content in elements if content != existing_content]
                            break
                    
                    if not is_duplicate:
                        # Generate unique key and add to results
                        unique_key = f"{tag}#{element.get('id', '')} {' '.join(element.get('class', []))}"
                        elements.append((unique_key.strip(), text_content))
                        seen_content.add(text_content)
    
    log(f"Extracted {len(elements)} unique text elements (including {len(button_elements)} buttons)", "SUCCESS")
    return elements

def find_resume_point(csv_path, target_language):
    """Find where to resume translation by looking for empty cells"""
    existing_data, header = check_existing_csv(csv_path)
    if not existing_data or target_language not in header:
        return 0
    
    lang_col_idx = header.index(target_language)
    
    for i, row in enumerate(existing_data[1:], 1):  # Skip header
        if len(row) <= lang_col_idx or not row[lang_col_idx].strip():
            return i - 1  # Return 0-based index for elements list
    
    return len(existing_data) - 1  # All done

def process_translations(csv_path, target_language):
    """Processes translations for extracted elements and updates the CSV with intelligent resume."""
    existing_data, header = check_existing_csv(csv_path)
    
    if not existing_data:
        log("No CSV file found to translate", "ERROR")
        return False
    
    if target_language not in header:
        header.append(target_language)
        # Add empty column for new language
        for row in existing_data[1:]:
            row.append("")
    
    lang_col_idx = header.index(target_language)
    total_rows = len(existing_data) - 1  # Exclude header
    
    # Find resume point
    resume_point = find_resume_point(csv_path, target_language)
    
    if resume_point >= total_rows:
        log("All translations already completed!", "SUCCESS")
        return True
    
    log(f"Starting translation from row {resume_point + 1} of {total_rows} (resuming from {resume_point})", "INFO")
    
    # Process translations with progress tracking
    translated_count = 0
    for i in range(resume_point, total_rows):
        row_idx = i + 1  # Account for header
        row = existing_data[row_idx]
        
        if len(row) < 2 or not row[1].strip():  # Skip rows without content
            continue
            
        content = row[1].strip()
        
        # Skip if already translated and not empty
        if len(row) > lang_col_idx and row[lang_col_idx].strip():
            continue
            
        log(f"Translating row {i + 1}/{total_rows}: {content[:50]}...")
        
        translated_content = translate_content(content, target_language)
        
        if translated_content:
            # Ensure row has enough columns
            while len(row) <= lang_col_idx:
                row.append("")
            row[lang_col_idx] = translated_content
            translated_count += 1
            
            # Save progress periodically (every 5 translations)
            if translated_count % 5 == 0:
                save_progress(csv_path, existing_data, header)
                log(f"Progress saved - completed {translated_count} translations", "SUCCESS")
        else:
            log(f"Failed to translate row {i + 1}, skipping...", "WARN")
        
        # Calculate and display progress
        progress = ((i + 1) / total_rows) * 100
        log(f"Progress: {progress:.1f}% ({i + 1}/{total_rows} rows processed)")
    
    # Final save
    save_progress(csv_path, existing_data, header)
    log(f"Translation complete! Processed {translated_count} new translations.", "SUCCESS")
    return True

def save_progress(csv_path, data, header):
    """Save current translation progress to CSV"""
    try:
        # Ensure header is first row
        data[0] = header
        
        with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(data)
    except Exception as e:
        log(f"Error saving progress: {e}", "ERROR")


def main():
    print("🔧 GPT Translator - Intelligent Web Content Translation Tool")
    print("=" * 60)
    
    # Step 1: Get URL input
    url = input("\n🌐 Enter the URL to translate: ").strip()
    if not url:
        log("No URL provided. Exiting.", "ERROR")
        return
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        log(f"Added https:// prefix: {url}", "INFO")
    
    # Step 2: Generate CSV filename from URL
    csv_path = get_csv_filename(url)
    log(f"Using CSV file: {csv_path}", "INFO")
    
    # Step 3: Get target language
    target_language = prompt_language()
    log(f"Target language: {target_language}", "SUCCESS")
    
    # Step 4: Check if we should refresh content or use existing
    should_refresh = prompt_refresh_content(csv_path)
    
    if should_refresh:
        # Step 5: Fetch and parse the URL
        log("Fetching fresh content from URL...", "INFO")
        soup = fetch_and_parse_url(url)
        if not soup:
            log("Failed to fetch URL content. Exiting.", "ERROR")
            return
        
        # Step 6: Extract elements and save to CSV
        elements = extract_text_elements(soup)
        if not elements:
            log("No translatable elements found on the page.", "WARN")
            return
        
        log(f"Extracted {len(elements)} elements from the page", "SUCCESS")
        save_to_csv(elements, csv_path, target_language)
    else:
        log("Using existing page content from CSV", "INFO")
    
    # Step 7: Process translations with intelligent resume
    log(f"Starting translation to {target_language}...", "INFO")
    success = process_translations(csv_path, target_language)
    
    if success:
        print(f"\n✅ Translation completed successfully!")
        print(f"📁 Results saved to: {csv_path}")
        print(f"🌍 Language: {target_language}")
    else:
        print(f"\n❌ Translation process failed.")
        print(f"Check the logs above for more details.")
    
    print("\n🎉 GPT Translator session completed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Translation interrupted by user.")
        print("Progress has been saved. You can resume by running the tool again.")
    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR")
        print("❌ An unexpected error occurred. Check the logs above.")
