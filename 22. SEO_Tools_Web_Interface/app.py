#!/usr/bin/env python3
"""
SEO Tools Web Interface
A unified web interface for all SEO tools with configuration management
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
import subprocess
import os
import json
import yaml
from datetime import datetime
import tempfile
import shutil
import glob
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'seo-tools-secret-key-change-in-production'

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'web_interface', 'uploads')
CONFIG_FILE = os.path.join(BASE_DIR, 'web_interface', 'config.json')

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Tool definitions with their parameters
TOOLS = {
    'all_hands_report': {
        'name': 'All Hands Report Generator',
        'description': 'Generate comprehensive SEO performance reports combining GSC and GA4 data',
        'script': 'All_hands_report/all_hands_report.py',
        'parameters': {
            'site_url': {'type': 'text', 'label': 'Site URL', 'required': True, 'default': 'https://www.example.com/', 'placeholder': 'https://www.example.com/'},
            'ga_property_id': {'type': 'text', 'label': 'GA4 Property ID', 'required': True, 'default': '', 'placeholder': 'YOUR_PROPERTY_ID'},
            'credentials': {'type': 'file', 'label': 'Google Service Account JSON', 'required': True, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'},
            'start_date': {'type': 'date', 'label': 'Start Date', 'required': True},
            'end_date': {'type': 'date', 'label': 'End Date', 'required': True},
            'output': {'type': 'text', 'label': 'Output File Path', 'required': False, 'default': 'SEOTools/All_hands_report/monthly_report.xlsx', 'placeholder': 'SEOTools/All_hands_report/monthly_report.xlsx'}
        }
    },
    'ga4_traffic_analyzer': {
        'name': 'GA4 Traffic Analyzer',
        'description': 'Compare traffic between two periods using GA4 data',
        'script': 'GA4TrafficAnalyzer/GA4TrafficAnalyzer.py',
        'parameters': {
            'property_id': {'type': 'text', 'label': 'GA4 Property ID', 'required': True, 'default': '', 'placeholder': 'YOUR_PROPERTY_ID'},
            'credentials': {'type': 'file', 'label': 'Service Account JSON', 'required': True, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'},
            'start1': {'type': 'date', 'label': 'Period 1 Start Date', 'required': True},
            'end1': {'type': 'date', 'label': 'Period 1 End Date', 'required': True},
            'start2': {'type': 'date', 'label': 'Period 2 Start Date', 'required': True},
            'end2': {'type': 'date', 'label': 'Period 2 End Date', 'required': True},
            'channels': {'type': 'multiselect', 'label': 'Traffic Channels', 'required': False, 'default': ['Direct', 'Organic Search', 'Paid Search'],
                        'options': ['Direct', 'Organic Search', 'Paid Search', 'Social', 'Email', 'Referral', 'Display', 'Video']},
            'output': {'type': 'text', 'label': 'Output Base Name', 'required': False, 'default': 'traffic_drop_analysis', 'placeholder': 'traffic_drop_analysis'}
        }
    },
    'gsc_indexer': {
        'name': 'Google Indexing API Tool',
        'description': 'Submit URLs to Google for faster indexing using the Indexing API',
        'script': 'GSCIndexer/indexer.py',
        'parameters': {
            'service_account_file': {'type': 'file', 'label': 'Service Account JSON', 'required': True, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'},
            'urls': {'type': 'textarea', 'label': 'URLs to Index (one per line)', 'required': True, 'placeholder': 'https://www.example.com/page1\nhttps://www.example.com/page2', 'help': 'Note: Rate limits: max 200 URLs/day, max 600 URLs/month'},
            'action': {'type': 'select', 'label': 'Action', 'required': True, 'options': ['URL_UPDATED', 'URL_DELETED'], 'default': 'URL_UPDATED'}
        }
    },
    'indexation_monitor': {
        'name': 'Website Indexation Monitor',
        'description': 'Monitor your website for indexation issues and noindex directives',
        'script': 'IndexationMonitor/indexation_monitor.py',
        'parameters': {
            'base_url': {'type': 'text', 'label': 'Base URL', 'required': True, 'default': 'https://example.com', 'placeholder': 'https://example.com'},
            'sitemap_urls': {'type': 'textarea', 'label': 'Sitemap URLs (one per line)', 'required': True,
                           'default': 'https://example.com/sitemap.xml',
                           'placeholder': 'https://example.com/sitemap.xml'},
            'interactive': {'type': 'checkbox', 'label': 'Interactive Mode', 'required': False, 'help': 'Enable to approve noindex URLs interactively'}
        }
    },
    'internal_linking': {
        'name': 'Internal Linking Optimizer',
        'description': 'Analyze and optimize internal linking using PageRank algorithms',
        'script': 'InternalLinkingTool/src/internal_linking_optimizer.py',
        'parameters': {
            'internal_all': {'type': 'file', 'label': 'Internal All CSV (from Screaming Frog)', 'required': True, 'accept': '.csv', 'default': 'SEOTools/InternalLinkingTool/data/internal_all.csv'},
            'all_inlinks': {'type': 'file', 'label': 'All Inlinks CSV (from Screaming Frog)', 'required': True, 'accept': '.csv', 'default': 'SEOTools/InternalLinkingTool/data/all_inlinks.csv'},
            'output': {'type': 'text', 'label': 'Output Excel File', 'required': False, 'default': 'SEOTools/InternalLinkingTool/output/analysis.xlsx', 'placeholder': 'SEOTools/InternalLinkingTool/output/analysis.xlsx'},
            'visualize': {'type': 'checkbox', 'label': 'Generate Graph Visualization', 'required': False},
            'viz_output': {'type': 'text', 'label': 'Visualization Output', 'required': False, 'placeholder': 'graph.png'}
        }
    },
    'pruning_tool': {
        'name': 'Content Pruning Tool',
        'description': 'Identify underperforming content for pruning or improvement',
        'script': 'PruningTool/main.py',
        'parameters': {
            'crawl_file': {'type': 'file', 'label': 'Crawl Data File', 'required': True, 'accept': '.csv,.xlsx', 'placeholder': 'your_crawl_export.csv'},
            'site_url': {'type': 'text', 'label': 'GSC Site URL', 'required': False, 'default': 'https://www.example.com/', 'placeholder': 'https://www.example.com/'},
            'ga_property_id': {'type': 'text', 'label': 'GA4 Property ID', 'required': False, 'default': '', 'placeholder': 'YOUR_PROPERTY_ID'},
            'gsc_credentials': {'type': 'file', 'label': 'GSC Credentials JSON', 'required': False, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'},
            'ga_credentials': {'type': 'file', 'label': 'GA Credentials JSON', 'required': False, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'},
            'days_back': {'type': 'number', 'label': 'Days Back', 'required': False, 'default': 90, 'min': 1, 'max': 365},
            'output': {'type': 'text', 'label': 'Output File', 'required': False, 'default': 'SEOTools/PruningTool/Reports/content_pruning_analysis.csv', 'placeholder': 'SEOTools/PruningTool/Reports/content_pruning_analysis.csv'}
        }
    },
    'seo_auto_qa': {
        'name': 'SEO Auto QA',
        'description': 'Automated SEO quality assurance testing for website changes',
        'script': 'SEOAutoQA/cli.py',
        'parameters': {
            'action': {'type': 'select', 'label': 'Action', 'required': True, 'options': ['baseline', 'compare', 'history'], 'default': 'compare'},
            'url': {'type': 'text', 'label': 'URL to Monitor', 'required': False, 'default': 'https://www.example.com/', 'placeholder': 'https://www.example.com/'},
            'format': {'type': 'select', 'label': 'Output Format', 'required': False, 'options': ['json', 'html'], 'default': 'html'},
            'days': {'type': 'number', 'label': 'History Days', 'required': False, 'default': 7, 'min': 1, 'max': 90},
            'config': {'type': 'text', 'label': 'Config File', 'required': False, 'default': 'SEOTools/SEOAutoQA/config.yaml', 'placeholder': 'SEOTools/SEOAutoQA/config.yaml'}
        }
    },
    'seo_content_optimizer': {
        'name': 'SEO Content Optimizer',
        'description': 'AI-powered content optimization using GPT analysis',
        'script': 'SEOContentOptimizer/main.py',
        'parameters': {
            'target_url': {'type': 'text', 'label': 'Target URL', 'required': True, 'default': 'https://www.example.com/sample-page', 'placeholder': 'https://www.example.com/sample-page'},
            'competitor_urls': {'type': 'textarea', 'label': 'Competitor URLs (one per line)', 'required': False, 
                               'default': 'https://www.canva.com/presentations/templates/pitch-deck/',
                               'placeholder': 'https://www.canva.com/presentations/templates/pitch-deck/'},
            'serp_features': {'type': 'text', 'label': 'SERP Features', 'required': False, 'placeholder': 'Featured Snippets, People Also Ask'},
            'gpt_model': {'type': 'select', 'label': 'GPT Model', 'required': False, 'options': ['gpt-3.5-turbo', 'gpt-4'], 'default': 'gpt-3.5-turbo'},
            'openai_api_key': {'type': 'password', 'label': 'OpenAI API Key', 'required': True, 'help': 'Required: Set in .env file or enter here'}
        }
    },
    'seo_meta_analyzer': {
        'name': 'SEO Meta Analyzer',
        'description': 'Analyze and optimize SEO elements using AI',
        'script': 'SEOMetaAnalyzer/seo_analyzer.py',
        'parameters': {
            'input': {'type': 'file', 'label': 'Input CSV/Excel File', 'required': True, 'accept': '.csv,.xlsx'},
            'api_key': {'type': 'password', 'label': 'DeepSeek API Key', 'required': False},
            'output': {'type': 'text', 'label': 'Output File', 'required': False, 'placeholder': 'seo_analysis.csv'},
            'limit': {'type': 'number', 'label': 'Limit Rows', 'required': False, 'min': 1, 'max': 10000},
            'skip_api': {'type': 'checkbox', 'label': 'Skip API Calls (Test Mode)', 'required': False},
            'resume': {'type': 'checkbox', 'label': 'Resume from Checkpoint', 'required': False}
        }
    },
    'seo_perf_optimizer': {
        'name': 'SEO Performance Optimizer',
        'description': 'Identify SEO opportunities from GSC data and Screaming Frog crawls',
        'script': 'SEOPerfOptimizer/src/main.py',
        'parameters': {
            'site_url': {'type': 'text', 'label': 'Site URL', 'required': True, 'default': 'https://www.example.com/', 'placeholder': 'https://www.example.com/'},
            'screaming_frog_file': {'type': 'file', 'label': 'Screaming Frog Export CSV', 'required': False, 'accept': '.csv', 'default': 'SEOTools/SEOPerfOptimizer/data/inputs/screaming_frog_export.csv'},
            'min_impressions': {'type': 'number', 'label': 'Minimum Impressions', 'required': False, 'default': 100, 'min': 1},
            'ctr_threshold': {'type': 'number', 'label': 'CTR Underperformance Ratio', 'required': False, 'default': 0.7, 'min': 0.1, 'max': 1.0, 'step': 0.1},
            'credentials': {'type': 'file', 'label': 'GSC Credentials JSON', 'required': False, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'}
        }
    },
    'url_comparison': {
        'name': 'URL Comparison Tool',
        'description': 'Compare URL performance between GSC and GA4 data',
        'script': 'URLcomparison/URLcomparison.py',
        'parameters': {
            'urls_file': {'type': 'file', 'label': 'URLs CSV File', 'required': True, 'accept': '.csv', 'default': 'SEOTools/URLcomparison/urls.csv'},
            'site_url': {'type': 'text', 'label': 'GSC Site URL', 'required': True, 'default': 'https://www.storydoc.com/', 'placeholder': 'https://www.storydoc.com/'},
            'ga_property_id': {'type': 'text', 'label': 'GA4 Property ID', 'required': True, 'default': '', 'placeholder': 'YOUR_PROPERTY_ID'},
            'credentials': {'type': 'file', 'label': 'Service Account JSON', 'required': True, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'},
            'period1_start': {'type': 'date', 'label': 'Period 1 Start', 'required': True},
            'period1_end': {'type': 'date', 'label': 'Period 1 End', 'required': True},
            'period2_start': {'type': 'date', 'label': 'Period 2 Start', 'required': True},
            'period2_end': {'type': 'date', 'label': 'Period 2 End', 'required': True},
            'gsc_output': {'type': 'text', 'label': 'GSC Output File', 'required': False, 'default': 'SEOTools/URLcomparison/gsc_comparison.csv', 'placeholder': 'SEOTools/URLcomparison/gsc_comparison.csv'},
            'ga_output': {'type': 'text', 'label': 'GA Output File', 'required': False, 'default': 'SEOTools/URLcomparison/ga4_comparison.csv', 'placeholder': 'SEOTools/URLcomparison/ga4_comparison.csv'}
        }
    },
    'gsc_analyzer': {
        'name': 'GSC Analyzer',
        'description': 'Comprehensive Google Search Console data analysis and reporting',
        'script': 'gsc-analyzer/main.py',
        'parameters': {
            'force_refresh': {'type': 'checkbox', 'label': 'Force Refresh Historical Data', 'required': False, 'default': True},
            'auto_yes': {'type': 'checkbox', 'label': 'Auto-answer Yes to Prompts', 'required': False, 'default': True},
            'skip_historical': {'type': 'checkbox', 'label': 'Skip Historical Analysis', 'required': False, 'default': True},
            'output_dir': {'type': 'text', 'label': 'Output Directory', 'required': False, 'default': 'SEOTools/gsc-analyzer/reports', 'placeholder': 'SEOTools/gsc-analyzer/reports'}
        }
    },
    'sitemap_index_status': {
        'name': 'Sitemap Index Status Checker',
        'description': 'Check the indexing status of URLs from XML sitemaps using Google Search Console API',
        'script': 'SitemapIndexStatus/SitemapIndexStatus.py',
        'parameters': {
            'site': {'type': 'text', 'label': 'GSC Site Property', 'required': True, 'default': 'https://www.example.com/', 'placeholder': 'https://www.example.com/ or sc-domain:example.com'},
            'sitemaps': {'type': 'textarea', 'label': 'Sitemap URLs (one per line)', 'required': True,
                        'default': 'https://www.example.com/sitemap.xml',
                        'placeholder': 'https://www.example.com/sitemap.xml'},
            'credentials': {'type': 'file', 'label': 'GSC Service Account JSON', 'required': True, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'},
            'output': {'type': 'text', 'label': 'Output CSV File Path', 'required': False, 'default': 'SEOTools/SitemapIndexStatus/report.csv', 'placeholder': 'SEOTools/SitemapIndexStatus/report.csv'},
            'quiet': {'type': 'checkbox', 'label': 'Quiet Mode (Reduce Verbose Output)', 'required': False}
        }
    },
    'ollama_description_optimizer': {
        'name': 'Ollama Description Optimizer',
        'description': 'AI-powered SEO meta description generator using local Ollama LLM',
        'script': 'ollamaDescriptionOptimizer/ollamaDescriptionOptimizer.py',
        'parameters': {
            'input_csv': {'type': 'file', 'label': 'Input CSV File', 'required': True, 'accept': '.csv', 
                         'default': 'SEOTools/ollamaDescriptionOptimizer/source.csv',
                         'placeholder': 'CSV with URL, Title, and Keywords columns'},
            'output_csv': {'type': 'text', 'label': 'Output CSV File Path', 'required': False, 'default': 'SEOTools/ollamaDescriptionOptimizer/optimized_descriptions.csv', 'placeholder': 'SEOTools/ollamaDescriptionOptimizer/optimized_descriptions.csv'},
            'model_name': {'type': 'text', 'label': 'Ollama Model Name', 'required': False, 'default': 'llama3.1:8b-instruct-q4_K_M', 
                          'placeholder': 'llama3.1:8b-instruct-q4_K_M'},
            'ollama_url': {'type': 'text', 'label': 'Ollama Server URL', 'required': False, 'default': 'http://localhost:11434', 
                          'placeholder': 'http://localhost:11434', 'help': 'Requires Ollama running locally with the specified model installed'}
        }
    },
    'ollama_title_optimizer': {
        'name': 'Ollama Title Optimizer',
        'description': 'AI-powered SEO title generator using local Ollama LLM with precise character length control',
        'script': 'ollamaTitleOptimizer/ollamaTitleOptimizer.py',
        'parameters': {
            'input_csv': {'type': 'file', 'label': 'Input CSV File', 'required': True, 'accept': '.csv', 
                         'default': 'SEOTools/ollamaTitleOptimizer/source.csv',
                         'placeholder': 'CSV with URL, Title, and Keywords columns'},
            'output_csv': {'type': 'text', 'label': 'Output CSV File Path', 'required': False, 'default': 'SEOTools/ollamaTitleOptimizer/optimized_titles.csv', 'placeholder': 'SEOTools/ollamaTitleOptimizer/optimized_titles.csv'},
            'model_name': {'type': 'text', 'label': 'Ollama Model Name', 'required': False, 'default': 'llama3.1:8b-instruct-q4_K_M', 
                          'placeholder': 'llama3.1:8b-instruct-q4_K_M'},
            'ollama_url': {'type': 'text', 'label': 'Ollama Server URL', 'required': False, 'default': 'http://localhost:11434', 
                          'placeholder': 'http://localhost:11434', 'help': 'Requires Ollama running locally with the specified model installed'}
        }
    },
    'blog_performance': {
        'name': 'Blog Performance Analyzer',
        'description': 'Comprehensive blog post performance analysis using GSC and GA4 data with manual URL source',
        'script': 'BlogPerformance/main.py',
        'parameters': {
            'site_url': {'type': 'text', 'label': 'Site URL', 'required': True, 'default': 'https://www.example.com/', 'placeholder': 'https://www.example.com/'},
            'ga_property_id': {'type': 'text', 'label': 'GA4 Property ID', 'required': True, 'default': '', 'placeholder': 'YOUR_PROPERTY_ID'},
            'credentials': {'type': 'file', 'label': 'Service Account JSON', 'required': True, 'accept': '.json', 'default': 'SEOTools/gsc-analyzer/service_account.json'},
            'source_file': {'type': 'file', 'label': 'Source URLs CSV', 'required': True, 'accept': '.csv', 
                           'help': 'CSV file with blog URLs (exported from Screaming Frog or manually created)'},
            'days_back': {'type': 'number', 'label': 'Days Back', 'required': False, 'default': 90, 'min': 1, 'max': 365},
            'output': {'type': 'text', 'label': 'Output Excel File', 'required': False, 'placeholder': 'blog_performance_analysis.xlsx'}
        }
    },
    'csv_merger': {
        'name': 'CSV Merger Tool',
        'description': 'Merge multiple CSV files from a directory into a single consolidated file',
        'script': 'CSVMerger/merge_csvs.py',
        'parameters': {
            'input_dir': {'type': 'text', 'label': 'Input Directory', 'required': True, 'default': '/Users/timothea/Documents/Project1/CSVs', 'placeholder': '/path/to/csv/directory'},
            'output_file': {'type': 'text', 'label': 'Output File', 'required': True, 'default': 'merged_output.csv', 'placeholder': 'merged_output.csv'},
            'pattern': {'type': 'text', 'label': 'File Pattern', 'required': False, 'default': '*.csv', 'placeholder': '*.csv', 'help': 'Pattern to match CSV files (e.g., *.csv, data_*.csv)'}
        }
    },
    'seo_analyzer': {
        'name': 'SEO Analyzer',
        'description': 'Advanced SEO analysis tool with AI-powered insights using DeepSeek API',
        'script': 'SEO Analyzer/seo_analyzer.py',
        'parameters': {
            'input': {'type': 'file', 'label': 'Input CSV File', 'required': True, 'accept': '.csv', 'placeholder': 'your_input_file.csv'},
            'output': {'type': 'text', 'label': 'Output File', 'required': False, 'default': 'SEOTools/SEO Analyzer/output_results.csv', 'placeholder': 'SEOTools/SEO Analyzer/output_results.csv'},
            'api_key': {'type': 'password', 'label': 'DeepSeek API Key', 'required': False, 'placeholder': 'YOUR_DEEPSEEK_API_KEY'},
            'limit': {'type': 'number', 'label': 'Limit Rows', 'required': False, 'default': 100, 'min': 1, 'max': 10000},
            'resume': {'type': 'checkbox', 'label': 'Resume from Checkpoint', 'required': False, 'default': True},
            'skip_api': {'type': 'checkbox', 'label': 'Skip API Calls (Demo Mode)', 'required': False},
            'debug': {'type': 'checkbox', 'label': 'Enable Debug Mode', 'required': False}
        }
    },
    'ai_visibility_auditor': {
        'name': 'AI Visibility Auditor',
        'description': 'Analyze how well webpage content is visible to AI search mechanisms using multiple AI providers',
        'script': 'AI_Visibility_Auditor/ai_visibility_auditor.py',
        'parameters': {
            'provider': {'type': 'select', 'label': 'AI Provider', 'required': True, 'options': ['ollama', 'deepseek', 'openai', 'gemini'], 'default': 'deepseek'},
            'model': {'type': 'text', 'label': 'Model Name', 'required': False, 'placeholder': 'e.g., llama3.2, deepseek-chat, gpt-4o-mini, gemini-1.5-flash'},
            'url': {'type': 'text', 'label': 'URL to Audit', 'required': True, 'placeholder': 'https://www.example.com/your-page'},
            'queries': {'type': 'number', 'label': 'Number of Synthetic Queries', 'required': False, 'default': 10, 'min': 3, 'max': 20},
            'threshold': {'type': 'number', 'label': 'Coverage Threshold', 'required': False, 'default': 0.75, 'min': 0.1, 'max': 1.0, 'step': 0.05, 'help': 'Similarity threshold for query coverage (0.1-1.0)'},
            'api_key': {'type': 'password', 'label': 'API Key (if needed)', 'required': False, 'help': 'Required for OpenAI, Gemini, or DeepSeek. Not needed for Ollama.'}
        }
    }
}

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_tool_icon(tool_id):
    """Get icon for tool"""
    icon_map = {
        'all_hands_report': 'chart-bar',
        'ga4_traffic_analyzer': 'analytics',
        'gsc_indexer': 'search',
        'indexation_monitor': 'eye',
        'internal_linking': 'link',
        'pruning_tool': 'cut',
        'seo_auto_qa': 'check-circle',
        'seo_content_optimizer': 'magic',
        'seo_meta_analyzer': 'tags',
        'seo_perf_optimizer': 'tachometer-alt',
        'url_comparison': 'balance-scale',
        'gsc_analyzer': 'chart-line',
        'sitemap_index_status': 'sitemap',
        'ollama_description_optimizer': 'edit',
        'ollama_title_optimizer': 'heading',
        'blog_performance': 'blog',
        'csv_merger': 'table',
        'seo_analyzer': 'search-plus',
        'ai_visibility_auditor': 'robot'
    }
    return icon_map.get(tool_id, 'cog')

def get_param_icon(param_type):
    """Get icon for parameter type"""
    icon_map = {
        'text': 'keyboard',
        'file': 'file',
        'date': 'calendar',
        'number': 'hashtag',
        'select': 'list',
        'multiselect': 'list-ul',
        'checkbox': 'check-square',
        'textarea': 'edit',
        'password': 'key'
    }
    return icon_map.get(param_type, 'cog')

def get_file_icon(filename):
    """Get icon for file type"""
    ext = filename.split('.').pop().lower()
    icon_map = {
        'xlsx': 'file-excel',
        'xls': 'file-excel',
        'csv': 'file-csv',
        'json': 'file-code',
        'html': 'file-code',
        'txt': 'file-alt',
        'pdf': 'file-pdf',
        'png': 'file-image',
        'jpg': 'file-image',
        'jpeg': 'file-image'
    }
    return icon_map.get(ext, 'file')

def get_file_type(filename):
    """Get file type category"""
    ext = filename.split('.').pop().lower()
    if ext in ['xlsx', 'xls']:
        return 'excel'
    elif ext == 'csv':
        return 'csv'
    elif ext in ['html', 'txt', 'json']:
        return 'reports'
    return 'other'

def format_file_size(size):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def time_ago(dt):
    """Get human readable time ago"""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}m ago"
    else:
        return "Just now"

# Add template functions and filters
app.jinja_env.globals.update(
    get_tool_icon=get_tool_icon,
    get_param_icon=get_param_icon,
    get_file_icon=get_file_icon,
    get_file_type=get_file_type,
    format_file_size=format_file_size,
    time_ago=time_ago
)

# Add custom filters for templates
import re
app.jinja_env.filters['basename'] = os.path.basename

def regex_match(value, pattern):
    """Custom filter to match regex patterns"""
    return bool(re.match(pattern, value))

def get_length(value):
    """Custom filter to get length of any object"""
    try:
        return len(value)
    except (TypeError, AttributeError):
        return 0

app.jinja_env.filters['match'] = regex_match
app.jinja_env.filters['get_length'] = get_length

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html', tools=TOOLS)

@app.route('/tool/<tool_id>')
def tool_page(tool_id):
    """Individual tool configuration page"""
    if tool_id not in TOOLS:
        flash('Tool not found', 'error')
        return redirect(url_for('index'))
    
    tool = TOOLS[tool_id]
    config = load_config()
    saved_params = config.get(tool_id, {})
    
    return render_template('tool.html', 
                         tool_id=tool_id, 
                         tool=tool, 
                         saved_params=saved_params)

@app.route('/run/<tool_id>', methods=['POST'])
def run_tool(tool_id):
    """Execute a tool with provided parameters"""
    if tool_id not in TOOLS:
        return jsonify({'error': 'Tool not found'}), 404
    
    tool = TOOLS[tool_id]
    params = request.json
    
    # Save configuration
    config = load_config()
    config[tool_id] = params
    save_config(config)
    
    try:
        # Build command
        script_path = os.path.join(BASE_DIR, tool['script'])
        cmd = ['python', script_path]
        
        # Handle file uploads
        uploaded_files = {}
        for param_name, param_config in tool['parameters'].items():
            if param_config['type'] == 'file' and param_name in params:
                # File should be uploaded separately via /upload endpoint
                pass
        
        # Special handling for tools with specific argument patterns
        if tool_id in ['ollama_description_optimizer', 'ollama_title_optimizer']:
            # These tools expect: python script.py input_csv output_csv
            input_csv = params.get('input_csv', '')
            output_csv = params.get('output_csv', f'{tool_id}_output.csv')
            
            if input_csv:
                cmd.append(input_csv)
                cmd.append(output_csv)
            
            # Skip other parameters for now as these tools don't support them via command line
        elif tool_id == 'ai_visibility_auditor':
            # Handle AI Visibility Auditor arguments
            provider = params.get('provider', 'deepseek')
            model = params.get('model', '')
            url = params.get('url', '')
            queries = params.get('queries', 10)
            threshold = params.get('threshold', 0.75)
            api_key = params.get('api_key', '')
            
            # Add provider-specific arguments
            if provider == 'ollama' and model:
                cmd.extend(['--ollama', model])
            elif provider == 'deepseek':
                cmd.append('--deepseek')
            elif provider == 'openai':
                if model:
                    cmd.extend(['--openai', model])
                else:
                    cmd.append('--openai')
            elif provider == 'gemini':
                if model:
                    cmd.extend(['--gemini', model])
                else:
                    cmd.append('--gemini')
            
            # Add other parameters
            if url:
                cmd.extend(['--url', url])
            if queries:
                cmd.extend(['--queries', str(queries)])
            if threshold:
                cmd.extend(['--threshold', str(threshold)])
        else:
            # Add parameters to command for other tools
            for param_name, value in params.items():
                if value and param_name != 'csrf_token':
                    param_config = tool['parameters'].get(param_name, {})
                    
                    if param_config.get('type') == 'checkbox':
                        if value:
                            cmd.append(f'--{param_name.replace("_", "-")}')
                    elif param_config.get('type') == 'multiselect':
                        if isinstance(value, list):
                            for item in value:
                                cmd.extend([f'--{param_name.replace("_", "-")}', item])
                    elif param_name == 'sitemaps' and param_config.get('type') == 'textarea':
                        # Special handling for sitemap URLs - split by lines and add each as separate argument
                        sitemap_urls = [url.strip() for url in str(value).split('\n') if url.strip()]
                        if sitemap_urls:
                            cmd.append('--sitemaps')
                            cmd.extend(sitemap_urls)
                    else:
                        cmd.extend([f'--{param_name.replace("_", "-")}', str(value)])
        
        # Execute tool
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
        
        return jsonify({
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath
        })

@app.route('/config')
def config_page():
    """Configuration management page"""
    config = load_config()
    return render_template('config.html', config=config, tools=TOOLS)

@app.route('/config', methods=['POST'])
def save_global_config():
    """Save global configuration"""
    config = request.json
    save_config(config)
    return jsonify({'success': True})

@app.route('/results')
def results_page():
    """Results and downloads page"""
    results_dir = os.path.join(BASE_DIR, 'results')
    reports_dir = os.path.join(BASE_DIR, 'reports')
    
    files = []
    
    # Scan for result files in various tool directories
    for tool_id, tool in TOOLS.items():
        tool_dir = os.path.dirname(os.path.join(BASE_DIR, tool['script']))
        
        # Common result file patterns
        patterns = ['*.csv', '*.xlsx', '*.json', '*.txt', '*.html']
        
        # Special handling for AI Visibility Auditor with organized output folders
        if tool_id == 'ai_visibility_auditor':
            ai_vis_dir = os.path.join(BASE_DIR, 'AI_Visibility_Auditor')
            for subfolder in ['Json', 'Text']:
                subfolder_path = os.path.join(ai_vis_dir, subfolder)
                if os.path.exists(subfolder_path):
                    for pattern in patterns:
                        import glob
                        for file_path in glob.glob(os.path.join(subfolder_path, pattern)):
                            if os.path.isfile(file_path):
                                stat = os.stat(file_path)
                                files.append({
                                    'name': os.path.basename(file_path),
                                    'path': file_path,
                                    'tool': f"{tool['name']} ({subfolder})",
                                    'size': stat.st_size,
                                    'modified': datetime.fromtimestamp(stat.st_mtime)
                                })
        
        if os.path.exists(tool_dir):
            for pattern in patterns:
                import glob
                for file_path in glob.glob(os.path.join(tool_dir, pattern)):
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        files.append({
                            'name': os.path.basename(file_path),
                            'path': file_path,
                            'tool': tool['name'],
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime)
                        })
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template('results.html', files=files)

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download result files"""
    # Security: only allow downloading from specific directories
    safe_path = os.path.abspath(filename)
    base_path = os.path.abspath(BASE_DIR)
    
    if not safe_path.startswith(base_path):
        return jsonify({'error': 'Access denied'}), 403
    
    if os.path.exists(safe_path):
        return send_file(safe_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(os.path.join(BASE_DIR, 'web_interface', 'templates'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'web_interface', 'static'), exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)