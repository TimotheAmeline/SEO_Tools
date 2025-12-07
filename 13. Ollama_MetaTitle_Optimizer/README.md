# Ollama Title Optimizer

An AI-powered SEO title generator that uses Ollama's local LLM to create optimized page titles for multiple URLs with precise character length control.

## Features

- **Local AI Processing**: Uses Ollama for privacy-focused, local LLM processing
- **Batch Processing**: Generate optimized titles for multiple URLs from CSV input
- **SEO Length Optimization**: Creates titles that are exactly 45-60 characters for optimal SERP display
- **Smart Context Extraction**: Automatically extracts keywords from URL structure
- **High CTR Focus**: Generates titles optimized for click-through rates
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
python ollamaTitleOptimizer.py <input_csv> <output_csv>
```

**Example:**
```bash
python ollamaTitleOptimizer.py source.csv output.csv
```

### CSV Input Format

Your input CSV must contain columns with these keywords in their names:
- **URL**: Column containing the target URLs
- **Title**: Column with existing page titles
- **Keywords**: Column with comma-separated target keywords

Example CSV structure:
```csv
URL,Current Title,Top 5 Keywords
https://example.com/page1,Current Page Title,keyword1, keyword2, keyword3
https://example.com/page2,Another Title,seo, optimization, tools
```

### Output

The tool generates a new CSV with an additional column `Generated Titles` containing 5 optimized title options for each URL, separated by line breaks.

## Configuration

### Model Selection
By default, the tool uses `llama3.1:8b-instruct-q4_K_M`. You can modify the model in the code:

```python
generator = SEOTitleGenerator(model_name="your-preferred-model")
```

### Ollama URL
If Ollama is running on a different host/port:

```python
generator = SEOTitleGenerator(ollama_url="http://your-host:port")
```

## Generated Title Features

- **Precise Length Control**: Exactly 45-60 characters for optimal SERP display
- **CTR Optimization**: High click-through rate focus with compelling language
- **Keyword Integration**: Naturally incorporates target keywords
- **No Fluff Words**: Eliminates unnecessary words to maximize impact
- **URL Context**: Extracts additional context from URL structure
- **Character Count Validation**: Strict adherence to SEO best practices

## Error Handling

The tool includes robust error handling:
- **Connection Issues**: Tests Ollama connectivity before processing
- **Timeout Protection**: Automatic retries with fallback generation
- **Model Warming**: Pre-warms the model for consistent performance
- **Length Validation**: Ensures all titles meet character requirements
- **Fallback Titles**: Generates template-based titles if AI fails

## Performance

- **Processing Speed**: ~2-3 seconds per URL (includes 0.5s delay between requests)
- **Model Warm-up**: Initial 5-10 second warm-up period
- **Memory Usage**: Optimized for local processing with reasonable resource usage
- **Character Accuracy**: Precise length control with intelligent truncation

## Troubleshooting

### Common Issues

1. **"Cannot connect to Ollama"**
   - Ensure Ollama is running: `ollama serve`
   - Check if the model is available: `ollama list`

2. **"Model not found"**
   - Pull the required model: `ollama pull llama3.1:8b-instruct-q4_K_M`

3. **"Could not find columns"**
   - Verify your CSV has columns containing 'URL', 'Title', and 'Keywords' in their names

4. **Titles too long/short**
   - The tool automatically validates and adjusts title lengths
   - Fallback titles are generated if length requirements can't be met

### Debug Mode

For troubleshooting, you can add debug prints by modifying the verbose output in the script.

## Example Output

Input:
```csv
URL,Title,Keywords
https://example.com/seo-tools,Best SEO Tools for Marketing,seo tools, optimization, ranking
```

Generated Titles:
```
Best SEO Tools Software for Teams in 2024
How to Choose the Right SEO Tools Platform
Top 10 SEO Tools Features You Need to Know
Ultimate SEO Tools Guide for Businesses
Why SEO Tools Matter: Complete Overview
```

## Length Optimization Details

The tool implements sophisticated length control:
- **Target Range**: 45-60 characters (Google's recommended title length)
- **Smart Truncation**: Cuts at word boundaries when needed
- **Padding Logic**: Extends short titles intelligently
- **Validation**: Multiple checks ensure optimal length

## Advanced Features

### URL Keyword Extraction
The tool analyzes URL structure to extract additional context:
- Domain name parsing
- Path segment analysis
- Camel case and hyphen splitting
- Automatic keyword detection

### Fallback Generation
When AI generation fails or produces unsuitable titles:
- Template-based title generation
- Keyword-focused alternatives
- Industry-standard formats
- Guaranteed length compliance

## License

This tool is part of the SEOTools suite and follows the same licensing terms.