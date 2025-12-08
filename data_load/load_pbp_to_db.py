"""
Load nflreadpy play-by-play data into SQLite database
Focuses on QB-relevant fields for analysis (2021-2025)
"""

import pandas as pd
import sqlite3
import nflreadpy
from datetime import datetime

# Database configuration
DB_PATH = "c:/Users/carme/NFL_QB_Project/data_load/nfl_qb_data.db"
TABLE_NAME = "play_by_play"
START_YEAR = 2010
END_YEAR = 2025

# Define QB-relevant columns to keep
QB_RELEVANT_COLUMNS = [
    # Game identifiers
    'play_id', 'game_id', 'old_game_id', 'season', 'week', 'season_type',
    'game_date', 'home_team', 'away_team', 'posteam', 'defteam',
    
    # Situational context
    'qtr', 'quarter_seconds_remaining', 'half_seconds_remaining', 
    'game_seconds_remaining', 'down', 'ydstogo', 'yardline_100', 
    'goal_to_go', 'drive', 'desc',
    
    # Score and game state
    'posteam_score', 'defteam_score', 'score_differential',
    'posteam_score_post', 'defteam_score_post', 'score_differential_post',
    
    # Play characteristics
    'play_type', 'yards_gained', 'shotgun', 'no_huddle', 
    'qb_dropback', 'qb_kneel', 'qb_spike', 'qb_scramble',
    
    # Pass-specific
    'pass_length', 'pass_location', 'air_yards', 'yards_after_catch',
    'complete_pass', 'incomplete_pass', 'pass_attempt', 'pass_touchdown',
    'interception', 'sack', 'qb_hit',
    
    # Rush-specific  
    'rush_attempt', 'rush_touchdown', 'run_location', 'run_gap',
    
    # Player identifiers
    'passer_player_id', 'passer_player_name', 'passing_yards',
    'receiver_player_id', 'receiver_player_name', 'receiving_yards',
    'rusher_player_id', 'rusher_player_name', 'rushing_yards',
    
    # Advanced metrics (EPA, WPA, CPOE)
    'epa', 'ep', 'air_epa', 'yac_epa', 'comp_air_epa', 'comp_yac_epa',
    'wpa', 'wp', 'def_wp', 'home_wp', 'away_wp',
    'air_wpa', 'yac_wpa', 'comp_air_wpa', 'comp_yac_wpa',
    'cp', 'cpoe',
    
    # Success and conversions
    'success', 'first_down', 'first_down_pass', 'first_down_rush',
    'third_down_converted', 'third_down_failed',
    'fourth_down_converted', 'fourth_down_failed',
    'two_point_attempt', 'two_point_conv_result',
    
    # Turnovers and pressure
    'fumble', 'fumble_lost', 'fumble_forced',
    'tackled_for_loss', 'qb_hit_1_player_id', 'qb_hit_2_player_id',
    
    # Penalties
    'penalty', 'penalty_team', 'penalty_type', 'penalty_yards',
    
    # Series and drive info
    'series', 'series_success', 'series_result',
    'drive_play_count', 'drive_time_of_possession', 'drive_first_downs',
    'drive_ended_with_score', 'drive_start_yard_line', 'drive_end_yard_line',
    
    # Expected yards after catch
    'xyac_epa', 'xyac_mean_yardage', 'xyac_median_yardage', 
    'xyac_success', 'xyac_fd',
    
    # Pass over expected
    'xpass', 'pass_oe',
    
    # Game conditions
    'roof', 'surface', 'temp', 'wind', 'stadium', 'location',
    'div_game', 'spread_line', 'total_line',
    
    # Additional identifiers for merging
    'passer_id', 'rusher_id', 'receiver_id',
    'passer', 'rusher', 'receiver',
    'name', 'id', 'fantasy_player_name', 'fantasy_player_id'
]

def load_pbp_data(start_year, end_year):
    """Load play-by-play data from nflreadpy for specified years"""
    print(f"\n{'='*60}")
    print(f"Loading play-by-play data from {start_year} to {end_year}")
    print(f"{'='*60}\n")
    
    pbp_list = []
    
    for year in range(start_year, end_year + 1):
        try:
            print(f"Loading {year} season... ", end='', flush=True)
            season_data = nflreadpy.load_pbp(year).to_pandas()
            
            # Filter to only QB-relevant columns (only keep columns that exist)
            available_cols = [col for col in QB_RELEVANT_COLUMNS if col in season_data.columns]
            missing_cols = [col for col in QB_RELEVANT_COLUMNS if col not in season_data.columns]
            
            if missing_cols:
                print(f"\n  [WARNING] Missing columns: {missing_cols[:5]}{'...' if len(missing_cols) > 5 else ''}")
            
            season_data = season_data[available_cols].copy()
            pbp_list.append(season_data)
            
            print(f"[OK] Loaded {len(season_data):,} plays")
            
        except Exception as e:
            print(f"[ERROR] Error loading {year}: {e}")
            continue
    
    if not pbp_list:
        raise ValueError("No data was loaded successfully")
    
    # Combine all seasons
    pbp = pd.concat(pbp_list, ignore_index=True)
    print(f"\n{'='*60}")
    print(f"Total plays loaded: {len(pbp):,}")
    print(f"Columns: {len(pbp.columns)}")
    print(f"{'='*60}\n")
    
    return pbp

def create_indexes(conn):
    """Create indexes for faster queries"""
    print("\nCreating database indexes...")
    
    indexes = [
        ("idx_passer_id", "passer_player_id"),
        ("idx_season_week", "season, week"),
        ("idx_game_id", "game_id"),
        ("idx_posteam", "posteam"),
        ("idx_play_type", "play_type"),
        ("idx_qb_dropback", "qb_dropback"),
        ("idx_passer_season", "passer_player_id, season"),
    ]
    
    cursor = conn.cursor()
    
    for idx_name, columns in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {TABLE_NAME} ({columns})")
            print(f"  [OK] Created index: {idx_name}")
        except Exception as e:
            print(f"  [ERROR] Error creating {idx_name}: {e}")
    
    conn.commit()
    print("Indexes created successfully!\n")

def load_to_database(pbp, db_path, table_name):
    """Load play-by-play data into SQLite database"""
    print(f"Loading data into database: {db_path}")
    print(f"Table: {table_name}\n")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    # Optimize SQLite for bulk insert
    conn.execute("PRAGMA synchronous = OFF;")
    conn.execute("PRAGMA journal_mode = MEMORY;")
    conn.execute("PRAGMA cache_size = 1000000;")
    
    # Load in chunks for memory efficiency
    chunk_size = 50000
    total_chunks = (len(pbp) + chunk_size - 1) // chunk_size
    
    print(f"Loading {len(pbp):,} rows in {total_chunks} chunks...")
    
    for i, start_idx in enumerate(range(0, len(pbp), chunk_size), 1):
        end_idx = min(start_idx + chunk_size, len(pbp))
        chunk = pbp.iloc[start_idx:end_idx]
        
        # First chunk replaces table, subsequent chunks append
        if_exists = 'replace' if i == 1 else 'append'
        
        chunk.to_sql(table_name, conn, if_exists=if_exists, index=False)
        
        print(f"  Chunk {i}/{total_chunks}: Loaded rows {start_idx:,} to {end_idx:,}")
    
    # Create indexes for better query performance
    create_indexes(conn)
    
    # Verify data
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT season) FROM {table_name}")
    season_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT passer_player_id) FROM {table_name} WHERE passer_player_id IS NOT NULL")
    qb_count = cursor.fetchone()[0]
    
    print(f"\n{'='*60}")
    print(f"DATABASE LOAD COMPLETE!")
    print(f"{'='*60}")
    print(f"Total rows: {row_count:,}")
    print(f"Seasons: {season_count}")
    print(f"Unique QBs: {qb_count:,}")
    print(f"{'='*60}\n")
    
    conn.close()

def print_sample_queries(db_path, table_name):
    """Print sample queries to verify data"""
    print("\n" + "="*60)
    print("SAMPLE QUERIES TO VERIFY DATA")
    print("="*60 + "\n")
    
    conn = sqlite3.connect(db_path)
    
    # Query 1: Top passers by EPA
    print("1. Top 10 QBs by total EPA (2024):")
    query = f"""
    SELECT 
        passer_player_name,
        COUNT(*) as plays,
        ROUND(SUM(epa), 2) as total_epa,
        ROUND(AVG(epa), 3) as epa_per_play,
        ROUND(AVG(cpoe) * 100, 1) as avg_cpoe
    FROM {table_name}
    WHERE season = 2024 
        AND qb_dropback = 1
        AND passer_player_name IS NOT NULL
    GROUP BY passer_player_name
    HAVING plays >= 100
    ORDER BY total_epa DESC
    LIMIT 10
    """
    df = pd.read_sql_query(query, conn)
    print(df.to_string(index=False))
    
    # Query 2: Play type distribution
    print("\n\n2. Play type distribution:")
    query = f"""
    SELECT 
        play_type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table_name}), 2) as percentage
    FROM {table_name}
    WHERE play_type IS NOT NULL
    GROUP BY play_type
    ORDER BY count DESC
    LIMIT 10
    """
    df = pd.read_sql_query(query, conn)
    print(df.to_string(index=False))
    
    # Query 3: Season summary
    print("\n\n3. Plays per season:")
    query = f"""
    SELECT 
        season,
        COUNT(*) as total_plays,
        COUNT(DISTINCT game_id) as games,
        SUM(CASE WHEN qb_dropback = 1 THEN 1 ELSE 0 END) as qb_dropbacks
    FROM {table_name}
    GROUP BY season
    ORDER BY season
    """
    df = pd.read_sql_query(query, conn)
    print(df.to_string(index=False))
    
    print("\n" + "="*60 + "\n")
    
    conn.close()

def main():
    """Main execution function"""
    start_time = datetime.now()
    
    print("\n" + "="*60)
    print("NFL QB PLAY-BY-PLAY DATA LOADER")
    print("="*60)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Years: {START_YEAR}-{END_YEAR}")
    print(f"Database: {DB_PATH}")
    print(f"Table: {TABLE_NAME}")
    print(f"Columns to load: {len(QB_RELEVANT_COLUMNS)}")
    print("="*60 + "\n")
    
    try:
        # Load data from nflreadpy
        pbp = load_pbp_data(START_YEAR, END_YEAR)
        
        # Load into database
        load_to_database(pbp, DB_PATH, TABLE_NAME)
        
        # Print sample queries
        print_sample_queries(DB_PATH, TABLE_NAME)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("="*60)
        print(f"COMPLETE! Duration: {duration:.1f} seconds")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
