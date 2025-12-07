# AI Visibility Auditor

A powerful tool that analyzes how well a webpage's content might be visible to AI search mechanisms by simulating query fan-out processes.

## Overview

The AI Visibility Auditor uses advanced AI techniques to evaluate your content's visibility to AI-powered search systems. It extracts content from web pages, identifies the main entity/topic, generates synthetic queries that AI systems might use, and measures how well your content covers these potential queries.

## Features

- **Multiple AI Providers**: Support for Ollama (local), DeepSeek, OpenAI, and Gemini APIs
- **Content Extraction**: Automatically extracts main content from web pages
- **Entity Identification**: Uses AI to identify the primary subject of your content
- **Synthetic Query Generation**: Creates realistic queries that AI search systems might use
- **Semantic Coverage Analysis**: Measures content coverage using advanced similarity scoring
- **Dual Output Format**: Saves results in both JSON and human-readable text formats
- **Configurable Parameters**: Customize number of queries and coverage thresholds
- **Command Line Interface**: Support for both interactive and command-line usage

## Supported AI Providers

### 1. Ollama (Local)
- **Pros**: Free, private, no API limits
- **Cons**: Requires local installation and setup
- **Setup**: Install Ollama and pull models (e.g., `ollama pull llama3.2`)

### 2. DeepSeek API
- **Pros**: Cost-effective, good performance
- **Cons**: Requires API key
- **Models**: deepseek-chat

### 3. OpenAI API
- **Pros**: High quality, reliable
- **Cons**: More expensive
- **Models**: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo

### 4. Gemini API
- **Pros**: Good performance, competitive pricing
- **Cons**: Requires Google account and API key
- **Models**: gemini-1.5-flash, gemini-1.5-pro, gemini-1.0-pro

## Requirements

- Python 3.7+
- At least one AI provider configured
- Required Python packages:
  ```bash
  pip install requests beautifulsoup4 openai sentence-transformers numpy
  ```
- Optional packages:
  ```bash
  pip install google-generativeai  # For Gemini support
  ```

## Setup

1. **Install Dependencies**:
   ```bash
   pip install requests beautifulsoup4 openai sentence-transformers numpy
   ```

2. **Configure AI Providers** (choose one or more):

   **For Ollama (Local)**:
   ```bash
   # Install Ollama from https://ollama.ai
   ollama pull llama3.2  # or any other model
   ollama serve
   ```

   **For DeepSeek, OpenAI, or Gemini**:
   - Obtain your API key from the provider's dashboard.
   - Pass it to the script using the `--api-key` argument.

## Usage

### Interactive Mode

Run the script without arguments for interactive provider selection:

```bash
python ai_visibility_auditor.py
```

You'll be prompted to:
1. **Select AI Provider**: Choose from Ollama, DeepSeek, OpenAI, or Gemini
2. **Choose Model**: Select specific model for the provider
3. **Enter URL**: The webpage you want to analyze
4. **Configure Parameters**: Number of queries and coverage threshold

### Command Line Mode

Use command line arguments to skip interactive selection:

```bash
# Using Ollama with specific model
python ai_visibility_auditor.py --ollama llama3.2 --url https://example.com

# Using DeepSeek
python ai_visibility_auditor.py --deepseek --url https://example.com

# Using OpenAI with specific model
python ai_visibility_auditor.py --openai gpt-4o --url https://example.com

# Using Gemini with default model
python ai_visibility_auditor.py --gemini --url https://example.com

# With additional parameters
python ai_visibility_auditor.py --openai --url https://example.com --queries 7 --threshold 0.8
```

### Command Line Arguments

- `--ollama MODEL`: Use Ollama with specified model
- `--deepseek`: Use DeepSeek API
- `--openai [MODEL]`: Use OpenAI API with optional model (default: gpt-4o-mini)
- `--gemini [MODEL]`: Use Gemini API with optional model (default: gemini-1.5-flash)
- `--url URL`: URL to audit
- `--queries N`: Number of synthetic queries (default: 5)
- `--threshold N`: Coverage threshold (default: 0.75)

### Examples

**Quick audit with DeepSeek**:
```bash
python ai_visibility_auditor.py --deepseek --url https://your-website.com
```

**Detailed audit with OpenAI**:
```bash
python ai_visibility_auditor.py --openai gpt-4o --url https://your-website.com --queries 10 --threshold 0.8
```

**Local analysis with Ollama**:
```bash
python ai_visibility_auditor.py --ollama llama3.2 --url https://your-website.com --queries 7
```

## Output

The tool generates two output files:

1. **JSON File**: `ai_visibility_audit_[entity_name].json`
   - Structured data with detailed analysis
   - Suitable for programmatic processing

2. **Text File**: `[domain]_output.txt`
   - Human-readable summary
   - Includes all queries and coverage analysis
   - Easy to share and review

### Sample Output

```
AI VISIBILITY AUDIT RESULTS
============================================================

URL: https://example.com/your-page
Entity: Your Topic
Coverage Score: 85.71%
Queries Covered: 6/7
Audit Timestamp: 2024-01-15T10:30:45.123456

REASONING ABOUT FACETS:
The key facets for this entity include definitional aspects,
practical applications, benefits and drawbacks...

SYNTHETIC QUERIES AND COVERAGE:

1. What is Your Topic and how does it work?
   Status: ✅ Covered (Max Similarity: 0.82)
   Best Matching Content: Your Topic is a comprehensive solution...

2. What are the benefits of using Your Topic?
   Status: ✅ Covered (Max Similarity: 0.79)
   ...
```

## How It Works

1. **Content Extraction**: Downloads and parses the webpage, removing navigation and non-content elements
2. **Entity Identification**: Uses AI to determine the main subject/topic of the page
3. **Content Chunking**: Breaks content into semantic chunks for better analysis
4. **Query Generation**: Creates synthetic queries that AI systems might use to find information about the entity
5. **Similarity Scoring**: Uses sentence transformers to measure semantic similarity between queries and content chunks
6. **Coverage Analysis**: Determines which queries are adequately covered by the content

## Configuration

### Coverage Threshold

The coverage threshold (default: 0.75) determines when a query is considered "covered" by your content. Higher values mean stricter requirements:

- **0.6-0.7**: Lenient - broader content matching
- **0.75-0.8**: Balanced - good coverage detection
- **0.8-0.9**: Strict - only high-quality matches

### Number of Queries

More queries provide a more comprehensive analysis but take longer to process:

- **3-5**: Quick analysis
- **5-7**: Balanced assessment
- **8-10**: Comprehensive evaluation

## Interpreting Results

### Coverage Score
- **90-100%**: Excellent AI visibility
- **70-89%**: Good coverage with room for improvement
- **50-69%**: Moderate coverage, consider content expansion
- **Below 50%**: Poor coverage, significant content gaps

### Query Analysis
- **Covered queries**: Your content addresses these information needs well
- **Uncovered queries**: Content gaps that could improve AI visibility
- **Similarity scores**: Higher scores indicate better semantic matching

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your API keys are valid and set correctly for your chosen provider
2. **Content Extraction Failed**: Check if the URL is accessible and contains readable content
3. **Low Coverage Scores**: Your content might need more comprehensive information about the topic
4. **Ollama Connection Error**: Make sure Ollama is running (`ollama serve`) and models are installed
5. **Gemini Import Error**: Install the Gemini library (`pip install google-generativeai`)

### Error Messages

- `Content Extraction Error`: URL inaccessible or parsing failed
- `DeepSeek/OpenAI/Gemini API Error`: API key issues or service unavailable
- `Ollama Connection Error`: Ollama service not running or model not available
- `Embedding Error`: Sentence transformer model loading issues
- `Provider Error`: Unsupported provider or initialization failed

## Advanced Usage

### Programmatic Usage

```python
from ai_visibility_auditor import AIVisibilityAuditor

# Initialize auditor with different providers
auditor_deepseek = AIVisibilityAuditor("deepseek", "deepseek-chat", "your-deepseek-key")
auditor_openai = AIVisibilityAuditor("openai", "gpt-4o-mini", "your-openai-key")
auditor_ollama = AIVisibilityAuditor("ollama", "llama3.2")
auditor_gemini = AIVisibilityAuditor("gemini", "gemini-1.5-flash", "your-gemini-key")

# Run audit
result = auditor_openai.audit_url("https://example.com", num_queries=7, threshold=0.8)

# Save results
auditor_openai.save_results(result)
auditor_openai.save_text_results(result, "https://example.com")

# Access results
print(f"Coverage: {result.coverage_score}%")
print(f"Provider: {auditor_openai.provider}")
for detail in result.audit_details:
    print(f"Query: {detail['query']}")
    print(f"Covered: {detail['covered']}")
```

### Provider Selection Tips

**Choose Ollama if**:
- You want complete privacy and control
- You have sufficient local computing resources
- You don't want to pay for API calls
- You need to run many audits

**Choose DeepSeek if**:
- You want cost-effective API usage
- You need good performance at low cost
- You're doing moderate volume analysis

**Choose OpenAI if**:
- You need the highest quality results
- Cost is not a primary concern
- You want reliable, consistent performance

**Choose Gemini if**:
- You want good performance at competitive pricing
- You're already using Google services
- You need a balance of cost and quality

## Contributing

Feel free to submit issues and enhancement requests. Contributions are welcome!

## License

This project is available under the MIT License.
