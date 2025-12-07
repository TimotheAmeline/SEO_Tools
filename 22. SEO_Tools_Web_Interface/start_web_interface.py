#!/usr/bin/env python3
"""
SEO Tools Web Interface Launcher
Easy launcher script for the web interface
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main launcher function"""
    # Get the directory of this script
    script_dir = Path(__file__).parent
    web_interface_dir = script_dir
    
    # Check if web interface directory exists
    if not web_interface_dir.exists():
        print("❌ Web interface directory not found!")
        print(f"Expected: {web_interface_dir}")
        return 1
    
    # Check if app.py exists
    app_file = web_interface_dir / "app.py"
    if not app_file.exists():
        print("❌ app.py not found in web interface directory!")
        return 1
    
    # Check if requirements are installed
    requirements_file = web_interface_dir / "requirements.txt"
    if requirements_file.exists():
        print("📦 Checking dependencies...")
        try:
            import flask
            print("✅ Flask is installed")
        except ImportError:
            print("❌ Flask not found. Installing requirements...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
                ])
                print("✅ Requirements installed successfully")
            except subprocess.CalledProcessError:
                print("❌ Failed to install requirements")
                print(f"Please run: pip install -r {requirements_file}")
                return 1
    
    # Start the web interface
    print("\n🚀 Starting SEO Tools Web Interface...")
    print("📍 Interface will be available at: http://localhost:5000")
    print("🔧 Available tools: 19 SEO analysis and optimization tools")
    print("\n💡 Tips:")
    print("   - Configure tools by clicking on tool cards")
    print("   - Upload required files (CSV, Excel, JSON)")
    print("   - Your configurations are automatically saved")
    print("   - Download results from the Results page")
    print("\n⏹️  Press Ctrl+C to stop the server\n")
    
    try:
        # Change to web interface directory and run the app
        os.chdir(web_interface_dir)
        subprocess.run([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n\n👋 SEO Tools Web Interface stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting web interface: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())