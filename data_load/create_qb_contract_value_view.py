"""
Create qb_contract_value view - Pre-aggregated contract value analysis
Combines QB season stats with contract data to analyze value vs performance.
"""

import sqlite3

db_path = 'c:/Users/carme/NFL_QB_Project/data_load/nfl_qb_data.db'

# SQL to create contract value view
create_view_sql = """
CREATE VIEW IF NOT EXISTS qb_contract_value AS
WITH
-- Expand contracts to all years they cover
contract_years AS (
    SELECT 
        pc.player_id,
        pc.player_name,
        pc.team,
        pc.year_signed,
        pc.year_signed + n.year_offset AS season,
        pc.apy,
        pc.value AS total_value,
        pc.guaranteed,
        pc.years AS contract_length,
        pc.is_active
    FROM player_contracts pc
    CROSS JOIN (
        SELECT 0 AS year_offset UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL 
        SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL 
        SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
    ) n
    WHERE pc.position = 'QB' 
      AND pc.apy IS NOT NULL 
      AND pc.apy > 0
      AND n.year_offset < pc.years  -- Only include years within contract length
),

-- Get QB season stats (using the view if it exists, otherwise aggregate from qb_plays)
qb_season_performance AS (
    SELECT 
        player_name,
        player_id,
        season,
        attempts,
        total_pass_epa,
        pass_success_rate,
        cpoe,
        completion_pct,
        td_rate,
        turnover_rate,
        total_rush_epa,
        rush_success_rate,
        total_wpa,
        red_zone_epa,
        late_close_epa,
        pressure_rate,
        epa_under_pressure
    FROM qb_season_stats
    WHERE attempts >= 100  -- Filter to meaningful sample sizes
),

-- Calculate custom rating from components
qb_ratings AS (
    SELECT 
        player_id,
        player_name,
        season,
        attempts,
        total_pass_epa,
        pass_success_rate,
        cpoe,
        completion_pct,
        td_rate,
        turnover_rate,
        total_rush_epa,
        total_wpa,
        
        -- Normalize EPA (most important factor)
        50 + 50 * (
            (total_pass_epa - MIN(total_pass_epa) OVER (PARTITION BY season)) / 
            NULLIF(MAX(total_pass_epa) OVER (PARTITION BY season) - MIN(total_pass_epa) OVER (PARTITION BY season), 0)
        ) AS epa_norm,
        
        -- Normalize success rate
        50 + 50 * (
            (pass_success_rate - MIN(pass_success_rate) OVER (PARTITION BY season)) / 
            NULLIF(MAX(pass_success_rate) OVER (PARTITION BY season) - MIN(pass_success_rate) OVER (PARTITION BY season), 0)
        ) AS success_norm,
        
        -- Normalize CPOE
        50 + 50 * (
            (cpoe - MIN(cpoe) OVER (PARTITION BY season)) / 
            NULLIF(MAX(cpoe) OVER (PARTITION BY season) - MIN(cpoe) OVER (PARTITION BY season), 0)
        ) AS cpoe_norm
        
    FROM qb_season_performance
),

qb_composite_ratings AS (
    SELECT 
        *,
        -- Custom composite rating (50-100 scale)
        ROUND(
            0.50 * COALESCE(epa_norm, 75) +
            0.30 * COALESCE(success_norm, 75) +
            0.20 * COALESCE(cpoe_norm, 75),
            1
        ) AS custom_rating
    FROM qb_ratings
),

-- Merge contracts with performance
qb_value_base AS (
    SELECT 
        r.player_name,
        r.player_id,
        r.season,
        c.team AS contract_team,
        r.attempts,
        r.custom_rating,
        c.apy AS salary,
        c.total_value,
        c.guaranteed,
        c.year_signed,
        c.contract_length,
        
        -- Calculate salary percentile within season
        100.0 * PERCENT_RANK() OVER (PARTITION BY r.season ORDER BY c.apy) AS salary_percentile,
        
        -- Performance metrics
        r.total_pass_epa,
        r.cpoe,
        r.pass_success_rate,
        r.completion_pct,
        r.td_rate,
        r.turnover_rate,
        r.total_wpa
        
    FROM qb_composite_ratings r
    INNER JOIN contract_years c
        ON r.player_id = c.player_id 
        AND r.season = c.season
    WHERE c.apy > 0  -- Filter out rookie contracts and missing data
)

-- Final view with value calculations
SELECT 
    player_name,
    player_id,
    season,
    contract_team AS team,
    attempts,
    custom_rating,
    salary,
    ROUND(salary, 2) AS salary_millions,
    ROUND(salary_percentile, 1) AS salary_percentile,
    
    -- Value Score: Rating minus Salary Percentile
    -- Positive = good value, Negative = overpaid
    ROUND(custom_rating - salary_percentile, 1) AS value_score,
    
    -- Value Category
    CASE 
        WHEN (custom_rating - salary_percentile) > 20 THEN 'Excellent Value'
        WHEN (custom_rating - salary_percentile) > 10 THEN 'Good Value'
        WHEN (custom_rating - salary_percentile) > -10 THEN 'Fair Value'
        WHEN (custom_rating - salary_percentile) > -20 THEN 'Overpaid'
        ELSE 'Severely Overpaid'
    END AS value_category,
    
    -- Rating per million dollars
    ROUND(custom_rating / NULLIF(salary, 0), 2) AS rating_per_million,
    
    -- Performance metrics
    ROUND(total_pass_epa, 1) AS total_pass_epa,
    ROUND(cpoe, 1) AS cpoe,
    ROUND(pass_success_rate * 100, 1) AS success_rate_pct,
    ROUND(completion_pct, 1) AS completion_pct,
    ROUND(td_rate * 100, 1) AS td_rate_pct,
    ROUND(turnover_rate * 100, 1) AS turnover_rate_pct,
    ROUND(total_wpa, 2) AS total_wpa,
    
    -- Contract details
    total_value,
    guaranteed,
    year_signed,
    contract_length

FROM qb_value_base
ORDER BY season DESC, value_score DESC;
"""

print("="*80)
print("Creating qb_contract_value view...")
print("="*80)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Drop existing view if it exists
cursor.execute("DROP VIEW IF EXISTS qb_contract_value")
print("[OK] Dropped old view (if existed)")

# Create new view
cursor.execute(create_view_sql)
conn.commit()
print("[OK] Created qb_contract_value view")

# Test the view
test_query = """
SELECT 
    COUNT(*) as total_records,
    MIN(season) as first_season,
    MAX(season) as last_season,
    COUNT(DISTINCT player_name) as unique_qbs,
    COUNT(DISTINCT value_category) as value_categories
FROM qb_contract_value
"""

result = cursor.execute(test_query).fetchone()

print("\n" + "="*80)
print("VALIDATION")
print("="*80)
print(f"Total QB-season contracts: {result[0]:,}")
print(f"Seasons covered: {result[1]}-{result[2]}")
print(f"Unique QBs: {result[3]:,}")
print(f"Value categories: {result[4]}")

# Show sample data
print("\n" + "="*80)
print("SAMPLE DATA - Best Value (Top 5)")
print("="*80)

sample_query = """
SELECT 
    player_name,
    season,
    ROUND(custom_rating, 1) as rating,
    ROUND(salary / 1000000.0, 1) as salary_m,
    value_score,
    value_category
FROM qb_contract_value
ORDER BY value_score DESC
LIMIT 5
"""

cursor.execute(sample_query)
for row in cursor.fetchall():
    print(f"{row[0]:20s} ({row[1]}) - Rating: {row[2]:5.1f}, Salary: ${row[3]:6.1f}M, Value: {row[4]:+6.1f} ({row[5]})")

print("\n" + "="*80)
print("SAMPLE DATA - Worst Value (Bottom 5)")
print("="*80)

sample_query_worst = """
SELECT 
    player_name,
    season,
    ROUND(custom_rating, 1) as rating,
    ROUND(salary / 1000000.0, 1) as salary_m,
    value_score,
    value_category
FROM qb_contract_value
ORDER BY value_score ASC
LIMIT 5
"""

cursor.execute(sample_query_worst)
for row in cursor.fetchall():
    print(f"{row[0]:20s} ({row[1]}) - Rating: {row[2]:5.1f}, Salary: ${row[3]:6.1f}M, Value: {row[4]:+6.1f} ({row[5]})")

conn.close()

print("\n" + "="*80)
print("[OK] View created successfully!")
print("="*80)
print("\nQuery the view with:")
print("  SELECT * FROM qb_contract_value")
print("\nFiltered examples:")
print("  SELECT * FROM qb_contract_value WHERE season = 2024")
print("  SELECT * FROM qb_contract_value WHERE value_category = 'Excellent Value'")
print("  SELECT * FROM qb_contract_value WHERE value_score > 15 ORDER BY season")
print("="*80)
