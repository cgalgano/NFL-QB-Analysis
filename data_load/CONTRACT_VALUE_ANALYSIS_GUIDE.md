# QB Contract Value Analysis Guide

## Overview

Evaluates which QBs provide the best/worst value by comparing actual performance ratings against expected ratings based on their salary.

---

## How It Works

### Expected Rating Approach

1. For each season, calculates what rating a QB *should* have based on their salary
2. Higher paid QBs are expected to perform better (linear relationship)
3. **Value = Actual Rating - Expected Rating**

**Example:**
- QB paid $55M should perform at 85 → actually performs at 75 → **-10 (Overpaid)**
- QB paid $5M should perform at 65 → actually performs at 80 → **+15 (Elite Value)**

### Value Categories

| Category | Value Range | Meaning |
|----------|-------------|---------|
| **Elite Value** | >+10 pts | Performing 10+ points above expectation |
| **Good Value** | +5 to +10 | Solid performance above salary level |
| **Fair Value** | -5 to +5 | Performing as expected |
| **Overpaid** | -10 to -5 | Underperforming relative to salary |
| **Severely Overpaid** | <-10 pts | Significantly underperforming |

---

## Setup & Usage

### Create/Update the View

```powershell
cd c:\Users\carme\NFL_QB_Project\data_load
python create_qb_contract_value_view.py
```

This creates the `qb_contract_value` view in `nfl_qb_data.db` and exports to `modeling/models/qb_contract_value.csv`.

### Query Examples

```sql
-- All data
SELECT * FROM qb_contract_value;

-- Filter by season
SELECT * FROM qb_contract_value WHERE season = 2024;

-- Best value QBs
SELECT player_name, actual_rating, expected_rating, value_over_expected
FROM qb_contract_value 
WHERE value_category = 'Elite Value'
ORDER BY value_over_expected DESC;
```

---

## Key Columns

| Column | Description |
|--------|-------------|
| `player_name` | QB name |
| `season` | Year |
| `team` | Team abbreviation |
| `actual_rating` | Performance rating (50-100) |
| `expected_rating` | Expected rating based on salary |
| `value_over_expected` | Actual - Expected |
| `value_pct` | Performance difference as % |
| `value_category` | Elite/Good/Fair/Overpaid/Severely Overpaid |
| `salary_millions` | Annual salary |

---

## Updates

When contract data or ratings change:

```powershell
python create_qb_contract_value_view.py
```

New CSV exported to `modeling/models/qb_contract_value.csv` for the Streamlit app.
