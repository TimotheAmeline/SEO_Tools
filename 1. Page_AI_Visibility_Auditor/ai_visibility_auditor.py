#!/usr/bin/env python3
"""
AI Visibility Auditor
Analyzes how well a webpage's content might be visible to AI search mechanisms
by simulating query fan-out processes.
"""

import os
import re
import json
import datetime
import requests
import argparse
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass
from bs4 import BeautifulSoup
import openai
from sentence_transformers import SentenceTransformer

# API Base URLs
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
OLLAMA_BASE_URL = "http://localhost:11434"

@dataclass
class AuditResult:
    entity_name: str
    url: str
    coverage_score: float
    audit_details: List[Dict[str, Any]]
    reasoning_about_facets: str
    timestamp: str

class WebContentExtractor:
    """Extracts and processes content from web pages"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def extract_content(self, url: str) -> Dict[str, Any]:
        """Extract main content and identify entity from URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Extract main content
            content_selectors = [
                'main', 'article', '.content', '#content', 
                '.post-content', '.entry-content', '.main-content'
            ]
            
            main_content = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    main_content = element.get_text(separator=' ', strip=True)
                    break
            
            if not main_content:
                # Fallback to body content
                body = soup.find('body')
                if body:
                    main_content = body.get_text(separator=' ', strip=True)
            
            # Clean up text
            main_content = re.sub(r'\s+', ' ', main_content).strip()
            
            # Extract meta description
            meta_desc = ""
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                meta_desc = desc_tag.get('content', '').strip()
            
            return {
                "status": "success",
                "title": title_text,
                "content": main_content,
                "meta_description": meta_desc,
                "url": url
            }
            
        except Exception as e:
            return {
                "status": "failure",
                "error": str(e),
                "url": url
            }

class UnifiedAIClient:
    """Unified client for multiple AI providers"""
    
    def __init__(self, provider: str, model: str = None, api_key: str = None):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.client = None
        
        if self.provider == "deepseek":
            if not api_key:
                raise ValueError("DeepSeek API key required")
            self.client = openai.OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
            self.model = model or "deepseek-chat"
            
        elif self.provider == "openai":
            if not api_key:
                raise ValueError("OpenAI API key required")
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model or "gpt-4o-mini"
            
        elif self.provider == "gemini":
            if not api_key:
                raise ValueError("Gemini API key required")
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(model or 'gemini-1.5-flash')
                self.model = model or 'gemini-1.5-flash'
            except ImportError:
                raise ImportError("Please install google-generativeai: pip install google-generativeai")
                
        elif self.provider == "ollama":
            self.client = openai.OpenAI(
                base_url=OLLAMA_BASE_URL + "/v1",
                api_key="ollama"
            )
            self.model = model or "llama3.2"
            
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def generate_response(self, prompt: str) -> str:
        """Generate response from the configured AI provider"""
        try:
            if self.provider == "gemini":
                response = self.client.generate_content(prompt)
                return response.text.strip()
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2000
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error with {self.provider.title()} API: {e}")
            return ""

class EntityExtractor:
    """Extract main entity from web content"""
    
    def __init__(self, ai_client: UnifiedAIClient):
        self.client = ai_client
    
    def extract_entity(self, content_data: Dict[str, Any]) -> str:
        """Extract the main entity/topic from content"""
        if content_data.get("status") == "failure":
            return "Content Extraction Error"
        
        title = content_data.get("title", "")
        meta_desc = content_data.get("meta_description", "")
        content = content_data.get("content", "")[:2000]  # Limit for API
        url = content_data.get("url", "")
        
        prompt = f"""
Analyze the following webpage content and identify the PRIMARY SUBJECT or main entity.
Respond with ONLY the entity name (1-4 words maximum).

URL: {url}
Title: {title}
Meta Description: {meta_desc}
Content Preview: {content}

Main Entity:"""
        
        entity = self.client.generate_response(prompt)
        
        if not entity or len(entity.split()) > 6:
            # Fallback to domain name
            parsed_domain = urlparse(url).netloc.replace("www.", "").split('.')[0].title()
            entity = parsed_domain
        
        return entity.strip()

class SyntheticQueryGenerator:
    """Generate synthetic queries that simulate AI search fan-out"""
    
    def __init__(self, ai_client: UnifiedAIClient):
        self.client = ai_client
    
    def generate_queries(self, entity_name: str, num_queries: int = 10) -> Dict[str, Any]:
        """Generate synthetic queries for an entity"""
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        prompt = f"""
You are simulating how an AI search system (like Google AI Mode) would internally "fan-out" queries to comprehensively understand an entity.

ENTITY: {entity_name}
CURRENT DATE: {current_date}
NUMBER OF QUERIES TO GENERATE: {num_queries}

First, reason about the key facets and types of information a user exploring this entity might need:
- Content based on the intent of the page (e.g., Homepage = brand, Product Page = technical details, Blog Page = more informational content)
- Definitional/explanatory aspects
- Practical applications or how-to information  
- Benefits, drawbacks, comparisons
- Recent developments (considering current date: {current_date})
- Related sub-topics or entities
- Business outcomes and KPIs for strategic leaders

Then generate exactly {num_queries} diverse, specific queries that an AI system might use internally.

Format your response as:

REASONING:
[Your brief reasoning about key facets]

QUERIES:
1. [query 1]
2. [query 2]
3. [query 3]
...
"""
        
        response = self.client.generate_response(prompt)
        
        # Parse reasoning and queries
        reasoning = ""
        queries = []
        
        if "REASONING:" in response and "QUERIES:" in response:
            parts = response.split("QUERIES:")
            reasoning = parts[0].replace("REASONING:", "").strip()
            
            query_section = parts[1].strip()
            query_lines = query_section.split('\n')
            
            for line in query_lines:
                line = line.strip()
                # Remove numbering
                line = re.sub(r'^\d+\.\s*', '', line)
                if line and len(line) > 10:  # Basic validation
                    queries.append(line)
        
        # Fallback parsing if format not followed
        if not queries:
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                line = re.sub(r'^\d+\.\s*', '', line)
                if line and len(line) > 10 and '?' in line:
                    queries.append(line)
        
        return {
            "reasoning": reasoning,
            "queries": queries[:num_queries]
        }

class ContentChunker:
    """Chunk content for better processing"""
    
    @staticmethod
    def chunk_text(text: str, max_chunk_length: int = 500, overlap_words: int = 10) -> List[str]:
        """Split text into overlapping chunks"""
        if not text:
            return []
        
        sentences = re.split(r'(?<=[.!?])\s+', text.replace('\n', ' '))
        if not sentences:
            return [text] if text else []
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > max_chunk_length and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap
                words = current_chunk.split()
                current_chunk = " ".join(words[-overlap_words:]) if len(words) > overlap_words else ""
            current_chunk += " " + sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return [c for c in chunks if c.strip()]

class SemanticSimilarityScorer:
    """Score semantic similarity between queries and content"""
    
    def __init__(self):
        # Using a lightweight sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if vec1.size == 0 or vec2.size == 0:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0.0
        
        return dot_product / (norm_vec1 * norm_vec2)
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text"""
        try:
            return self.model.encode(text)
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return np.array([])
    
    def score_coverage(self, query: str, content_chunks: List[str], threshold: float = 0.75) -> Dict[str, Any]:
        """Score how well content chunks cover a query"""
        if not query or not content_chunks:
            return {
                "is_covered": False,
                "best_matching_chunk": "",
                "max_similarity": 0.0
            }
        
        query_embedding = self.get_embedding(query)
        if query_embedding.size == 0:
            return {
                "is_covered": False,
                "best_matching_chunk": "",
                "max_similarity": 0.0
            }
        
        max_similarity = 0.0
        best_chunk = ""
        
        for chunk in content_chunks:
            chunk_embedding = self.get_embedding(chunk)
            if chunk_embedding.size > 0:
                similarity = self.cosine_similarity(query_embedding, chunk_embedding)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_chunk = chunk
        
        is_covered = max_similarity >= threshold
        
        return {
            "is_covered": is_covered,
            "best_matching_chunk": best_chunk if is_covered else "",
            "max_similarity": max_similarity
        }

class AIVisibilityAuditor:
    """Main auditor class that orchestrates the entire process"""
    
    def __init__(self, provider: str, model: str = None, api_key: str = None):
        self.ai_client = UnifiedAIClient(provider, model, api_key)
        self.content_extractor = WebContentExtractor()
        self.entity_extractor = EntityExtractor(self.ai_client)
        self.query_generator = SyntheticQueryGenerator(self.ai_client)
        self.chunker = ContentChunker()
        self.similarity_scorer = SemanticSimilarityScorer()
        self.provider = provider
    
    def audit_url(self, url: str, num_synthetic_queries: int = 10, coverage_threshold: float = 0.75) -> AuditResult:
        """Run complete AI visibility audit on a URL"""
        print(f"\n🚀 Starting AI Visibility Audit for: {url}")
        
        # Step 1: Extract content
        print("📄 Extracting content...")
        content_data = self.content_extractor.extract_content(url)
        
        if content_data.get("status") == "failure":
            return AuditResult(
                entity_name="Content Extraction Error",
                url=url,
                coverage_score=0.0,
                audit_details=[],
                reasoning_about_facets=f"Error: {content_data.get('error', 'Unknown error')}",
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
        
        # Step 2: Extract main entity
        print("🧠 Identifying main entity...")
        entity_name = self.entity_extractor.extract_entity(content_data)
        print(f"✅ Main entity identified: '{entity_name}'")
        
        # Step 3: Chunk content
        print("✂️ Chunking content...")
        content_chunks = self.chunker.chunk_text(content_data.get("content", ""))
        print(f"📝 Created {len(content_chunks)} content chunks")
        
        # Step 4: Generate synthetic queries
        print(f"🔍 Generating {num_synthetic_queries} synthetic queries...")
        query_data = self.query_generator.generate_queries(entity_name, num_synthetic_queries)
        synthetic_queries = query_data["queries"]
        reasoning = query_data["reasoning"]
        
        print(f"✅ Generated {len(synthetic_queries)} queries:")
        for i, query in enumerate(synthetic_queries, 1):
            print(f"  {i}. {query}")
        
        # Step 5: Score coverage
        print("\n🕵️ Assessing coverage for each synthetic query...")
        covered_count = 0
        audit_details = []
        
        for query in synthetic_queries:
            coverage_result = self.similarity_scorer.score_coverage(
                query, content_chunks, coverage_threshold
            )
            
            status = "✅ Covered" if coverage_result["is_covered"] else "❌ Not Covered"
            print(f"  - Query: '{query[:70]}...' -> {status} (Max Similarity: {coverage_result['max_similarity']:.2f})")
            
            if coverage_result["is_covered"]:
                covered_count += 1
            
            audit_details.append({
                "query": query,
                "covered": bool(coverage_result["is_covered"]),
                "max_similarity": float(coverage_result["max_similarity"]),
                "best_chunk": coverage_result["best_matching_chunk"]
            })
        
        # Calculate final score
        coverage_score = (covered_count / len(synthetic_queries)) * 100 if synthetic_queries else 0.0
        print(f"\n📊 Final Coverage Score: {coverage_score:.2f}%")
        
        return AuditResult(
            entity_name=entity_name,
            url=url,
            coverage_score=coverage_score,
            audit_details=audit_details,
            reasoning_about_facets=reasoning,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
    
    def save_results(self, result: AuditResult, filename: Optional[str] = None) -> str:
        """Save audit results to JSON file"""
        json_dir, _ = ensure_output_directories()
        
        if not filename:
            entity_safe = re.sub(r'[^a-zA-Z0-9_]', '', result.entity_name.replace(' ', '_')).lower()[:30]
            filename = f"ai_visibility_audit_{entity_safe}.json"
        
        # Ensure filename is just the name, not a path
        filename = os.path.basename(filename)
        full_path = os.path.join(json_dir, filename)
        
        output_data = {
            "url": result.url,
            "entity_name": result.entity_name,
            "overall_coverage_score_percent": result.coverage_score,
            "audit_timestamp_utc": result.timestamp,
            "llm_reasoning_for_queries": result.reasoning_about_facets,
            "synthetic_query_details": result.audit_details,
            "parameters": {
                "num_synthetic_queries_generated": len(result.audit_details),
                "coverage_threshold_used": 0.75  # Could be made configurable
            },
            "llm_provider": self.provider.title(),
            "llm_model": self.ai_client.model,
            "embedding_provider": "SentenceTransformers"
        }
        
        with open(full_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"💾 JSON results saved to {full_path}")
        return full_path
    
    def save_text_results(self, result: AuditResult, url: str) -> str:
        """Save audit results to text file based on URL"""
        _, text_dir = ensure_output_directories()
        
        # Extract domain from URL for filename
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "").replace(".", "_")
        filename = f"{domain}_output.txt"
        full_path = os.path.join(text_dir, filename)
        
        # Format the output text
        output_text = f"""AI VISIBILITY AUDIT RESULTS
{'='*60}

URL: {result.url}
Entity: {result.entity_name}
Coverage Score: {result.coverage_score:.2f}%
Queries Covered: {sum(1 for d in result.audit_details if d['covered'])}/{len(result.audit_details)}
Audit Timestamp: {result.timestamp}

REASONING ABOUT FACETS:
{result.reasoning_about_facets}

SYNTHETIC QUERIES AND COVERAGE:
"""
        
        for i, detail in enumerate(result.audit_details, 1):
            status = "✅ Covered" if detail["covered"] else "❌ Not Covered"
            output_text += f"\n{i}. {detail['query']}\n"
            output_text += f"   Status: {status} (Max Similarity: {detail['max_similarity']:.2f})\n"
            if detail["covered"] and detail["best_chunk"]:
                output_text += f"   Best Matching Content: {detail['best_chunk'][:200]}...\n"
        
        output_text += f"\n{'='*60}\nAudit completed at {result.timestamp}\n"
        
        # Write to file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(output_text)
        
        print(f"📄 Text results saved to {full_path}")
        return full_path

def get_script_directory():
    """Get the directory where this script is located"""
    return os.path.dirname(os.path.abspath(__file__))

def ensure_output_directories():
    """Create output directories if they don't exist"""
    script_dir = get_script_directory()
    json_dir = os.path.join(script_dir, "Json")
    text_dir = os.path.join(script_dir, "Text")
    
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(text_dir, exist_ok=True)
    
    return json_dir, text_dir

def get_available_ollama_models():
    """Get available Ollama models"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [model['name'] for model in models]
        return []
    except:
        return []

def select_provider_and_model():
    """Interactive provider and model selection"""
    print("\n🤖 AI Provider Selection")
    print("=" * 40)
    print("1. Ollama (Local)")
    print("2. DeepSeek API")  
    print("3. OpenAI API")
    print("4. Gemini API")
    
    while True:
        choice = input("\nSelect AI provider (1-4): ").strip()
        
        if choice == "1":
            print("\n🦙 Ollama Configuration")
            available_models = get_available_ollama_models()
            if not available_models:
                print("❌ No Ollama models found. Make sure Ollama is running and has models installed.")
                print("   Install a model with: ollama pull llama3.2")
                continue
                
            print("Available models:")
            for i, model in enumerate(available_models, 1):
                print(f"{i}. {model}")
            
            while True:
                model_choice = input(f"Select model (1-{len(available_models)}): ").strip()
                try:
                    model_idx = int(model_choice) - 1
                    if 0 <= model_idx < len(available_models):
                        return "ollama", available_models[model_idx], None
                    else:
                        print("Invalid choice, please try again.")
                except ValueError:
                    print("Please enter a number.")
                    
        elif choice == "2":
            key = input("Enter DeepSeek API key: ").strip()
            return "deepseek", "deepseek-chat", key
            
        elif choice == "3":
            print("\n🤖 OpenAI Configuration")
            print("Available models: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo")
            model = input("Select model (default: gpt-4o-mini): ").strip() or "gpt-4o-mini"
            key = input("Enter OpenAI API key: ").strip()
            return "openai", model, key
            
        elif choice == "4":
            print("\n💎 Gemini Configuration") 
            print("Available models: gemini-1.5-flash, gemini-1.5-pro, gemini-1.0-pro")
            model = input("Select model (default: gemini-1.5-flash): ").strip() or "gemini-1.5-flash"
            key = input("Enter Gemini API key: ").strip()
            return "gemini", model, key
            
        else:
            print("Invalid choice, please select 1-4.")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='AI Visibility Auditor - Analyze webpage visibility to AI search')
    
    # Provider selection arguments
    provider_group = parser.add_mutually_exclusive_group()
    provider_group.add_argument('--ollama', metavar='MODEL', help='Use Ollama with specified model')
    provider_group.add_argument('--deepseek', action='store_true', help='Use DeepSeek API')
    provider_group.add_argument('--openai', metavar='MODEL', nargs='?', const='gpt-4o-mini', help='Use OpenAI API with optional model')
    provider_group.add_argument('--gemini', metavar='MODEL', nargs='?', const='gemini-1.5-flash', help='Use Gemini API with optional model')
    
    # Other arguments
    parser.add_argument('--url', help='URL to audit')
    parser.add_argument('--queries', type=int, default=10, help='Number of synthetic queries (default: 10)')
    parser.add_argument('--threshold', type=float, default=0.5, help='Coverage threshold (default: 0.5)')
    parser.add_argument('--api-key', help='API key for selected provider')
    
    return parser.parse_args()

def main():
    """Main function with provider selection and audit execution"""
    args = parse_arguments()
    
    # Determine provider, model, and API key
    provider = None
    model = None
    api_key = None
    
    if args.ollama:
        provider = "ollama"
        model = args.ollama
        api_key = None
    elif args.deepseek:
        provider = "deepseek"
        model = "deepseek-chat"
        api_key = args.api_key
    elif args.openai:
        provider = "openai"
        model = args.openai
        api_key = args.api_key
    elif args.gemini:
        provider = "gemini"
        model = args.gemini
        api_key = args.api_key
    else:
        # Interactive selection
        provider, model, api_key = select_provider_and_model()
    
    # Get URL and other parameters
    if args.url:
        url_to_audit = args.url
    else:
        url_to_audit = input("\nEnter URL to audit: ").strip()
        if not url_to_audit:
            url_to_audit = "https://example.com/"
    
    num_queries = args.queries
    coverage_threshold = args.threshold
    
    # Display configuration
    print(f"\n🔧 Configuration")
    print(f"   Provider: {provider.title()}")
    print(f"   Model: {model}")
    print(f"   URL: {url_to_audit}")
    print(f"   Queries: {num_queries}")
    print(f"   Threshold: {coverage_threshold}")
    
    # Initialize auditor
    try:
        auditor = AIVisibilityAuditor(provider, model, api_key)
    except Exception as e:
        print(f"❌ Error initializing {provider}: {e}")
        if provider == "gemini":
            print("   Install Gemini library: pip install google-generativeai")
        elif provider == "ollama":
            print("   Make sure Ollama is running: ollama serve")
        return
    
    # Run audit
    try:
        result = auditor.audit_url(url_to_audit, num_queries, coverage_threshold)
        
        # Save results
        json_filename = auditor.save_results(result)
        text_filename = auditor.save_text_results(result, url_to_audit)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"AI VISIBILITY AUDIT SUMMARY")
        print(f"{'='*60}")
        print(f"URL: {result.url}")
        print(f"Entity: {result.entity_name}")
        print(f"Provider: {provider.title()} ({model})")
        print(f"Coverage Score: {result.coverage_score:.2f}%")
        print(f"Queries Covered: {sum(1 for d in result.audit_details if d['covered'])}/{len(result.audit_details)}")
        print(f"JSON results saved to: {json_filename}")
        print(f"Text results saved to: {text_filename}")
        
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
