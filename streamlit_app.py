import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import nflreadpy

# Page configuration
st.set_page_config(
    page_title="NFL QB Performance Analysis",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    h1 {
        color: #1f77b4;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and description
st.title("🏈 NFL Quarterback Performance Analysis (2021-2025)")
st.markdown("""
Comprehensive statistical analysis evaluating NFL quarterback performance using advanced metrics beyond traditional box scores.
**Data Source:** nflfastR play-by-play data via nflreadpy
""")

# Sidebar controls
st.sidebar.header("⚙️ Analysis Controls")

# Season selector
season_start, season_end = st.sidebar.select_slider(
    "Select Season Range",
    options=list(range(2021, 2026)),
    value=(2021, 2025),
    help="Choose the range of seasons to analyze"
)

# Minimum attempts filter
min_attempts = st.sidebar.slider(
    "Minimum Pass Attempts",
    min_value=100,
    max_value=500,
    value=300,
    step=50,
    help="Filter QBs by minimum pass attempts for statistical significance"
)

# Top N QBs for heatmap
top_n_qbs = st.sidebar.slider(
    "Top N QBs for Heatmap",
    min_value=10,
    max_value=25,
    value=15,
    step=1,
    help="Number of top QBs to display in situational heatmap"
)

# Load data
@st.cache_data
def load_data(start_season, end_season):
    """Load and cache play-by-play data"""
    seasons = range(start_season, end_season + 1)
    pbp_list = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, season in enumerate(seasons):
        status_text.text(f"Loading {season} season...")
        pbp_season = nflreadpy.load_pbp(season).to_pandas()
        pbp_list.append(pbp_season)
        progress_bar.progress((idx + 1) / len(seasons))
    
    progress_bar.empty()
    status_text.empty()
    
    pbp = pd.concat(pbp_list, ignore_index=True)
    return pbp

# Process data
@st.cache_data
def process_qb_stats(pbp, min_attempts_filter):
    """Process QB statistics"""
    # Filter passing plays
    passing_plays = pbp[pbp['pass_attempt'] == 1].copy()
    passing_plays = passing_plays[passing_plays['passer_player_name'].notnull()]
    passing_plays['success'] = (passing_plays['epa'] > 0).astype(int)
    
    # Filter rushing plays for QBs
    rushing_plays = pbp[(pbp['rush_attempt'] == 1) & (pbp['rusher_player_name'].notnull())].copy()
    rushing_plays['success'] = (rushing_plays['epa'] > 0).astype(int)
    
    # Aggregate passing statistics
    pass_stats = passing_plays.groupby('passer_player_name').agg(
        pass_attempts=('pass_attempt', 'sum'),
        completions=('complete_pass', 'sum'),
        pass_tds=('pass_touchdown', 'sum'),
        interceptions=('interception', 'sum'),
        sacks=('sack', 'sum'),
        pass_epa_total=('epa', 'sum'),
        pass_epa_mean=('epa', 'mean'),
        passing_yards=('passing_yards', 'sum'),
        air_yards_total=('air_yards', 'sum'),
        cpoe_mean=('cpoe', 'mean'),
        pass_successes=('success', 'sum')
    ).reset_index()
    
    # Aggregate rushing statistics
    rush_stats = rushing_plays.groupby('rusher_player_name').agg(
        rush_attempts=('rush_attempt', 'sum'),
        rush_epa_total=('epa', 'sum'),
        rush_epa_mean=('epa', 'mean'),
        rushing_yards=('rushing_yards', 'sum'),
        rush_successes=('success', 'sum')
    ).reset_index()
    rush_stats.rename(columns={'rusher_player_name': 'passer_player_name'}, inplace=True)
    
    # Merge passing and rushing stats
    qb_stats = pass_stats.merge(rush_stats, on='passer_player_name', how='left')
    qb_stats.fillna({'rush_attempts': 0, 'rush_epa_total': 0, 'rush_epa_mean': 0, 
                     'rushing_yards': 0, 'rush_successes': 0}, inplace=True)
    
    # Calculate total metrics
    qb_stats['total_plays'] = qb_stats['pass_attempts'] + qb_stats['rush_attempts']
    qb_stats['total_epa'] = qb_stats['pass_epa_total'] + qb_stats['rush_epa_total']
    qb_stats['total_epa_per_play'] = qb_stats['total_epa'] / qb_stats['total_plays']
    qb_stats['total_successes'] = qb_stats['pass_successes'] + qb_stats['rush_successes']
    qb_stats['total_success_rate'] = 100 * (qb_stats['total_successes'] / qb_stats['total_plays'])
    
    # Calculate derived metrics
    qb_stats['completion_pct'] = 100 * (qb_stats['completions'] / qb_stats['pass_attempts'])
    qb_stats['pass_success_rate'] = 100 * (qb_stats['pass_successes'] / qb_stats['pass_attempts'])
    qb_stats['td_int_ratio'] = qb_stats['pass_tds'] / qb_stats['interceptions'].replace(0, 1)
    qb_stats['yards_per_attempt'] = qb_stats['passing_yards'] / qb_stats['pass_attempts']
    qb_stats['sack_rate'] = 100 * (qb_stats['sacks'] / (qb_stats['pass_attempts'] + qb_stats['sacks']))
    qb_stats['td_rate'] = 100 * (qb_stats['pass_tds'] / qb_stats['pass_attempts'])
    qb_stats['int_rate'] = 100 * (qb_stats['interceptions'] / qb_stats['pass_attempts'])
    qb_stats['air_yards_per_attempt'] = qb_stats['air_yards_total'] / qb_stats['pass_attempts']
    
    # Filter for minimum attempts
    qb_stats = qb_stats[qb_stats['pass_attempts'] >= min_attempts_filter].sort_values('total_epa_per_play', ascending=False)
    
    return qb_stats, passing_plays, rushing_plays

# Main app logic
try:
    with st.spinner('Loading NFL play-by-play data...'):
        pbp = load_data(season_start, season_end)
    
    with st.spinner('Processing QB statistics...'):
        qb_stats, passing_plays, rushing_plays = process_qb_stats(pbp, min_attempts)
    
    # Display key metrics
    st.header("📊 Dataset Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Plays", f"{len(pbp):,}")
    with col2:
        st.metric("Qualifying QBs", len(qb_stats))
    with col3:
        st.metric("Seasons Analyzed", f"{season_start}-{season_end}")
    with col4:
        st.metric("Min Pass Attempts", min_attempts)
    
    # QB Search/Filter
    st.header("🔍 QB Rankings")
    qb_search = st.text_input("Search for a specific QB", placeholder="e.g., Patrick Mahomes")
    
    if qb_search:
        filtered_qbs = qb_stats[qb_stats['passer_player_name'].str.contains(qb_search, case=False, na=False)]
    else:
        filtered_qbs = qb_stats.head(10)
    
    # Display QB rankings table
    st.dataframe(
        filtered_qbs[['passer_player_name', 'pass_attempts', 'rush_attempts', 'total_plays', 
                      'total_epa_per_play', 'cpoe_mean', 'yards_per_attempt', 'sack_rate']].style.format({
            'total_epa_per_play': '{:.3f}',
            'cpoe_mean': '{:.2f}',
            'yards_per_attempt': '{:.2f}',
            'sack_rate': '{:.2f}%'
        }),
        use_container_width=True
    )
    
    # Visualization tabs
    st.header("📈 Performance Visualizations")
    tab1, tab2, tab3 = st.tabs(["Total EPA vs CPOE", "Situational Heatmap", "Sack Rate vs Y/A"])
    
    # Visualization 1: Total EPA vs CPOE
    with tab1:
        st.subheader("QB Performance: Total EPA vs CPOE")
        
        fig, ax = plt.subplots(figsize=(16, 12))
        
        # Add quadrant lines
        ax.axhline(y=qb_stats['total_epa_per_play'].median(), color='gray', linestyle='--', linewidth=1.5, alpha=0.5)
        ax.axvline(x=qb_stats['cpoe_mean'].median(), color='gray', linestyle='--', linewidth=1.5, alpha=0.5)
        
        # Plot small markers
        ax.scatter(qb_stats['cpoe_mean'], qb_stats['total_epa_per_play'], 
                   s=20, color='steelblue', alpha=0.3, zorder=1)
        
        # Label all QBs
        for _, qb in qb_stats.iterrows():
            ax.text(qb['cpoe_mean'], qb['total_epa_per_play'], qb['passer_player_name'],
                    fontsize=10, fontweight='bold', alpha=0.9,
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                             edgecolor='steelblue', alpha=0.7, linewidth=1),
                    zorder=2)
        
        ax.set_xlabel('CPOE (Completion % Over Expected)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Total EPA per Play (Passing + Rushing)', fontsize=13, fontweight='bold')
        ax.set_title(f'QB Performance: Total EPA vs CPOE ({season_start}-{season_end})', 
                     fontsize=15, fontweight='bold', pad=20)
        
        # Quadrant labels
        ax.text(0.98, 0.98, 'Elite\n(High Total EPA & CPOE)', 
                transform=ax.transAxes, fontsize=10, ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor='green', alpha=0.2))
        ax.text(0.02, 0.98, 'High Total EPA\nLow CPOE', 
                transform=ax.transAxes, fontsize=10, ha='left', va='top',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.2))
        ax.text(0.98, 0.02, 'High CPOE\nLow Total EPA', 
                transform=ax.transAxes, fontsize=10, ha='right', va='bottom',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.2))
        ax.text(0.02, 0.02, 'Below Average', 
                transform=ax.transAxes, fontsize=10, ha='left', va='bottom',
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.2))
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)
        
        st.info("""
        **How to read this chart:**
        - **Upper-right (Green)**: Elite QBs with high value creation and accuracy
        - **Upper-left (Yellow)**: High value but lower accuracy (often mobile QBs)
        - **Lower-right (Yellow)**: Accurate but limited value generation
        - **Lower-left (Red)**: Below average in both metrics
        """)
    
    # Visualization 2: Situational Heatmap
    with tab2:
        st.subheader("Situational QB Performance")
        
        # Combine passing and rushing plays
        all_plays = pd.concat([passing_plays, rushing_plays[rushing_plays['rusher_player_name'].isin(qb_stats['passer_player_name'])]])
        
        # Create situational contexts
        all_plays['down'] = all_plays['down'].astype(str)
        all_plays['field_zone'] = pd.cut(all_plays['yardline_100'], 
                                          bins=[0, 20, 50, 75, 100],
                                          labels=['Red Zone', 'Scoring Range', 'Midfield', 'Own Territory'])
        all_plays['score_diff'] = all_plays['score_differential']
        all_plays['score_situation'] = pd.cut(all_plays['score_diff'],
                                               bins=[-100, -8, -3, 3, 8, 100],
                                               labels=['Down 2+ Scores', 'Down 4-8', 'Close', 'Up 4-8', 'Up 2+ Scores'])
        
        # Unify player name column
        all_plays['qb_name'] = all_plays['passer_player_name'].fillna(all_plays['rusher_player_name'])
        
        # Select top N QBs
        top_qbs_heatmap = qb_stats.nlargest(top_n_qbs, 'total_epa_per_play')['passer_player_name'].tolist()
        situational_context = all_plays[all_plays['qb_name'].isin(top_qbs_heatmap)]
        situational_context = situational_context[situational_context['down'] != 'nan']
        
        # Calculate EPA by situation
        situations = ['down', 'field_zone', 'score_situation']
        situation_labels = ['Down', 'Field Position', 'Score Differential']
        
        fig, axes = plt.subplots(1, 3, figsize=(20, 10))
        
        for idx, (situation, label) in enumerate(zip(situations, situation_labels)):
            heatmap_data = situational_context.groupby(['qb_name', situation])['epa'].mean().unstack(fill_value=0)
            qb_order = [qb for qb in top_qbs_heatmap if qb in heatmap_data.index]
            heatmap_data = heatmap_data.loc[qb_order]
            
            sns.heatmap(heatmap_data, ax=axes[idx], cmap='RdYlGn', center=0, 
                        vmin=-0.3, vmax=0.3, annot=True, fmt='.2f',
                        cbar_kws={'label': 'EPA'}, linewidths=0.5)
            
            axes[idx].set_title(f'EPA by {label}', fontsize=13, fontweight='bold', pad=10)
            axes[idx].set_xlabel(label, fontsize=11, fontweight='bold')
            axes[idx].set_ylabel('Quarterback' if idx == 0 else '', fontsize=11, fontweight='bold')
            axes[idx].tick_params(axis='y', labelsize=9)
            axes[idx].tick_params(axis='x', labelsize=9, rotation=45)
        
        plt.suptitle(f'Situational QB Performance: Total EPA Across Game Contexts\n(Top {top_n_qbs} QBs by Overall EPA/play - Passing + Rushing)', 
                     fontsize=16, fontweight='bold', y=1.00)
        plt.tight_layout()
        st.pyplot(fig)
        
        st.info("""
        **How to read this chart:**
        - **Green cells**: Positive EPA (effective in that situation)
        - **Red cells**: Negative EPA (struggles in that situation)
        - Elite QBs show green across most situations
        """)
    
    # Visualization 3: Sack Rate vs Y/A
    with tab3:
        st.subheader("QB Pocket Management vs Offensive Output")
        
        fig, ax = plt.subplots(figsize=(16, 12))
        
        # Add quadrant lines
        ax.axhline(y=qb_stats['yards_per_attempt'].median(), color='gray', linestyle='--', linewidth=1.5, alpha=0.5)
        ax.axvline(x=qb_stats['sack_rate'].median(), color='gray', linestyle='--', linewidth=1.5, alpha=0.5)
        
        # Plot small markers
        ax.scatter(qb_stats['sack_rate'], qb_stats['yards_per_attempt'], 
                   s=20, color='steelblue', alpha=0.3, zorder=1)
        
        # Label all QBs
        for _, qb in qb_stats.iterrows():
            ax.text(qb['sack_rate'], qb['yards_per_attempt'], qb['passer_player_name'],
                    fontsize=10, fontweight='bold', alpha=0.9,
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                             edgecolor='steelblue', alpha=0.7, linewidth=1),
                    zorder=2)
        
        ax.set_xlabel('Sack Rate (%)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Yards per Attempt', fontsize=13, fontweight='bold')
        ax.set_title(f'QB Pocket Management vs Offensive Output ({season_start}-{season_end})', 
                     fontsize=15, fontweight='bold', pad=20)
        
        # Quadrant labels
        ax.text(0.98, 0.98, 'Elite\n(Low Sacks, High Y/A)', 
                transform=ax.transAxes, fontsize=10, ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor='green', alpha=0.2))
        ax.text(0.02, 0.98, 'Struggling\n(High Sacks, High Y/A)', 
                transform=ax.transAxes, fontsize=10, ha='left', va='top',
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.2))
        ax.text(0.98, 0.02, 'Conservative\n(Low Sacks, Low Y/A)', 
                transform=ax.transAxes, fontsize=10, ha='right', va='bottom',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.2))
        ax.text(0.02, 0.02, 'High Risk\n(High Sacks, Low Y/A)', 
                transform=ax.transAxes, fontsize=10, ha='left', va='bottom',
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.2))
        
        ax.grid(True, alpha=0.3)
        ax.invert_xaxis()
        plt.tight_layout()
        st.pyplot(fig)
        
        st.info("""
        **How to read this chart:**
        - **Upper-right (Green)**: Elite pocket management with high offensive output
        - **Upper-left (Red)**: Takes many sacks but still productive
        - **Lower-right (Yellow)**: Safe but limited explosiveness
        - **Lower-left (Red)**: High sacks and low production
        """)
    
    # Download section
    st.header("💾 Download Data")
    col1, col2 = st.columns(2)
    
    with col1:
        csv = qb_stats.to_csv(index=False)
        st.download_button(
            label="Download QB Stats (CSV)",
            data=csv,
            file_name=f"qb_stats_{season_start}_{season_end}.csv",
            mime="text/csv"
        )
    
    with col2:
        st.download_button(
            label="Download Full Dataset (CSV)",
            data=pbp.to_csv(index=False),
            file_name=f"nfl_pbp_{season_start}_{season_end}.csv",
            mime="text/csv"
        )
    
    # Metrics explanation
    with st.expander("📖 Metric Definitions"):
        st.markdown("""
        ### EPA (Expected Points Added)
        Measures play value by comparing expected points before and after a play, accounting for down, distance, field position, and score.
        
        **Example**: On 3rd-and-2 from the opponent's 30-yard line, the offense expects ~2.5 points. A 10-yard completion moves them to the 20-yard line with ~3.5 expected points = **+1.0 EPA**.
        
        ### CPOE (Completion % Over Expected)
        Measures accuracy adjusted for throw difficulty. Models predict completion probability based on throw distance, receiver separation, and defensive pressure.
        
        ### Sack Rate
        Percentage of dropbacks that result in a sack: `Sacks / (Pass Attempts + Sacks)`
        
        ### Total EPA
        Combines passing and rushing EPA to properly credit dual-threat QBs who add value with their legs.
        """)

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Please ensure nflreadpy is installed and you have an internet connection to download NFL data.")
