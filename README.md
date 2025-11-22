# NFL Quarterback Performance Analysis (2021-2025)

Advanced statistical analysis evaluating NFL quarterback performance across five seasons using play-by-play data and modern analytics.

## 📊 Analysis Overview

This project ranks and evaluates NFL quarterbacks using three complementary visualizations:

1. **Total EPA vs CPOE** - Identifies elite QBs who create value through accurate execution
2. **Situational Performance Heatmap** - Shows consistency across game contexts (down, field position, score)
3. **Sack Rate vs Yards/Attempt** - Reveals pocket management styles

## 🔑 Key Features

- **Multi-season analysis**: 2021-2025 seasons (~500k+ plays)
- **Dual-threat QB evaluation**: Combines passing + rushing EPA
- **Context-aware metrics**: EPA accounts for down, distance, field position, score
- **Statistical rigor**: 300+ pass attempt filter for reliability

## 📦 Setup

**Requirements:** Python 3.9+, UV package manager

```bash
# Install UV (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# OR
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Install dependencies
uv pip install pandas numpy matplotlib seaborn nflreadpy
```

## 🚀 Usage

Open and run `nfl_qb_analysis.ipynb` in Jupyter:

```bash
jupyter notebook nfl_qb_analysis.ipynb
```

Data downloads automatically on first run via nflreadpy.

## 📈 Metrics Explained

- **EPA (Expected Points Added)**: Context-aware metric measuring play value relative to average outcomes
- **CPOE (Completion % Over Expected)**: Accuracy adjusted for throw difficulty
- **Sack Rate**: Sacks / (Pass Attempts + Sacks)
- **Yards/Attempt**: Passing efficiency and downfield aggressiveness

## 🗂️ Data Source

Play-by-play data from [nflfastR](https://github.com/nflverse/nflfastR) via [nflreadpy](https://github.com/nflverse/nflreadpy)

## 📝 License

This project is open source and available for educational and analytical purposes.
