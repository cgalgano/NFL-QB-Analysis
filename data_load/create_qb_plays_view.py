"""
Create a SQL view in the database for QB play-by-play data with proper filtering.
This view handles the column naming complexity and filters to confirmed QBs only.
"""

import sqlite3

def create_qb_plays_view(db_path='c:/Users/carme/NFL_QB_Project/data_load/nfl_qb_data.db'):
    """
    Creates a view called 'qb_plays' that properly filters play-by-play data.
    
    The view:
    - Uses passer_player_name/rusher_player_name (NOT player_name)
    - Filters to QB dropbacks and rush attempts
    - Joins with qb_statistics to exclude trick plays by WRs/RBs
    - Includes all relevant columns for analysis
    """
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop view if it exists
    print("Dropping existing view if present...")
    cursor.execute("DROP VIEW IF EXISTS qb_plays")
    
    # Create the view
    print("Creating qb_plays view...")
    
    create_view_sql = """
    CREATE VIEW qb_plays AS
    SELECT 
        COALESCE(pbp.passer_player_name, pbp.rusher_player_name) as player_name,
        COALESCE(pbp.passer_player_id, pbp.rusher_player_id) as player_id,
        pbp.season, 
        pbp.week, 
        pbp.game_id, 
        pbp.posteam, 
        pbp.defteam,
        
        -- Core metrics
        pbp.epa, 
        pbp.wpa, 
        pbp.success,
        
        -- Play type indicators
        pbp.qb_dropback, 
        pbp.rush_attempt,
        
        -- Passing details
        pbp.cpoe, 
        pbp.air_yards, 
        pbp.yards_after_catch, 
        pbp.complete_pass, 
        pbp.incomplete_pass,
        pbp.pass_touchdown, 
        pbp.interception, 
        pbp.qb_hit, 
        pbp.sack, 
        pbp.qb_scramble,
        
        -- Rushing details
        pbp.rushing_yards, 
        pbp.rush_touchdown,
        
        -- Situational context
        pbp.down, 
        pbp.ydstogo, 
        pbp.yardline_100, 
        pbp.score_differential, 
        pbp.half_seconds_remaining, 
        pbp.qtr,
        
        -- Expected metrics
        pbp.xpass, 
        pbp.pass_oe, 
        pbp.xyac_epa,
        
        -- Pass characteristics
        pbp.pass_length, 
        pbp.pass_location
        
    FROM play_by_play pbp
    INNER JOIN (
        SELECT DISTINCT player_id 
        FROM qb_statistics 
        WHERE position = 'QB'
    ) qbs ON COALESCE(pbp.passer_player_id, pbp.rusher_player_id) = qbs.player_id
    WHERE (pbp.qb_dropback = 1 OR pbp.rush_attempt = 1)
        AND (pbp.passer_player_name IS NOT NULL OR pbp.rusher_player_name IS NOT NULL)
        AND pbp.season >= 2010
    """
    
    cursor.execute(create_view_sql)
    conn.commit()
    
    print("✓ View created successfully!")
    
    # Test the view
    print("\nTesting view with Lamar Jackson 2024...")
    test_query = """
    SELECT 
        player_name,
        COUNT(*) as total_plays,
        SUM(qb_dropback) as dropbacks,
        SUM(rush_attempt) as rush_attempts,
        SUM(complete_pass) as completions,
        SUM(rushing_yards) as rushing_yards
    FROM qb_plays
    WHERE player_name = 'L.Jackson' AND season = 2024
    GROUP BY player_name
    """
    
    result = cursor.execute(test_query).fetchone()
    
    if result:
        print(f"\nPlayer: {result[0]}")
        print(f"Total plays: {result[1]:,}")
        print(f"Dropbacks: {result[2]:,}")
        print(f"Rush attempts: {result[3]:,}")
        print(f"Completions: {result[4]:,}")
        print(f"Rushing yards: {result[5]:,.0f}")
        print("\n✓ View is working correctly!")
    else:
        print("\n✗ Test query returned no results")
    
    # Show total plays in view
    total_plays = cursor.execute("SELECT COUNT(*) FROM qb_plays").fetchone()[0]
    print(f"\nTotal plays in view: {total_plays:,}")
    
    conn.close()
    print("\n" + "="*80)
    print("SUCCESS! You can now use 'SELECT * FROM qb_plays' in your notebooks.")
    print("="*80)

if __name__ == '__main__':
    create_qb_plays_view()
