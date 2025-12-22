"""
Create qb_contract_value view - Pre-aggregated contract value analysis
Combines QB season stats with contract data to analyze value vs performance.
"""

import sqlite3
import pandas as pd
import os

db_path = 'c:/Users/carme/NFL_QB_Project/data_load/nfl_qb_data.db'
ratings_csv_path = 'c:/Users/carme/NFL_QB_Project/modeling/models/custom_qb_ratings.csv'

print("="*80)
print("Loading custom ratings from CSV...")
print("="*80)

# Load ratings CSV
ratings_df = pd.read_csv(ratings_csv_path)
print(f"Loaded {len(ratings_df)} ratings records")

# Connect to database
conn = sqlite3.connect(db_path)

# Create temporary table with ratings
ratings_df.to_sql('temp_qb_ratings', conn, if_exists='replace', index=False)
print("[OK] Imported ratings to temp table")

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

-- Get stats from qb_season_stats view
qb_stats AS (
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
        total_wpa
    FROM qb_season_stats
    WHERE attempts >= 100
),

-- Load pre-calculated ratings from temp table (same ratings the app uses)
qb_ratings AS (
    SELECT
        player_id,
        season,
        custom_rating
    FROM temp_qb_ratings
),

-- Calculate expected rating based on salary (linear regression per season)
salary_to_rating AS (
    SELECT 
        s.player_id,
        s.season,
        c.apy,
        r.custom_rating,
        -- Calculate average rating and salary for the season
        AVG(r.custom_rating) OVER (PARTITION BY s.season) AS avg_rating,
        AVG(c.apy) OVER (PARTITION BY s.season) AS avg_salary,
        -- Min and max for normalization
        MIN(c.apy) OVER (PARTITION BY s.season) AS min_salary,
        MAX(c.apy) OVER (PARTITION BY s.season) AS max_salary,
        MIN(r.custom_rating) OVER (PARTITION BY s.season) AS min_rating,
        MAX(r.custom_rating) OVER (PARTITION BY s.season) AS max_rating
    FROM qb_stats s
    INNER JOIN contract_years c
        ON s.player_id = c.player_id 
        AND s.season = c.season
    INNER JOIN qb_ratings r
        ON s.player_id = r.player_id
        AND s.season = r.season
    WHERE c.apy > 0
),

-- Merge contracts with performance and calculate expected rating
qb_value_base AS (
    SELECT 
        s.player_name,
        s.player_id,
        s.season,
        c.team AS contract_team,
        s.attempts,
        r.custom_rating,
        c.apy AS salary,
        c.total_value,
        c.guaranteed,
        c.year_signed,
        c.contract_length,
        
        -- Calculate expected rating based on salary percentile within season
        -- Maps salary position to expected rating range
        str.min_rating + 
            ((c.apy - str.min_salary) / NULLIF(str.max_salary - str.min_salary, 0)) * 
            (str.max_rating - str.min_rating) AS expected_rating,
        
        -- Performance metrics
        s.total_pass_epa,
        s.cpoe,
        s.pass_success_rate,
        s.completion_pct,
        s.td_rate,
        s.turnover_rate,
        s.total_wpa
        
    FROM qb_stats s
    INNER JOIN contract_years c
        ON s.player_id = c.player_id 
        AND s.season = c.season
    INNER JOIN qb_ratings r
        ON s.player_id = r.player_id
        AND s.season = r.season
    INNER JOIN salary_to_rating str
        ON s.player_id = str.player_id
        AND s.season = str.season
    WHERE c.apy > 0
)

-- Final view with value calculations
SELECT DISTINCT
    player_name,
    player_id,
    season,
    contract_team AS team,
    attempts,
    custom_rating AS actual_rating,
    ROUND(expected_rating, 1) AS expected_rating,
    salary,
    ROUND(salary, 2) AS salary_millions,
    
    -- Value metrics: Actual vs Expected
    ROUND(custom_rating - expected_rating, 1) AS value_over_expected,
    ROUND(((custom_rating - expected_rating) / NULLIF(expected_rating, 0)) * 100, 1) AS value_pct,
    
    -- Value Category based on difference from expected
    CASE 
        WHEN (custom_rating - expected_rating) > 10 THEN 'Elite Value'
        WHEN (custom_rating - expected_rating) > 5 THEN 'Good Value'
        WHEN (custom_rating - expected_rating) > -5 THEN 'Fair Value'
        WHEN (custom_rating - expected_rating) > -10 THEN 'Overpaid'
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
ORDER BY value_over_expected DESC;
"""

print("="*80)
print("Creating qb_contract_value view...")
print("="*80)

# Drop existing view if it exists
cursor = conn.cursor()
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
    ROUND(actual_rating, 1) as rating,
    ROUND(expected_rating, 1) as expected,
    ROUND(salary / 1000000.0, 1) as salary_m,
    value_over_expected,
    value_category
FROM qb_contract_value
ORDER BY value_over_expected DESC
LIMIT 5
"""

cursor.execute(sample_query)
for row in cursor.fetchall():
    print(f"{row[0]:20s} ({row[1]}) - Actual: {row[2]:5.1f}, Expected: {row[3]:5.1f}, Salary: ${row[4]:6.1f}M, Value: {row[5]:+6.1f} ({row[6]})")

print("\n" + "="*80)
print("SAMPLE DATA - Worst Value (Bottom 5)")
print("="*80)

sample_query_worst = """
SELECT 
    player_name,
    season,
    ROUND(actual_rating, 1) as rating,
    ROUND(expected_rating, 1) as expected,
    ROUND(salary / 1000000.0, 1) as salary_m,
    value_over_expected,
    value_category
FROM qb_contract_value
ORDER BY value_over_expected ASC
LIMIT 5
"""

cursor.execute(sample_query_worst)
for row in cursor.fetchall():
    print(f"{row[0]:20s} ({row[1]}) - Actual: {row[2]:5.1f}, Expected: {row[3]:5.1f}, Salary: ${row[4]:6.1f}M, Value: {row[5]:+6.1f} ({row[6]})")

# Export to CSV
print("\n" + "="*80)
print("EXPORTING TO CSV")
print("="*80)

export_query = "SELECT * FROM qb_contract_value"
export_df = pd.read_sql_query(export_query, conn)
output_path = 'c:/Users/carme/NFL_QB_Project/modeling/models/qb_contract_value.csv'
export_df.to_csv(output_path, index=False)
print(f"Exported {len(export_df)} records to {output_path}")

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

# Export to CSV for Streamlit Cloud deployment
print("\n" + "="*80)
print("Exporting to CSV for Streamlit deployment...")
print("="*80)

conn_export = sqlite3.connect(db_path)
export_df = pd.read_sql_query("SELECT * FROM qb_contract_value", conn_export)
conn_export.close()

csv_output_path = 'c:/Users/carme/NFL_QB_Project/modeling/models/qb_contract_value.csv'
export_df.to_csv(csv_output_path, index=False)

print(f"[OK] Exported {len(export_df)} records to {csv_output_path}")
print("="*80)
