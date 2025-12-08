"""
Initialize data for Streamlit Cloud deployment.
This script runs on first deployment to generate the database and ratings.
"""
import os
import sys
from pathlib import Path

def check_and_init_data():
    """Check if data exists, if not, generate it."""
    db_path = Path('data_load/nfl_qb_data.db')
    ratings_path = Path('Modeling/models/custom_qb_ratings.csv')
    
    if db_path.exists() and ratings_path.exists():
        print("Data already exists. Skipping initialization.")
        return True
    
    print("="*60)
    print("First-time setup: Generating NFL QB data...")
    print("This will take 5-10 minutes. Please wait...")
    print("="*60)
    
    try:
        # Step 1: Load play-by-play data
        print("\n[1/3] Fetching play-by-play data from nflfastR...")
        result = os.system(f"{sys.executable} data_load/load_pbp_to_db.py")
        if result != 0:
            print("ERROR: Failed to load play-by-play data")
            return False
        
        # Step 2: Create QB views
        print("\n[2/3] Creating QB statistics views...")
        result = os.system(f"{sys.executable} data_load/create_qb_season_stats_view.py")
        if result != 0:
            print("ERROR: Failed to create QB views")
            return False
        
        # Step 3: Generate ratings (using notebook execution)
        print("\n[3/3] Generating custom QB ratings...")
        try:
            import papermill as pm
            pm.execute_notebook(
                'Modeling/custom_qb_rating_system.ipynb',
                'Modeling/custom_qb_rating_system.ipynb',
                kernel_name='python3'
            )
        except ImportError:
            print("Papermill not available, trying direct notebook execution...")
            # Fallback: Try to run key cells manually
            print("ERROR: Cannot generate ratings without papermill")
            print("Installing papermill...")
            os.system(f"{sys.executable} -m pip install papermill")
            import papermill as pm
            pm.execute_notebook(
                'Modeling/custom_qb_rating_system.ipynb',
                'Modeling/custom_qb_rating_system.ipynb',
                kernel_name='python3'
            )
        
        print("\n" + "="*60)
        print("Setup complete! Starting application...")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\nERROR during setup: {e}")
        print("Please check the logs and try again.")
        return False

if __name__ == "__main__":
    success = check_and_init_data()
    sys.exit(0 if success else 1)
