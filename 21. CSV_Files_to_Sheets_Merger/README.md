# CSV Files to Sheets Merger

A simple Python utility to merge multiple CSV files from a directory into a single consolidated CSV file.

## Features

- Merges all CSV files in a specified directory
- Case-insensitive CSV file detection (.csv, .CSV, .CsV, etc.)
- Preserves headers from the first file
- Concatenates data while ignoring subsequent headers
- Detailed processing feedback with row counts
- Error handling for invalid or corrupted CSV files

## Requirements

```bash
pip install pandas
```

## Usage

### Basic Usage

1. Edit the configuration in `merge_csvs.py`:

```python
input_dir = "input_csvs"           # Directory containing CSV files
output_file = "merged_output.csv"  # Output file name
```

2. Run the script:

```bash
python merge_csvs.py
```

### Programmatic Usage

```python
from merge_csvs import merge_csv_files

# Merge all CSV files from a directory
merge_csv_files(
    input_directory="path/to/csv/files",
    output_file="merged_output.csv",
    keep_headers=True
)
```

## How It Works

1. **File Discovery**: Scans the input directory for all CSV files (case-insensitive)
2. **Data Loading**: Reads each CSV file into a pandas DataFrame
3. **Concatenation**: Combines all DataFrames into a single DataFrame
4. **Output**: Writes the merged data to the specified output file

## Example Output

```
Found 5 CSV files to merge
Processing 1/5: data_jan.csv - 1500 rows
Processing 2/5: data_feb.csv - 1800 rows
Processing 3/5: data_mar.csv - 2000 rows
Processing 4/5: data_apr.csv - 1700 rows
Processing 5/5: data_may.csv - 1900 rows

Successfully merged 5 files into merged_output.csv
Total rows in merged file: 8900
```

## Use Cases

- Consolidating monthly SEO reports
- Merging crawl data from multiple exports
- Combining split data files for analysis
- Aggregating CSV exports from different tools

## Error Handling

- Reports when no CSV files are found in the directory
- Lists directory contents if no CSVs detected
- Skips corrupted or invalid CSV files with error messages
- Continues processing remaining files if one fails

## Notes

- All CSV files must have the same column structure for proper merging
- The script preserves the order of columns from the first file
- Row indices are reset in the merged output (ignore_index=True)
- Original files are not modified
