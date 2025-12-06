# NFL QB Analysis & Rating System (2010-2025)

Custom quarterback rating system built from 754,858 play-by-play records, analyzing 16 seasons of NFL data to create a more comprehensive QB evaluation model.

## Project Overview

Existing QB rating systems (NFL Passer Rating, QBR, ELO) each capture important aspects of quarterback play, but none provide a complete picture. This project develops a custom rating system by analyzing these established models alongside raw play-by-play data to better evaluate modern quarterback performance.

QB rankings are a constant topic of debate among football fans and analysts. This project aims to contribute to that discussion by building a data-driven model that accounts for the multi-dimensional nature of quarterback play - passing accuracy, decision-making, mobility, ball security, pocket presence, and playmaking ability.

### Primary Goal
Build a custom QB rating system that improves upon existing models by incorporating:
- Advanced metrics from established rating systems (QBR, ELO)
- Play-by-play situational data (EPA, CPOE, WPA)
- Modern tracking technology (Next Gen Stats)
- Context-aware evaluation across six playstyle dimensions

### Secondary Goal
Predict future QB performance and statistics based on historical trends and multi-season patterns.

## Key Features

- Custom 6-dimension rating system: Mobility, Aggression, Accuracy, Ball Security, Pocket Presence, Playmaking
- Archetype classification based on playstyle ratings
- Interactive Streamlit dashboard with 6 analysis tabs
- 16 seasons of comprehensive data (2010-2025)
- 754,858 play-by-play records from nflfastR
- Machine learning composite ratings for comparison
- SQLite database with 8 integrated data sources

## Tech Stack

- **Language:** Python 3.12
- **Package Manager:** UV
- **Database:** SQLite (1.4 GB)
- **Data Sources:** nflfastR, ESPN QBR, Next Gen Stats, ELO rankings, Over The Cap
- **Analysis:** pandas, numpy, scikit-learn
- **Visualization:** Streamlit, plotly, matplotlib, seaborn

## Setup

**Requirements:** Python 3.9+, UV package manager

```bash
# Clone repository
git clone https://github.com/cgalgano/NFL-QB-Analysis.git
cd NFL-QB-Analysis

# Install UV (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Install dependencies
uv sync
```

## Usage

### Run Streamlit Dashboard
```bash
uv run streamlit run custom_qb_ratings_app.py
```

### Explore Analysis Notebooks
- `Modeling/custom_qb_rating_system.ipynb` - Rating formula development
- `data_load/qb_data_loading.ipynb` - Data ingestion pipeline
- `data_load/test_qb_database.ipynb` - Database loading
- `Comprehensive_NFL_QB_Review.ipynb` - Full analysis with archetype logic

## Database Structure

Location: `data_load/nfl_qb_data.db`

- `play_by_play` - 754,858 plays (2010-2025)
- `qb_statistics` - 10,029 game logs
- `espn_qbr` - 502 season ratings
- `nflelo_qb_rankings` - 687 comprehensive season stats
- `next_gen_stats` - 5,697 advanced tracking metrics
- `player_contracts` - 1,939 contract records
- `custom_qb_ratings` - Custom rating outputs
- `qb_composite_ratings` - ML composite ratings

See `data_load/DATABASE_TABLES_GUIDE.md` for complete schema documentation.

## Rating System

### Six Playstyle Dimensions (50-100 scale)

1. **Mobility** - Rushing volume and efficiency (85% rush yards/game, 15% success rate)
2. **Aggression** - Downfield passing aggressiveness (65% Y/A, 25% deep pass rate, 10% air yards)
3. **Accuracy** - Completion probability over expected (CPOE)
4. **Ball Security** - Turnover avoidance (inverted turnover rate)
5. **Pocket Presence** - Pressure handling (60% sack avoidance, 40% EPA under pressure)
6. **Playmaking** - Overall value creation (EPA per play)

### Archetype Classification

QBs are assigned archetypes based on their dominant playstyle ratings:
- Elite tier: 93+ rating
- Strong tier: 85+ rating  
- Solid tier: 72+ rating

Examples: Dynamic Rusher, Precision Passer, Gunslinger, Efficient Ball Protector, Poised Passer

## Data Sources

- Play-by-play: [nflfastR](https://github.com/nflverse/nflfastR) via [nflreadpy](https://github.com/nflverse/nflreadpy)
- QBR: ESPN Total Quarterback Rating
- ELO: FiveThirtyEight NFL QB Rankings
- Tracking: NFL Next Gen Stats
- Contracts: Over The Cap

## License

This project is open source and available for educational and analytical purposes.
