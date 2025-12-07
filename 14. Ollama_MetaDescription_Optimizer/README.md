# Ollama Description Optimizer

An AI-powered SEO meta description generator that uses Ollama's local LLM to create optimized meta descriptions for multiple URLs.

## Features

- **Local AI Processing**: Uses Ollama for privacy-focused, local LLM processing
- **Batch Processing**: Generate meta descriptions for multiple URLs from CSV input
- **SEO Optimized**: Creates descriptions that are 130-160 characters with high CTR focus
- **Smart Context Extraction**: Automatically extracts keywords from URL structure
- **Fallback Generation**: Robust error handling with intelligent fallbacks
- **Model Flexibility**: Configurable Ollama model selection

## Requirements

- Python 3.7+
- Ollama installed and running
- Required Python packages: `pandas`, `requests`

## Installation

1. Install Ollama from [https://ollama.ai](https://ollama.ai)
2. Pull the required model:
   ```bash
   ollama pull llama3.1:8b-instruct-q4_K_M
   ```
3. Install Python dependencies:
   ```bash
   pip install pandas requests
   ```

## Usage

### Command Line

```bash
python ollamaDescriptionOptimizer.py <input_csv> <output_csv>
```

**Example:**
```bash
python ollamaDescriptionOptimizer.py source.csv output.csv
```

### CSV Input Format

Your input CSV must contain columns with these keywords in their names:
- **URL**: Column containing the target URLs
- **Title**: Column with existing page titles
- **Keywords**: Column with comma-separated target keywords

Example CSV structure:
```csv
URL,Existing Title,Top 5 Keywords
https://example.com/page1,Current Page Title,keyword1, keyword2, keyword3
https://example.com/page2,Another Title,seo, optimization, tools
```

### Output

The tool generates a new CSV with an additional column `Generated Meta Descriptions` containing 5 optimized meta description options for each URL, separated by line breaks.

## Configuration

### Model Selection
By default, the tool uses `llama3.1:8b-instruct-q4_K_M`. You can modify the model in the code:

```python
generator = SEOMetaGenerator(model_name="your-preferred-model")
```

### Ollama URL
If Ollama is running on a different host/port:

```python
generator = SEOMetaGenerator(ollama_url="http://your-host:port")
```

## Generated Meta Description Features

- **Length Optimization**: 130-160 characters for optimal SERP display
- **CTR Focus**: Includes action words, urgency, and benefits
- **Call-to-Action**: Each description includes compelling CTAs
- **Power Words**: Uses proven conversion terms (free, best, ultimate, proven, instant)
- **Keyword Integration**: Naturally incorporates target keywords
- **URL Context**: Extracts additional context from URL structure

## Error Handling

The tool includes robust error handling:
- **Connection Issues**: Tests Ollama connectivity before processing
- **Timeout Protection**: Automatic retries with fallback generation
- **Model Warming**: Pre-warms the model for consistent performance
- **Fallback Descriptions**: Generates template-based descriptions if AI fails

## Performance

- **Processing Speed**: ~2-3 seconds per URL (includes 0.5s delay between requests)
- **Model Warm-up**: Initial 5-10 second warm-up period
- **Memory Usage**: Optimized for local processing with reasonable resource usage

## Troubleshooting

### Common Issues

1. **"Cannot connect to Ollama"**
   - Ensure Ollama is running: `ollama serve`
   - Check if the model is available: `ollama list`

2. **"Model not found"**
   - Pull the required model: `ollama pull llama3.1:8b-instruct-q4_K_M`

3. **"Could not find columns"**
   - Verify your CSV has columns containing 'URL', 'Title', and 'Keywords' in their names

### Debug Mode

For troubleshooting, you can add debug prints by modifying the verbose output in the script.

## Example Output

Input:
```csv
URL,Title,Keywords
https://example.com/seo-tools,Best SEO Tools,seo tools, optimization, ranking
```

Generated Meta Descriptions:
```
Discover the best SEO tools software and boost your rankings today. Get started with our free trial and see results fast!
Compare top-rated SEO optimization platforms for better search rankings. Expert reviews and free trials available now.
Ultimate SEO tools guide with proven strategies to improve your website rankings. Start optimizing today for free!
Get instant access to professional SEO tools and templates. Join thousands of users improving their search rankings.
Transform your website with powerful SEO tools that increase visibility and traffic. Try our platform free for 14 days!
```

## License

This tool is part of the SEOTools suite and follows the same licensing terms.