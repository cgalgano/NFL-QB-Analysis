# NFL QB Analysis Streamlit Dashboard

An interactive dashboard for visualizing NFL quarterback performance data from 2021-2025.

## Features

### 📋 Rankings Table
- Sortable, filterable table of all QB rankings
- Color-coded performance metrics
- Download filtered data as CSV

### 📈 Performance Scatter Plots
- **EPA vs CPOE**: Value creation vs accuracy
- **Sack Rate vs Yards/Attempt**: Pocket management vs efficiency
- **Success Rate vs Completion %**: Consistency analysis
- Interactive tooltips with detailed stats

### 🎯 QB Comparison
- Select up to 5 QBs for side-by-side comparison
- Radar charts showing multi-dimensional performance
- Highlighted best/worst metrics

### 🔄 Archetype Analysis
- Distribution of QB playing styles
- Average performance by archetype
- Comprehensive archetype statistics

### 📊 Advanced Metrics
- Correlation heatmap between metrics
- Distribution plots by archetype
- Top performers by specific metrics

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

Or using UV:
```bash
uv pip install -r requirements.txt
```

2. Ensure `qb_rankings_2021_2025.csv` is in the same directory

## Running the App

```bash
streamlit run streamlit_app.py
```

The app will open in your default browser at `http://localhost:8501`

## Data Requirements

The app expects a CSV file named `qb_rankings_2021_2025.csv` with the following columns:
- rank
- passer_player_name
- qb_rating
- percentile
- archetype
- total_epa_per_play
- cpoe_mean
- sack_rate
- yards_per_attempt
- td_int_ratio
- success_rate
- completion_pct
- pass_attempts

## Filters

- **Archetype**: Filter by QB playing style
- **Rank Range**: Focus on top performers or specific ranges

## Deployment

### Streamlit Community Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Deploy from your repository

### Local Network Access

To access from other devices on your network:
```bash
streamlit run streamlit_app.py --server.address 0.0.0.0
```

## Customization

Edit `streamlit_app.py` to:
- Add new visualizations
- Modify color schemes
- Add additional metrics
- Change layout and styling

## Metrics Glossary

- **EPA (Expected Points Added)**: Context-aware metric measuring play value
- **CPOE (Completion % Over Expected)**: Accuracy adjusted for throw difficulty
- **Success Rate**: Percentage of plays with positive EPA
- **QB Rating**: Custom composite score (0-100) based on multiple dimensions
- **TD:INT Ratio**: Touchdown to interception ratio
- **Sack Rate**: Percentage of dropbacks resulting in sacks

## Troubleshooting

**App won't start:**
- Verify all dependencies are installed
- Check that Python version is 3.8 or higher

**Data not loading:**
- Ensure CSV file is in the correct location
- Verify CSV has all required columns

**Visualizations not rendering:**
- Update plotly: `pip install --upgrade plotly`
- Clear browser cache

## Contact

For questions or issues, please open an issue on GitHub.
