# Internal Linking Optimizer

A powerful tool for analyzing and optimizing internal linking structures of websites using NetworkX and PageRank algorithms.

## Features

- Builds a directed graph representation of website structure
- Calculates PageRank scores with custom weights based on link location
- Identifies orphaned content and authority leaks
- Generates specific linking recommendations
- Creates comprehensive Excel reports
- Optional graph visualization

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

The tool requires two input files from Screaming Frog:
1. `internal_all.csv` - Contains page metadata
2. `all_inlinks.csv` - Contains source, target, and anchor data

### Basic Usage

```bash
python src/internal_linking_optimizer.py \
    --internal-all path/to/internal_all.csv \
    --all-inlinks path/to/all_inlinks.csv \
    --output path/to/output.xlsx
```

### With Graph Visualization

```bash
python src/internal_linking_optimizer.py \
    --internal-all path/to/internal_all.csv \
    --all-inlinks path/to/all_inlinks.csv \
    --output path/to/output.xlsx \
    --visualize \
    --viz-output path/to/graph.png
```

## Output

The tool generates an Excel file with the following sheets:

1. `pagerank_analysis`: All pages with their calculated PageRank, inbound/outbound links, and importance metrics
2. `optimization_recommendations`: Specific linking recommendations with source URL, target URL, and suggested anchor text
3. `orphaned_content`: Pages with minimal inbound links that should be better integrated
4. `authority_leaks`: High-PageRank pages linking to low-value destinations

## How It Works

1. **Data Loading**: The tool loads and normalizes URLs from both input files
2. **Graph Building**: Creates a directed graph using NetworkX
3. **PageRank Calculation**: Computes PageRank scores with custom weights based on link location
4. **Analysis**: Identifies orphaned content and authority leaks
5. **Recommendations**: Generates specific linking recommendations
6. **Reporting**: Creates comprehensive Excel reports

## Customization

You can modify the following parameters in the code:
- `min_inlinks`: Minimum number of inbound links to consider a page non-orphaned
- `pagerank_threshold`: Threshold for identifying authority pages
- Link location weights in the `calculate_pagerank` method

## Notes

- Only pages with 200 status code are included in the analysis
- URLs are normalized (trailing slashes removed, converted to lowercase)
- The tool uses `pagerank_scipy` for better performance with large graphs
- Progress is reported for long-running operations 