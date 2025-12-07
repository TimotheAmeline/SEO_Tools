# setup_project.py
import os
import sys
from pathlib import Path

def setup_project():
    """Set up the project structure"""
    print("\n=== Setting up GSC Analyzer Project ===\n")
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    
    # Define necessary directories
    directories = [
        script_dir / "data",
        script_dir / "data/historical",
        script_dir / "data/recent",
        script_dir / "reports"
    ]
    
    # Create directories if they don't exist
    for directory in directories:
        if not directory.exists():
            print(f"Creating directory: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
        else:
            print(f"Directory already exists: {directory}")
    
    # Check for required files
    required_files = [
        (script_dir / "service_account.json", "Service account credentials"),
        (script_dir / "config.py", "Configuration file")
    ]
    
    for file_path, description in required_files:
        if file_path.exists():
            print(f"Found {description}: {file_path}")
        else:
            print(f"Warning: Missing {description}: {file_path}")
    
    print("\nProject setup complete!")

if __name__ == "__main__":
    setup_project()