# SEO Tools Web Interface

A unified web interface for all your SEO analysis and optimization tools. This dashboard provides easy access to 12 powerful SEO tools with a user-friendly configuration system and automated result management.

## Features

### 🎯 Unified Dashboard
- **One-Click Access**: Launch any of the 12 SEO tools from a single interface
- **Tool Overview**: See descriptions, parameter counts, and requirements at a glance
- **Progress Tracking**: Real-time status updates during tool execution

### ⚙️ Smart Configuration Management
- **Parameter Forms**: Dynamic forms for each tool with validation
- **Saved Configurations**: Automatically save and restore tool settings
- **File Upload Handling**: Secure file uploads for CSV, Excel, and JSON inputs
- **Configuration Import/Export**: Backup and share your settings

### 📊 Results Management
- **Centralized Downloads**: Access all generated reports from one location
- **File Organization**: Filter by file type (Excel, CSV, Reports)
- **File Preview**: Quick preview for text and HTML reports
- **Download Statistics**: Track your analysis history

### 🛠️ Available Tools

1. **All Hands Report Generator** - Comprehensive SEO performance reports (GSC + GA4)
2. **GA4 Traffic Analyzer** - Period-over-period traffic comparison
3. **Google Indexing API Tool** - Bulk URL submission for faster indexing
4. **Website Indexation Monitor** - Automated noindex detection and monitoring
5. **Internal Linking Optimizer** - PageRank-based linking analysis
6. **Content Pruning Tool** - Identify underperforming content for removal
7. **SEO Auto QA** - Automated SEO quality assurance testing
8. **SEO Content Optimizer** - AI-powered content optimization
9. **SEO Meta Analyzer** - Bulk SEO element analysis and optimization
10. **SEO Performance Optimizer** - GSC opportunity identification
11. **URL Comparison Tool** - Multi-period URL performance analysis
12. **GSC Analyzer** - Comprehensive Search Console data analysis

## Quick Start

### 1. Installation

```bash
# Navigate to the web interface directory
cd SEOTools/web_interface

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch the Interface

```bash
# Start the web server
python app.py
```

The interface will be available at `http://localhost:5000`

### 3. Configure Your First Tool

1. Click on any tool card from the dashboard
2. Fill in the required parameters (marked with *)
3. Upload any required files (credentials, data files)
4. Click "Run Analysis"
5. Download your results from the Results page

## Configuration Details

### Required Setup

Most tools require these common elements:

- **Google Service Account**: For GSC and GA4 API access
- **API Keys**: For AI-powered tools (OpenAI, DeepSeek)
- **Input Data**: CSV/Excel files from crawling tools like Screaming Frog

### Parameter Types

The interface handles various parameter types:

- **Text Fields**: URLs, property IDs, file paths
- **File Uploads**: Service account JSON, CSV data, Excel files
- **Date Pickers**: Start/end dates for analysis periods
- **Dropdowns**: Predefined options (models, actions, formats)
- **Multi-select**: Traffic channels, analysis options
- **Checkboxes**: Enable/disable features
- **Number Fields**: Thresholds, limits, day ranges

### File Management

- **Uploads**: Files are securely stored with timestamps
- **Results**: Generated reports are automatically detected
- **Downloads**: Direct download links for all outputs
- **Organization**: Files grouped by generating tool

## Advanced Features

### Configuration Management

- **Auto-Save**: Settings are automatically saved when you run tools
- **Export/Import**: Share configurations between environments
- **Validation**: Check for missing required parameters
- **Backup**: Create timestamped configuration backups

### Security

- **File Validation**: Only allowed file types can be uploaded
- **Secure Paths**: Files are restricted to safe directories
- **Input Sanitization**: All user inputs are properly escaped
- **Secret Handling**: API keys and credentials are protected

### Performance

- **Efficient Execution**: Tools run with proper Python environments
- **Progress Tracking**: Real-time feedback during analysis
- **Error Handling**: Comprehensive error reporting and logging
- **Resource Management**: Proper cleanup of temporary files

## Tool-Specific Guides

### Google APIs Setup

For tools requiring Google API access:

1. Create a Google Cloud Project
2. Enable Search Console API and/or Analytics Data API
3. Create a Service Account
4. Download the JSON credentials file
5. Add the service account email to your GSC/GA4 properties

### AI-Powered Tools

For tools using AI optimization:

1. Obtain API keys from OpenAI or DeepSeek
2. Set appropriate usage limits to control costs
3. Test with small datasets first
4. Review generated optimizations before implementation

### Data Export Tools

For tools requiring Screaming Frog or similar data:

1. Export the required data format (usually CSV)
2. Ensure column names match expected formats
3. Upload files through the web interface
4. Verify data quality before running analysis

## Troubleshooting

### Common Issues

**Tool Execution Fails**
- Check that all required parameters are filled
- Verify file uploads completed successfully
- Ensure API credentials have proper permissions

**File Upload Errors**
- Check file size limits (browser dependent)
- Verify file format matches expected type
- Ensure filename doesn't contain special characters

**API Authentication Errors**
- Verify service account has required API access
- Check that credentials file is valid JSON
- Ensure service account is added to relevant properties

**Missing Results**
- Check the tool's output directory for manual files
- Verify the tool completed successfully
- Look for error messages in the execution log

### Getting Help

1. Check tool-specific README files for detailed documentation
2. Review parameter descriptions and help text
3. Test with smaller datasets first
4. Verify all prerequisites are met

## Directory Structure

```
web_interface/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Dashboard with tool overview
│   ├── tool.html         # Individual tool configuration
│   ├── results.html      # Results and downloads
│   └── config.html       # Configuration management
├── uploads/              # Uploaded files storage
└── config.json          # Saved configurations
```

## Contributing

This interface is designed to be easily extensible:

1. **Adding New Tools**: Add tool definitions to the `TOOLS` dictionary in `app.py`
2. **Custom Parameters**: Define new parameter types and handlers
3. **Enhanced UI**: Modify templates for improved user experience
4. **Additional Features**: Extend the Flask app with new routes and functionality

## License

This web interface is part of the SEO Tools collection and follows the same licensing terms as the underlying tools.