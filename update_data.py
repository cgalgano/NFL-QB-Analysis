"""
Automated data update pipeline for NFL QB Analysis project.
Fetches latest nflfastR data, updates database, and regenerates ratings.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import sqlite3

def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_command(command, description):
    """Run a command and handle errors."""
    log(f"Starting: {description}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        log(f"[OK] Completed: {description}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"[ERROR] Failed: {description}")
        log(f"Error: {e.stderr}")
        return False

def update_timestamp():
    """Update the last_updated timestamp in database."""
    try:
        conn = sqlite3.connect('data_load/nfl_qb_data.db')
        cursor = conn.cursor()
        
        # Create metadata table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Update last refresh timestamp
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value, updated_at)
            VALUES ('last_data_refresh', ?, CURRENT_TIMESTAMP)
        """, (datetime.now().isoformat(),))
        
        conn.commit()
        conn.close()
        log("[OK] Updated metadata timestamp")
        return True
    except Exception as e:
        log(f"[ERROR] Failed to update timestamp: {e}")
        return False

def main():
    """Execute the full data update pipeline."""
    log("="*60)
    log("Starting NFL QB Data Update Pipeline")
    log("="*60)
    
    # Step 1: Update play-by-play data in database
    if not run_command(
        f"{sys.executable} data_load/load_pbp_to_db.py",
        "Fetching latest play-by-play data from nflfastR"
    ):
        log("Pipeline failed at data fetch step")
        return 1
    
    # Step 2: Update QB statistics views
    if not run_command(
        f"{sys.executable} data_load/create_qb_season_stats_view.py",
        "Updating QB season statistics view"
    ):
        log("Pipeline failed at stats view update")
        return 1
    
    # Step 3: Regenerate custom QB ratings
    log("Starting: Regenerating QB ratings (this may take a few minutes)")
    log("Note: This requires 'papermill' package. Installing if needed...")
    
    # First, try to install papermill if not present
    try:
        subprocess.run(
            ["uv", "add", "papermill"],
            check=False,  # Don't fail if already installed
            capture_output=True
        )
    except:
        pass
    
    try:
        import papermill as pm
        pm.execute_notebook(
            'Modeling/custom_qb_rating_system.ipynb',
            'Modeling/custom_qb_rating_system.ipynb',
            kernel_name='python3'
        )
        log("[OK] Completed: QB ratings regenerated")
    except ImportError:
        log("[ERROR] Failed: papermill not available")
        log("Please run: uv add papermill")
        log("Then re-run this script, or manually execute:")
        log("  Modeling/custom_qb_rating_system.ipynb")
        return 1
    except Exception as e:
        log(f"[ERROR] Failed: {e}")
        log("Please manually run the notebook: Modeling/custom_qb_rating_system.ipynb")
        return 1
    
    # Step 4: Update timestamp
    if not update_timestamp():
        log("Warning: Could not update timestamp, but data is refreshed")
    
    log("="*60)
    log("[OK] Pipeline completed successfully!")
    log("Your Streamlit app will now show the latest data")
    log("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
