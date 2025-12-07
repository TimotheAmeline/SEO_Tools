import os
import glob
import pandas as pd

def merge_csv_files(input_directory, output_file, keep_headers=True):
    """
    Merge all CSV files in a directory into a single CSV file.
    
    Parameters:
    input_directory (str): Path to directory containing CSV files
    output_file (str): Path to output the merged CSV file
    keep_headers (bool): If True, keep headers only for the first file
    """
    # Get all CSV files in the directory (case insensitive)
    csv_files = glob.glob(os.path.join(input_directory, '*.[cC][sS][vV]'))
    
    if not csv_files:
        print(f"No CSV files found in {input_directory}")
        print("Checking directory contents:")
        try:
            all_files = os.listdir(input_directory)
            if all_files:
                print(f"Found {len(all_files)} files in the directory:")
                for file in all_files[:10]:  # Show first 10 files
                    print(f"  - {file}")
                if len(all_files) > 10:
                    print(f"  ... and {len(all_files) - 10} more")
            else:
                print("The directory is empty.")
        except Exception as e:
            print(f"Error listing directory contents: {str(e)}")
        return
    
    print(f"Found {len(csv_files)} CSV files to merge")
    
    # Create a list to store each DataFrame
    all_df_list = []
    
    # Read each CSV file and add to the list
    for i, file in enumerate(csv_files):
        try:
            df = pd.read_csv(file)
            file_name = os.path.basename(file)
            print(f"Processing {i+1}/{len(csv_files)}: {file_name} - {len(df)} rows")
            all_df_list.append(df)
        except Exception as e:
            print(f"Error reading {file}: {str(e)}")
    
    if not all_df_list:
        print("No data frames to merge. Check if files are valid CSVs.")
        return
    
    # Concatenate all DataFrames
    merged_df = pd.concat(all_df_list, ignore_index=True)
    
    # Save to output file
    merged_df.to_csv(output_file, index=False)
    print(f"\nSuccessfully merged {len(csv_files)} files into {output_file}")
    print(f"Total rows in merged file: {len(merged_df)}")

if __name__ == "__main__":
    # You can change these values
    input_dir = "input_csvs"  # Replace with your directory containing CSVs
    output_file = "merged_output.csv"     # Name of the output file

    merge_csv_files(input_dir, output_file)