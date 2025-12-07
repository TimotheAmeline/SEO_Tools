# GPT Translator

An intelligent web content translation tool that crawls web pages and translates content using OpenAI's GPT models.

## Features

- **Smart Resume**: Automatically resumes from where it left off if interrupted
- **Multiple Languages**: Add new languages as columns without overwriting existing translations
- **Progress Persistence**: Saves progress every 5 translations
- **URL-based Filenames**: CSV files named after the website being translated
- **Interactive Prompts**: Choose language and whether to refresh content
- **Enhanced Logging**: Colored console output with detailed progress tracking
- **Error Recovery**: Automatic retries with exponential backoff for API failures

## Setup

1. Install dependencies:
```bash
pip install requests beautifulsoup4 openai
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

## Usage

```bash
python GPTtranslator.py
```

Follow the prompts:
1. Enter the URL to translate
2. Enter target language code (e.g., 'fr', 'es', 'de')
3. Choose to refresh page content or use existing

## Output

- CSV file named after the domain (e.g., `example_com.csv`)
- Each language gets its own column
- Progress is automatically saved and can be resumed

## Language Codes

Common 2-letter language codes:
- `fr` - French
- `es` - Spanish  
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `ru` - Russian
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese