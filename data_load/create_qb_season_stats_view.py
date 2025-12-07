"""
Create qb_season_stats view - Pre-aggregated season-level QB statistics
This view eliminates the need to aggregate play-by-play data in every notebook.
"""

import sqlite3

db_path = 'c:/Users/carme/NFL_QB_Project/data_load/nfl_qb_data.db'

# SQL to create pre-aggregated season stats view
create_view_sql = """
CREATE VIEW IF NOT EXISTS qb_season_stats AS
WITH 
-- Filter to QB plays with situational flags
qb_plays_flagged AS (
    SELECT 
        player_name,
        player_id,
        season,
        -- Play types
        qb_dropback,
        rush_attempt,
        complete_pass,
        incomplete_pass,
        -- Efficiency metrics
        epa,
        wpa,
        cpoe,
        success,
        -- Passing details
        air_yards,
        yards_after_catch,
        CASE WHEN complete_pass = 1 THEN COALESCE(air_yards, 0) + COALESCE(yards_after_catch, 0) ELSE 0 END AS passing_yards,
        pass_touchdown,
        interception,
        qb_hit,
        sack,
        qb_scramble,
        -- Rushing
        rushing_yards,
        rush_touchdown,
        -- Situational flags
        CASE WHEN down = 3 THEN 1 ELSE 0 END AS third_down,
        CASE WHEN yardline_100 <= 20 THEN 1 ELSE 0 END AS red_zone,
        CASE WHEN qtr = 4 AND ABS(score_differential) <= 8 THEN 1 ELSE 0 END AS late_close,
        CASE WHEN air_yards >= 20 THEN 1 ELSE 0 END AS deep_pass,
        CASE WHEN qb_hit = 1 OR sack = 1 OR qb_scramble = 1 THEN 1 ELSE 0 END AS under_pressure,
        CASE WHEN ABS(wpa) >= 0.1 THEN 1 ELSE 0 END AS high_leverage
    FROM qb_plays
),

-- Aggregate to season level
season_agg AS (
    SELECT 
        player_name,
        player_id,
        season,
        
        -- VOLUME METRICS
        SUM(qb_dropback) AS attempts,
        
        -- PASSING EFFICIENCY
        SUM(CASE WHEN qb_dropback = 1 THEN epa ELSE 0 END) AS total_pass_epa,
        AVG(CASE WHEN qb_dropback = 1 THEN success ELSE NULL END) AS pass_success_rate,
        AVG(cpoe) AS cpoe,
        CAST(SUM(complete_pass) AS FLOAT) / NULLIF(SUM(qb_dropback), 0) * 100 AS completion_pct,
        
        -- RUSHING EFFICIENCY
        AVG(CASE WHEN rush_attempt = 1 THEN epa ELSE NULL END) AS rush_epa_per_play,
        SUM(CASE WHEN rush_attempt = 1 THEN epa ELSE 0 END) AS total_rush_epa,
        AVG(CASE WHEN rush_attempt = 1 THEN success ELSE NULL END) AS rush_success_rate,
        
        -- SITUATIONAL EFFICIENCY
        AVG(CASE WHEN third_down = 1 THEN success ELSE NULL END) AS third_down_success,
        AVG(CASE WHEN red_zone = 1 THEN epa ELSE NULL END) AS red_zone_epa,
        AVG(CASE WHEN late_close = 1 THEN epa ELSE NULL END) AS late_close_epa,
        
        -- PRESSURE RESPONSE
        AVG(under_pressure) AS pressure_rate,
        AVG(CASE WHEN under_pressure = 1 THEN epa ELSE NULL END) AS epa_under_pressure,
        AVG(sack) AS sack_rate,
        
        -- BALL DISTRIBUTION
        AVG(air_yards) AS avg_air_yards,
        AVG(deep_pass) AS deep_pass_rate,
        AVG(yards_after_catch) AS avg_yac,
        
        -- DECISION MAKING
        AVG(interception) AS turnover_rate,
        AVG(pass_touchdown) AS td_rate,
        
        -- VOLUME STATS (per game)
        SUM(rush_attempt) AS rush_attempts,
        SUM(rushing_yards) / 17.0 AS rush_yards_per_game,
        SUM(passing_yards) / 17.0 AS pass_yards_per_game,
        (SUM(pass_touchdown) + SUM(rush_touchdown)) / 17.0 AS total_tds_per_game,
        
        -- CLUTCH/WPA
        SUM(wpa) AS total_wpa,
        AVG(CASE WHEN high_leverage = 1 THEN epa ELSE NULL END) AS high_leverage_epa
        
    FROM qb_plays_flagged
    GROUP BY player_name, player_id, season
)

-- Final view with NULL handling and Next Gen Stats join
SELECT 
    s.player_name,
    s.player_id,
    s.season,
    s.attempts,
    
    -- Passing metrics
    COALESCE(s.total_pass_epa, 0) AS total_pass_epa,
    COALESCE(s.pass_success_rate, 0) AS pass_success_rate,
    COALESCE(s.cpoe, 0) AS cpoe,
    COALESCE(s.completion_pct, 0) AS completion_pct,
    
    -- Next Gen Stats (NULL for seasons before 2016 when tracking started)
    CASE WHEN s.season >= 2016 THEN ngs.avg_time_to_throw ELSE NULL END AS avg_time_to_throw,
    
    -- Rushing metrics (set to 0 if <5 rush attempts)
    CASE WHEN s.rush_attempts >= 5 THEN COALESCE(s.rush_epa_per_play, 0) ELSE 0 END AS rush_epa_per_play,
    CASE WHEN s.rush_attempts >= 5 THEN COALESCE(s.total_rush_epa, 0) ELSE 0 END AS total_rush_epa,
    CASE WHEN s.rush_attempts >= 5 THEN COALESCE(s.rush_success_rate, 0) ELSE 0 END AS rush_success_rate,
    
    -- Situational metrics
    COALESCE(s.third_down_success, 0) AS third_down_success,
    COALESCE(s.red_zone_epa, 0) AS red_zone_epa,
    COALESCE(s.late_close_epa, 0) AS late_close_epa,
    
    -- Pressure metrics
    COALESCE(s.pressure_rate, 0) AS pressure_rate,
    COALESCE(s.epa_under_pressure, 0) AS epa_under_pressure,
    COALESCE(s.sack_rate, 0) AS sack_rate,
    
    -- Ball distribution
    COALESCE(s.avg_air_yards, 0) AS avg_air_yards,
    COALESCE(s.deep_pass_rate, 0) AS deep_pass_rate,
    COALESCE(s.avg_yac, 0) AS avg_yac,
    
    -- Decision making
    COALESCE(s.turnover_rate, 0) AS turnover_rate,
    COALESCE(s.td_rate, 0) AS td_rate,
    
    -- Volume stats (per game)
    COALESCE(s.rush_attempts, 0) AS rush_attempts,
    COALESCE(s.rush_yards_per_game, 0) AS rush_yards_per_game,
    COALESCE(s.pass_yards_per_game, 0) AS pass_yards_per_game,
    COALESCE(s.total_tds_per_game, 0) AS total_tds_per_game,
    
    -- Clutch metrics
    COALESCE(s.total_wpa, 0) AS total_wpa,
    COALESCE(s.high_leverage_epa, 0) AS high_leverage_epa

FROM season_agg s
LEFT JOIN next_gen_stats ngs 
    ON s.player_id = ngs.player_id 
    AND s.season = ngs.season 
    AND ngs.week = 0
WHERE s.attempts >= 225  -- Filter to meaningful sample sizes (roughly 13+ games started)
ORDER BY s.season DESC, s.total_pass_epa DESC;
"""

print("="*80)
print("Creating qb_season_stats view...")
print("="*80)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Drop existing view if it exists
cursor.execute("DROP VIEW IF EXISTS qb_season_stats")
print("✓ Dropped old view (if existed)")

# Create new view
cursor.execute(create_view_sql)
conn.commit()
print("✓ Created qb_season_stats view")

# Test the view
test_query = """
SELECT 
    COUNT(*) as total_qb_seasons,
    MIN(season) as first_season,
    MAX(season) as last_season,
    COUNT(DISTINCT player_name) as unique_qbs
FROM qb_season_stats
"""

result = cursor.execute(test_query).fetchone()
conn.close()

print("\n" + "="*80)
print("VALIDATION")
print("="*80)
print(f"Total QB-seasons: {result[0]:,}")
print(f"Seasons covered: {result[1]}-{result[2]}")
print(f"Unique QBs: {result[3]:,}")

print("\n" + "="*80)
print("✅ View created successfully!")
print("="*80)
print("\nNow you can query season-level stats with:")
print("  SELECT * FROM qb_season_stats")
print("\nThis replaces ~100 lines of Python aggregation code!")
print("="*80)
