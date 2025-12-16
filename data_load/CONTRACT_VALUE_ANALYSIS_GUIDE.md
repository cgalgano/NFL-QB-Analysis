# QB Contract Value Analysis - Setup Guide

## Overview

This analysis evaluates which NFL quarterbacks provide the best/worst value relative to their contracts by comparing performance ratings against salary percentiles. The system is built using a **SQL view** for efficiency and consistency.

---

## Components

### 1. Database View: `qb_contract_value`

**Location:** SQLite database `nfl_qb_data.db`  
**Created by:** `data_load/create_qb_contract_value_view.py`

#### What It Does
The view automatically:
- Expands multi-year contracts to individual seasons
- Matches player_contracts with qb_season_stats by player_id and season
- Calculates custom QB ratings (composite of EPA, CPOE, success rate)
- Computes salary percentiles within each season
- Calculates value scores (rating - salary percentile)
- Categorizes QBs into value tiers

#### How to Create/Recreate the View

```powershell
cd c:\Users\carme\NFL_QB_Project\data_load
python create_qb_contract_value_view.py
```

**Output:**
```
Total QB-season contracts: 626
Seasons covered: 2010-2025
Unique QBs: 124
Value categories: 5
```

#### View Schema

| Column | Type | Description |
|--------|------|-------------|
| `player_name` | TEXT | QB full name |
| `player_id` | TEXT | GSIS unique ID |
| `season` | INTEGER | NFL season year |
| `team` | TEXT | Team abbreviation |
| `attempts` | INTEGER | Pass attempts (min 100) |
| `custom_rating` | REAL | Composite rating (50-100 scale) |
| `salary` | REAL | Annual salary (APY) |
| `salary_millions` | REAL | Salary in millions |
| `salary_percentile` | REAL | Salary rank within season (0-100) |
| `value_score` | REAL | Rating - Salary Percentile |
| `value_category` | TEXT | Excellent/Good/Fair/Overpaid/Severely Overpaid |
| `rating_per_million` | REAL | Rating per $1M salary |
| `total_pass_epa` | REAL | Expected Points Added (passing) |
| `cpoe` | REAL | Completion % Over Expected |
| `success_rate_pct` | REAL | Success rate % |
| `completion_pct` | REAL | Completion % |
| `td_rate_pct` | REAL | TD rate % |
| `turnover_rate_pct` | REAL | Turnover rate % |
| `total_wpa` | REAL | Win Probability Added |
| `total_value` | REAL | Total contract value |
| `guaranteed` | REAL | Guaranteed money |
| `year_signed` | INTEGER | Year contract was signed |
| `contract_length` | INTEGER | Contract length in years |

#### Value Categories

| Category | Value Score Range | Interpretation |
|----------|------------------|----------------|
| **Excellent Value** | > +20 | Elite performance, low salary |
| **Good Value** | +10 to +20 | Strong performance vs cost |
| **Fair Value** | -10 to +10 | Performance matches salary |
| **Overpaid** | -20 to -10 | Underperforming salary |
| **Severely Overpaid** | < -20 | Poor performance, high salary |

---

### 2. Analysis Notebook: `contract_value_analysis.ipynb`

**Location:** `data_load/EDA/contract_value_analysis.ipynb`

#### Sections

1. **Load Data** - Reads from `qb_contract_value` view
2. **Data Overview** - Summary statistics and distributions
3. **Best & Worst Value** - Top 20 QBs in each category
4. **Year-by-Year** - Best/worst value QB for each season
5. **Visualizations** - Scatter plots, distributions, category charts
6. **Export** - Saves CSV for Streamlit app
7. **Key Insights** - Summary findings

#### To Run the Notebook

Open in VS Code and run all cells. It will:
- Load 626 QB-season records from the view
- Generate statistical summaries
- Create visualizations
- Export to `data_load/project_CSVs/qb_contract_value_analysis.csv`

---

## Usage Examples

### Query the View Directly

```sql
-- All contract value data
SELECT * FROM qb_contract_value;

-- Filter by season
SELECT * FROM qb_contract_value WHERE season = 2024;

-- Best value QBs
SELECT * FROM qb_contract_value 
WHERE value_category = 'Excellent Value'
ORDER BY value_score DESC;

-- Overpaid QBs in recent seasons
SELECT player_name, season, custom_rating, salary_millions, value_score
FROM qb_contract_value
WHERE value_score < -15 AND season >= 2020
ORDER BY value_score ASC;
```

### Python/Pandas

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data_load/nfl_qb_data.db')
df = pd.read_sql_query("SELECT * FROM qb_contract_value", conn)

# Filter to 2024 season
df_2024 = df[df['season'] == 2024]

# Best value in 2024
best_2024 = df_2024.nlargest(10, 'value_score')
```

---

## Key Metrics Explained

### Custom Rating Calculation

The view calculates a composite rating on a 50-100 scale:

```
custom_rating = 0.50 × EPA_normalized + 
                0.30 × Success_Rate_normalized + 
                0.20 × CPOE_normalized
```

**Normalization:** Each metric is scaled 50-100 within each season.

### Value Score Calculation

```
value_score = custom_rating - salary_percentile
```

**Interpretation:**
- **Positive score:** QB performs better than their salary rank
- **Zero:** Performance matches salary
- **Negative score:** QB underperforms their salary

**Example:**
- Rating: 85.0 (good performance)
- Salary Percentile: 95.0 (top 5% salary)
- Value Score: -10.0 (Overpaid - high salary, decent performance)

---

## Integration with Streamlit App

The exported CSV (`qb_contract_value_analysis.csv`) is ready for Streamlit with:

### Recommended Features

1. **Year Filter** - Dropdown/slider to select season
2. **Side-by-Side Tables** - Best Value vs Worst Value
3. **Conditional Formatting** - Green (good value), Red (overpaid)
4. **Sortable Columns** - Click to sort by any metric
5. **Scatter Plot** - Rating vs Salary colored by value_score
6. **Player Search** - Filter by QB name

### Sample Streamlit Code

```python
import streamlit as st
import pandas as pd

# Load data
df = pd.read_csv('data_load/project_CSVs/qb_contract_value_analysis.csv')

# Year filter
year = st.selectbox('Select Season', sorted(df['Season'].unique(), reverse=True))
df_year = df[df['Season'] == year]

# Split into best/worst
col1, col2 = st.columns(2)

with col1:
    st.subheader('Best Value QBs')
    best = df_year.nlargest(10, 'Value Score')
    st.dataframe(best.style.background_gradient(subset=['Value Score'], cmap='Greens'))

with col2:
    st.subheader('Worst Value QBs')
    worst = df_year.nsmallest(10, 'Value Score')
    st.dataframe(worst.style.background_gradient(subset=['Value Score'], cmap='Reds_r'))
```

---

## Maintenance & Updates

### Regenerating the View

When contract data or QB stats are updated:

```powershell
cd c:\Users\carme\NFL_QB_Project\data_load
python create_qb_contract_value_view.py
```

This will drop and recreate the view with fresh data.

### Updating the CSV Export

After regenerating the view:

1. Open `contract_value_analysis.ipynb`
2. Run all cells
3. New CSV will be saved to `project_CSVs/`

---

## Data Flow

```
player_contracts (table)
    ↓
    + Expand to contract years
    ↓
    + Join with qb_season_stats (view)
    ↓
    + Calculate custom ratings
    ↓
    + Calculate salary percentiles
    ↓
    + Calculate value scores
    ↓
qb_contract_value (view)
    ↓
    + Load into notebook
    ↓
    + Analysis & visualization
    ↓
qb_contract_value_analysis.csv
    ↓
Streamlit App
```

---

## Filters Applied

The view automatically applies these filters:
- **Position:** QB only
- **Attempts:** ≥ 100 per season (meaningful sample size)
- **Salary:** > $0 (excludes missing/invalid contract data)
- **Contract Years:** Only years within contract length

---

## Benefits of Using a View

1. **Consistency:** Same calculations across notebooks and apps
2. **Performance:** Pre-computed joins and aggregations
3. **Maintainability:** Update logic in one place
4. **Simplicity:** Notebooks use simple `SELECT *` queries
5. **Reproducibility:** View definition is version-controlled

---

## Troubleshooting

### View not found
```powershell
python create_qb_contract_value_view.py
```

### Empty results
Check that:
- `qb_season_stats` view exists
- `player_contracts` table has QB data
- Database path is correct

### Salary showing as $0
Check contract year expansion logic in the view - contracts must be properly expanded across all years.

---

## Related Files

- **View creation:** `create_qb_contract_value_view.py`
- **Analysis notebook:** `EDA/contract_value_analysis.ipynb`
- **Export CSV:** `project_CSVs/qb_contract_value_analysis.csv`
- **Database:** `nfl_qb_data.db`
- **Other views:** `create_qb_season_stats_view.py`, `create_qb_plays_view.py`
