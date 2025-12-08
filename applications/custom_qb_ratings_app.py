import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import io
from pathlib import Path
import sys
import subprocess

# --- Archetype Assignment Logic ---
def get_level(val):
    """Classify rating value into tier."""
    if val >= 93:
        return 'elite'
    elif val >= 85:
        return 'strong'
    elif val >= 72:
        return 'solid'
    else:
        return 'developing'

def assign_custom_archetype(row):
    """Assign QB archetype based on playstyle rating strengths."""
    # Map to trait names
    trait_style_map = {
        'mobility_rating': 'Mobility',
        'aggression_rating': 'Aggression',
        'accuracy_rating': 'Accuracy',
        'ball_security_rating': 'Protective',
        'pocket_presence_rating': 'Poise',
        'playmaking_rating': 'Playmaking',
    }
    
    ratings = [
        ('mobility_rating', row['mobility_rating']),
        ('aggression_rating', row['aggression_rating']),
        ('accuracy_rating', row['accuracy_rating']),
        ('ball_security_rating', row['ball_security_rating']),
        ('pocket_presence_rating', row['pocket_presence_rating']),
        ('playmaking_rating', row['playmaking_rating']),
    ]
    ratings_sorted = sorted(ratings, key=lambda x: x[1], reverse=True)
    (trait1, val1), (trait2, val2), (trait3, val3) = ratings_sorted[0], ratings_sorted[1], ratings_sorted[2]
    level1 = get_level(val1)
    level2 = get_level(val2)
    name1 = trait_style_map[trait1]
    name2 = trait_style_map[trait2]
    
    # Well-rounded/All-Around logic (make less likely)
    good_traits = sum([v >= 77 for _, v in ratings])
    elite_traits = sum([v >= 93 for _, v in ratings])
    strong_traits = sum([v >= 85 for _, v in ratings])
    if good_traits == 6 and elite_traits == 0:
        return 'All-Around Threat'
    if strong_traits == 6:
        return 'Complete All-Around'
    
    # Special archetypes - check ball security first if it's elite (93+)
    if name1 == 'Protective' and val1 >= 93:
        if name2 == 'Accuracy' and val2 >= 82:
            return 'Efficient Ball Protector'
        elif name2 == 'Mobility' and val2 >= 82:
            return 'Safe Ball Handler'
        elif name2 == 'Aggression' and val2 >= 82:
            return 'Aggressive Ball Protector'
        else:
            return 'Ball Protector'
    
    if name1 == 'Mobility' and val1 >= 82:
        return 'Dynamic Rusher'
    if name1 == 'Accuracy' and val1 >= 82:
        return 'Precision Passer'
    if name1 == 'Aggression' and val1 >= 82:
        return 'Gunslinger'
    if name1 == 'Mobility' and name2 == 'Protective' and val1 >= 82 and val2 >= 93:
        return 'Safe Ball Handler'
    if name1 == 'Poise' and val1 >= 82:
        return 'Pressure Resistant'
    
    # If playmaking is highest, use second trait instead
    if name1 == 'Playmaking':
        if name2 == 'Aggression' and val2 >= 82:
            return 'Gunslinger'
        elif name2 == 'Accuracy' and val2 >= 82:
            return 'Precision Passer'
        elif name2 == 'Mobility' and val2 >= 82:
            return 'Dynamic Rusher'
        elif name2 == 'Protective' and val2 >= 85:
            return 'Efficient Passer'
        else:
            return 'Efficient Passer'
    
    # Combo archetypes
    if name1 == 'Accuracy' and name2 == 'Protective' and val1 >= 73 and val2 >= 92:
        return 'Steady Accurate Passer'
    if name1 == 'Aggression' and name2 == 'Accuracy' and val1 >= 73 and val2 >= 73:
        return 'Aggressive Precision Passer'
    
    # Default: use top trait and style, but avoid awkward combos
    if name1 == 'Protective':
        # Only allow Ball Protector archetype for extremely high ratings (95+)
        if val1 >= 95:
            if name2 == 'Mobility':
                return 'Safe Ball Handler'
            if name2 == 'Accuracy':
                return 'Efficient Ball Protector'
        # Otherwise redirect to generic archetypes based on second trait
        if name2 == 'Accuracy':
            return 'Accurate Passer'
        elif name2 == 'Mobility':
            return 'Mobile Passer'
        elif name2 == 'Aggression':
            return 'Aggressive Passer'
        else:
            return 'Poised Passer'
    if name1 == 'Aggression':
        return 'Aggressive Passer'
    if name1 == 'Accuracy':
        return 'Accurate Passer'
    if name1 == 'Mobility':
        return 'Mobile Passer'
    if name1 == 'Poise':
        return 'Poised Passer'
    # Final fallback
    return f"Balanced Passer" if name1 == 'Protective' else f"Efficient Passer"

# --- Load Data ---
@st.cache_data
def load_data():
    import sqlite3
    
    # Load custom ratings
    df = pd.read_csv('Modeling/models/custom_qb_ratings.csv')
    
    # Remove duplicates - keep the entry with more attempts for each player_id + season combination
    df = df.sort_values('attempts', ascending=False).drop_duplicates(subset=['player_id', 'season'], keep='first')
    
    # Load composite ratings from ML model
    composite_df = pd.read_csv('Modeling/models/qb_composite_ratings.csv')
    composite_df = composite_df[['player_id', 'season', 'composite_rating', 'predicted_qbr', 'predicted_elo']]
    
    # Check if database exists (for local dev and full setup)
    db_path = Path('data_load/nfl_qb_data.db')
    last_refresh = None
    
    if db_path.exists():
        # Load additional data from database
        conn = sqlite3.connect('data_load/nfl_qb_data.db')
        names_df = pd.read_sql('SELECT DISTINCT player_id, player_name as full_name FROM qb_statistics', conn)
        
        # Get last data refresh timestamp
        try:
            metadata_df = pd.read_sql('SELECT value, updated_at FROM metadata WHERE key = "last_data_refresh"', conn)
            if not metadata_df.empty:
                last_refresh = metadata_df.iloc[0]['updated_at']
        except:
            pass
        
        # Get yards per attempt from qb_season_stats view
        ya_query = """
        SELECT 
            player_id,
            season,
            (pass_yards_per_game * 17.0) / attempts as yards_per_attempt
        FROM qb_season_stats
        """
        ya_df = pd.read_sql(ya_query, conn)
        conn.close()
        
        # Merge database data
        df = df.merge(names_df, on='player_id', how='left')
        df = df.merge(ya_df, on=['player_id', 'season'], how='left')
    else:
        # No database - calculate yards per attempt from available data
        # Assuming pass_yards_per_game is in df, otherwise use defaults
        if 'pass_yards_per_game' in df.columns:
            df['yards_per_attempt'] = (df['pass_yards_per_game'] * 17.0) / df['attempts']
        else:
            df['yards_per_attempt'] = 7.0  # Default reasonable value
        
        df['full_name'] = None  # Will use player_name as fallback
    
    # Merge composite ratings
    df = df.merge(composite_df, on=['player_id', 'season'], how='left')
    
    # Use full name if available, otherwise keep abbreviated name
    df['display_name'] = df['full_name'].fillna(df['player_name'])
    
    # Calculate archetypes
    df['archetype'] = df.apply(assign_custom_archetype, axis=1)
    
    return df, last_refresh

# --- Helper: Explanation of Ratings ---
def rating_explanation():
    st.markdown("""
    ### What Each Rating Means (50-100 Scale)
    
    **Overall Custom Rating**: Transparent formula-based rating combining efficiency, impact, consistency, volume, ball security, and pressure performance.
    
    **Rating Scale**: 50-100 (like traditional grading)
    - 90-100: Elite/A+ grade
    - 80-89: Excellent/A grade  
    - 70-79: Good/B grade
    - 60-69: Average/C grade
    - 50-59: Below Average/D-F grade
    
    #### Playstyle Ratings (50-100 scale):
    - **Mobility**: Rush yards per game (85%) + rush success rate (15%) - heavily volume-focused
    - **Aggression**: Yards per attempt (65%, primary) + deep pass rate (25%) + air yards (10%) - downfield efficiency
    - **Accuracy**: CPOE (Completion % Over Expected)
    - **Ball Security**: Inverse of turnover rate (higher = fewer turnovers)
    - **Pocket Presence**: Inverse of sack rate + EPA under pressure
    - **Playmaking**: Total EPA per play (impact on every snap)
    
    #### Custom Rating Formula Weights:
    - **Efficiency (40%)**: Total Pass EPA (50%) + Success Rate (30%) + CPOE (20%)
    - **Impact (20%)**: Total WPA (50%) + High Leverage EPA (30%) + TD Rate (20%)
    - **Consistency (20%)**: 3rd Down Success (40%) + Red Zone EPA (35%) + Completion % (25%)
    - **Volume (5%)**: Passing Yards (40%) + Rush Yds/Game (30%) + Total TDs (30%)
    - **Ball Security (10%)**: Turnover Rate inverted (60%) + Sack Rate inverted (40%)
    - **Pressure Performance (5%)**: EPA Under Pressure (100%)
    
    **Data Source**: Play-by-play data (2010-2025) aggregated to season level. Minimum 150 attempts per season.
    """)

# --- Streamlit App ---
st.set_page_config(page_title="Custom NFL QB Rankings", layout="wide")

# Load data
df, last_refresh = load_data()

# Header with last updated info
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏈 Custom NFL QB Rankings (2010-2025)")
with col2:
    if last_refresh:
        from datetime import datetime
        refresh_dt = datetime.fromisoformat(last_refresh)
        st.caption(f"📅 Last updated: {refresh_dt.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.caption("💡 Run `python update_data.py` to refresh")

tabs = st.tabs(["Top 32 QBs & Playstyles", "Player Career View", "Component Scores Analysis", "EPA vs CPOE Scatter", "Sack Rate vs Y/A Scatter", "Custom vs ML Composite", "Interactive QB Journey Map"])

# --- Tab 1: Top 32 QBs Table ---
with tabs[0]:
    st.header("Top 32 QBs - Custom Ratings & Playstyle Profiles")
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", options=all_years, default=[2024, 2025] if 2024 in all_years else all_years[:2], format_func=str, key="year_filter_tab0")
    filtered_df = df[df['season'].isin(selected_years)]
    
    # If only one year is selected, show that year's ratings
    if len(selected_years) == 1:
        season_df = filtered_df.sort_values('custom_rating', ascending=False).head(32).reset_index(drop=True)
        season_df['Rank'] = season_df.index + 1
    else:
        # Aggregate over career for each QB (average ratings, most common archetype)
        agg_dict = {
            'custom_rating': 'mean',
            'mobility_rating': 'mean',
            'aggression_rating': 'mean',
            'accuracy_rating': 'mean',
            'ball_security_rating': 'mean',
            'pocket_presence_rating': 'mean',
            'playmaking_rating': 'mean',
            'attempts': 'sum',
            'display_name': 'first',
            'archetype': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]  # Most common archetype
        }
        season_df = filtered_df.groupby('player_name', as_index=False).agg(agg_dict)
        season_df = season_df.sort_values('custom_rating', ascending=False).head(32).reset_index(drop=True)
        season_df['Rank'] = season_df.index + 1
    
    show_cols = [
        'Rank', 'display_name', 'archetype', 'custom_rating', 'playmaking_rating', 'aggression_rating',
        'accuracy_rating', 'ball_security_rating', 'pocket_presence_rating', 'mobility_rating'
    ]
    rename_dict = {
        'Rank': 'Rank',
        'display_name': 'QB Name',
        'archetype': 'Archetype',
        'custom_rating': 'Overall Rating',
        'mobility_rating': 'Mobility',
        'aggression_rating': 'Aggression',
        'accuracy_rating': 'Accuracy',
        'ball_security_rating': 'Ball Security',
        'pocket_presence_rating': 'Pocket Presence',
        'playmaking_rating': 'Playmaking'
    }
    table = season_df[show_cols].rename(columns=rename_dict)
    gradient_cols = [
        'Overall Rating', 'Playmaking', 'Aggression', 'Accuracy',
        'Ball Security', 'Pocket Presence', 'Mobility'
    ]
    gradient_cols = [col for col in gradient_cols if col in table.columns]
    format_dict = {col: "{:.1f}" for col in gradient_cols}
    
    # Use custom colormap that works with 50-100 scale
    styled = table.style.format(format_dict).background_gradient(
        subset=gradient_cols, cmap='RdYlGn', vmin=50, vmax=100
    )
    st.dataframe(styled, use_container_width=True, height=800)
    rating_explanation()

# --- Tab 2: Player Career Ratings Table ---
with tabs[1]:
    st.header("Player Career Ratings Table")
    player = st.selectbox("Select Player", sorted(df['display_name'].unique()))
    player_df = df[df['display_name'] == player].sort_values('season')
    
    if not player_df.empty:
        # Ensure no duplicates in player_df before processing
        player_df = player_df.drop_duplicates(subset=['season', 'player_id'], keep='first')
        
        # Compute rank for each season (by custom_rating, descending)
        df_ranks = df[df['season'].isin(player_df['season'])].copy()
        df_ranks['Rank'] = df_ranks.groupby('season')['custom_rating'].rank(ascending=False, method='min')
        
        # Ensure df_ranks has no duplicates before merging
        df_ranks = df_ranks.drop_duplicates(subset=['season', 'player_id'], keep='first')
        
        player_df = player_df.merge(df_ranks[['season', 'player_id', 'Rank']], on=['season', 'player_id'], how='left')
        
        show_cols = [
            'season', 'Rank', 'attempts', 'custom_rating', 'playmaking_rating', 'aggression_rating',
            'accuracy_rating', 'ball_security_rating', 'pocket_presence_rating',
            'mobility_rating'
        ]
        rename_dict = {
            'season': 'Season',
            'Rank': 'Rank',
            'attempts': 'Attempts',
            'custom_rating': 'Overall Rating',
            'mobility_rating': 'Mobility',
            'aggression_rating': 'Aggression',
            'accuracy_rating': 'Accuracy',
            'ball_security_rating': 'Ball Security',
            'pocket_presence_rating': 'Pocket Presence',
            'playmaking_rating': 'Playmaking'
        }
        table = player_df[show_cols].rename(columns=rename_dict)
        gradient_cols = [
            'Overall Rating', 'Playmaking', 'Aggression', 'Accuracy',
            'Ball Security', 'Pocket Presence', 'Mobility'
        ]
        format_dict = {col: "{:.1f}" for col in gradient_cols}
        format_dict['Rank'] = "{:.0f}"
        format_dict['Attempts'] = "{:.0f}"
        
        styled = table.style.format(format_dict).background_gradient(
            subset=gradient_cols, cmap='RdYlGn', vmin=50, vmax=100
        )
        st.dataframe(styled, use_container_width=True, height=600)
        
        # Show radar chart for selected player
        st.subheader(f"Career Average Playstyle Profile: {player}")
        
        # Create radar chart using plotly - career averages
        categories = ['Playmaking', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket Presence', 'Mobility']
        
        # Calculate career averages
        avg_values = [
            player_df['playmaking_rating'].mean(),
            player_df['aggression_rating'].mean(),
            player_df['accuracy_rating'].mean(),
            player_df['ball_security_rating'].mean(),
            player_df['pocket_presence_rating'].mean(),
            player_df['mobility_rating'].mean()
        ]
        
        values_closed = avg_values + [avg_values[0]]
        categories_closed = categories + [categories[0]]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill='toself',
            line_color='steelblue',
            fillcolor='steelblue',
            opacity=0.6,
            name='Career Average'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[50, 100],
                    tickmode='linear',
                    tick0=50,
                    dtick=10
                )
            ),
            showlegend=False,
            title=f"{player} - Career Average Playstyle"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        rating_explanation()
    else:
        st.info("No data for this player.")

# --- Tab 3: Component Scores Analysis ---
with tabs[2]:
    st.header("Rating Component Scores Analysis")
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", all_years, default=[2024, 2025] if 2024 in all_years else [all_years[0]], key="year_filter_tab2")
    filtered_df = df[df['season'].isin(selected_years)]
    
    # If multiple years, aggregate
    if len(selected_years) > 1:
        agg_dict = {
            'custom_rating': 'mean',
            'efficiency_score': 'mean',
            'impact_score': 'mean',
            'consistency_score': 'mean',
            'volume_score': 'mean',
            'ball_security_score': 'mean',
            'pressure_score': 'mean',
            'display_name': 'first'
        }
        display_df = filtered_df.groupby('player_name', as_index=False).agg(agg_dict)
    else:
        display_df = filtered_df.copy()
    
    # Sort by custom rating
    display_df = display_df.sort_values('custom_rating', ascending=False).head(32).reset_index(drop=True)
    display_df['Rank'] = display_df.index + 1
    
    show_cols = [
        'Rank', 'display_name', 'custom_rating', 'efficiency_score', 'impact_score',
        'consistency_score', 'volume_score', 'ball_security_score', 'pressure_score'
    ]
    rename_dict = {
        'Rank': 'Rank',
        'display_name': 'QB Name',
        'custom_rating': 'Overall',
        'efficiency_score': 'Efficiency (40%)',
        'impact_score': 'Impact (20%)',
        'consistency_score': 'Consistency (20%)',
        'volume_score': 'Volume (5%)',
        'ball_security_score': 'Ball Security (10%)',
        'pressure_score': 'Pressure (5%)'
    }
    
    table = display_df[show_cols].rename(columns=rename_dict)
    gradient_cols = [
        'Overall', 'Efficiency (40%)', 'Impact (20%)', 'Consistency (20%)',
        'Volume (5%)', 'Ball Security (10%)', 'Pressure (5%)'
    ]
    format_dict = {col: "{:.1f}" for col in gradient_cols}
    
    styled = table.style.format(format_dict).background_gradient(
        subset=gradient_cols, cmap='RdYlGn', vmin=50, vmax=100
    )
    st.dataframe(styled, use_container_width=True, height=800)
    
    st.markdown("""
    ### Component Score Interpretation
    
    Each component is normalized to a 50-100 scale and weighted to create the overall rating:
    
    - **Efficiency (40%)**: How much value created per play (EPA, Success Rate, CPOE)
    - **Impact (20%)**: Big plays and clutch performance (WPA, High Leverage EPA, TD Rate)
    - **Consistency (20%)**: Performance in key situations (3rd downs, red zone, completion %)
    - **Volume (5%)**: Raw production (passing yards, rush yards/game, total TDs)
    - **Ball Security (10%)**: Avoiding mistakes (low turnover rate, low sack rate)
    - **Pressure Performance (5%)**: Effectiveness when under pressure
    
    **Higher scores are better** - Each component ranges from 50 (worst) to 100 (best).
    """)

# --- Tab 4: EPA vs CPOE Scatter Plot ---
with tabs[3]:
    st.header("Total Pass EPA vs CPOE Scatter Plot")
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", all_years, default=[2024, 2025] if 2024 in all_years else all_years[:2], key="year_filter_tab3")
    
    # Aggregate data by player across selected seasons
    if selected_years:
        filtered_df = df[df['season'].isin(selected_years)].copy()
        
        # Group by player and aggregate
        agg_df = filtered_df.groupby('display_name').agg({
            'cpoe': 'mean',
            'total_pass_epa': 'sum',  # Sum EPA across seasons
            'custom_rating': 'mean',
            'attempts': 'sum'
        }).reset_index()
        
        # Filter for minimum attempts (at least 225 per season on average)
        min_attempts = 225 * len(selected_years)
        agg_df = agg_df[agg_df['attempts'] >= min_attempts]
    else:
        agg_df = pd.DataFrame()
    
    if not agg_df.empty:
        fig = px.scatter(
            agg_df,
            x='cpoe',
            y='total_pass_epa',
            text='display_name',
            color='custom_rating',
            color_continuous_scale='RdYlGn',
            range_color=[50, 100],
            labels={
                'cpoe': 'CPOE (Completion % Over Expected)',
                'total_pass_epa': 'Total Pass EPA',
                'custom_rating': 'Custom Rating'
            },
            hover_data=['custom_rating', 'display_name', 'attempts']
        )
        fig.update_traces(textposition='top center', marker=dict(size=14, line=dict(width=1, color='DarkSlateGrey')))
        
        # Add quadrant lines
        median_epa = agg_df['total_pass_epa'].median()
        median_cpoe = agg_df['cpoe'].median()
        fig.add_shape(type="line", x0=median_cpoe, x1=median_cpoe, y0=agg_df['total_pass_epa'].min(), y1=agg_df['total_pass_epa'].max(),
                      line=dict(color="gray", dash="dash"))
        fig.add_shape(type="line", x0=agg_df['cpoe'].min(), x1=agg_df['cpoe'].max(), y0=median_epa, y1=median_epa,
                      line=dict(color="gray", dash="dash"))
        
        # Add quadrant labels
        fig.add_annotation(x=agg_df['cpoe'].max(), y=agg_df['total_pass_epa'].max(),
            text="Elite<br>(High EPA & CPOE)", showarrow=False, xanchor="right", yanchor="top",
            font=dict(size=13, color="green"), bgcolor="rgba(0,255,0,0.08)")
        fig.add_annotation(x=agg_df['cpoe'].min(), y=agg_df['total_pass_epa'].max(),
            text="High EPA<br>Low CPOE", showarrow=False, xanchor="left", yanchor="top",
            font=dict(size=13, color="orange"), bgcolor="rgba(255,255,0,0.08)")
        fig.add_annotation(x=agg_df['cpoe'].max(), y=agg_df['total_pass_epa'].min(),
            text="High CPOE<br>Low EPA", showarrow=False, xanchor="right", yanchor="bottom",
            font=dict(size=13, color="orange"), bgcolor="rgba(255,255,0,0.08)")
        fig.add_annotation(x=agg_df['cpoe'].min(), y=agg_df['total_pass_epa'].min(),
            text="Below Average", showarrow=False, xanchor="left", yanchor="bottom",
            font=dict(size=13, color="red"), bgcolor="rgba(255,0,0,0.08)")
        
        fig.update_layout(height=700, xaxis_title="CPOE (Completion % Over Expected)", yaxis_title="Total Pass EPA")
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        **Quadrant Interpretation:**
        
        - **Upper-right:** Elite (High EPA & CPOE) - Most accurate AND most effective
        - **Upper-left:** High EPA, Low CPOE - Volume throwers who produce despite lower accuracy
        - **Lower-right:** High CPOE, Low EPA - Accurate but not producing value (short passes?)
        - **Lower-left:** Below Average - Neither accurate nor effective
        
        **Total Pass EPA** = Sum of Expected Points Added on all passing plays
        **CPOE** = Completion % Over Expected (how accurate relative to pass difficulty)
        """)
    else:
        st.warning("No data available for selected seasons")

# --- Tab 5: Sack Rate vs Yards/Attempt Scatter Plot ---
with tabs[4]:
    st.header("Sack Rate vs Yards/Attempt Scatter Plot")
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", all_years, default=[2024, 2025] if 2024 in all_years else all_years[:2], key="year_filter_tab5")
    
    # Aggregate data by player across selected seasons
    if selected_years:
        filtered_df = df[df['season'].isin(selected_years)].copy()
        
        # Group by player and aggregate
        agg_df = filtered_df.groupby('display_name').agg({
            'sack_rate': 'mean',
            'yards_per_attempt': 'mean',
            'custom_rating': 'mean',
            'attempts': 'sum'
        }).reset_index()
        
        # Filter for minimum attempts
        min_attempts = 225 * len(selected_years)
        agg_df = agg_df[agg_df['attempts'] >= min_attempts]
        
        # Invert sack rate for plotting (so lower sack rate is to the right)
        agg_df['inv_sack_rate'] = -agg_df['sack_rate']
    else:
        agg_df = pd.DataFrame()
    
    if not agg_df.empty:
        fig2 = px.scatter(
            agg_df,
            x='inv_sack_rate',
            y='yards_per_attempt',
            text='display_name',
            color='custom_rating',
            color_continuous_scale='RdYlGn',
            range_color=[50, 100],
            labels={
                'inv_sack_rate': 'Sack Rate (Inverted - Lower is Right)',
                'yards_per_attempt': 'Yards per Attempt',
                'custom_rating': 'Custom Rating'
            },
            hover_data=['custom_rating', 'sack_rate', 'display_name', 'attempts']
        )
        fig2.update_traces(textposition='top center', marker=dict(size=14, line=dict(width=1, color='DarkSlateGrey')))
        
        # Add quadrant lines
        median_inv_sack = agg_df['inv_sack_rate'].median()
        median_ya = agg_df['yards_per_attempt'].median()
        fig2.add_shape(type="line", x0=median_inv_sack, x1=median_inv_sack, 
                       y0=agg_df['yards_per_attempt'].min(), y1=agg_df['yards_per_attempt'].max(),
                       line=dict(color="gray", dash="dash"))
        fig2.add_shape(type="line", x0=agg_df['inv_sack_rate'].min(), x1=agg_df['inv_sack_rate'].max(), 
                       y0=median_ya, y1=median_ya,
                       line=dict(color="gray", dash="dash"))
        
        # Add quadrant labels
        fig2.add_annotation(x=agg_df['inv_sack_rate'].max(), y=agg_df['yards_per_attempt'].max(),
            text="Elite<br>(Low Sacks, High Y/A)", showarrow=False, xanchor="right", yanchor="top",
            font=dict(size=13, color="green"), bgcolor="rgba(0,255,0,0.08)")
        fig2.add_annotation(x=agg_df['inv_sack_rate'].min(), y=agg_df['yards_per_attempt'].max(),
            text="High Risk High Reward<br>(High Sacks, High Y/A)", showarrow=False, xanchor="left", yanchor="top",
            font=dict(size=13, color="orange"), bgcolor="rgba(255,255,0,0.08)")
        fig2.add_annotation(x=agg_df['inv_sack_rate'].max(), y=agg_df['yards_per_attempt'].min(),
            text="Conservative<br>(Low Sacks, Low Y/A)", showarrow=False, xanchor="right", yanchor="bottom",
            font=dict(size=13, color="orange"), bgcolor="rgba(255,255,0,0.08)")
        fig2.add_annotation(x=agg_df['inv_sack_rate'].min(), y=agg_df['yards_per_attempt'].min(),
            text="High Risk Low Reward<br>(High Sacks, Low Y/A)", showarrow=False, xanchor="left", yanchor="bottom",
            font=dict(size=13, color="red"), bgcolor="rgba(255,0,0,0.08)")
        
        fig2.update_layout(height=700, xaxis_title="Sack Rate (Inverted: Lower Sack Rate = Right)", 
                           yaxis_title="Yards per Attempt")
        st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("""
        **Quadrant Interpretation:**
        
        - **Upper-right:** Elite (Low Sacks, High Y/A) - Protecting the ball AND throwing downfield
        - **Upper-left:** High Risk High Reward (High Sacks, High Y/A) - Aggressive downfield but taking sacks
        - **Lower-right:** Conservative (Low Sacks, Low Y/A) - Safe, short passes with good protection
        - **Lower-left:** High Risk Low Reward (High Sacks, Low Y/A) - Taking sacks without downfield production
        
        **Sack Rate** = Sacks / (Pass Attempts + Sacks)  
        **Y/A** = Yards per Attempt (downfield aggressiveness and completion efficiency)
        """)
    else:
        st.warning("No data available for selected seasons")

# --- Tab 6: Custom vs ML Composite Comparison ---
with tabs[5]:
    st.header("Custom Rating vs ML Composite Rating")
    
    st.markdown("""
    ### Comparing Two Approaches to QB Rating
    
    **Custom Rating (Formula-Based)**:
    - Transparent weighted formula: 40% Efficiency + 20% Impact + 20% Consistency + 5% Volume + 10% Ball Security + 5% Pressure
    - Scale: 50-100 (traditional grading)
    - Philosophy: Values efficiency, ball security, and pressure performance equally across all QBs
    
    **ML Composite Rating (Model-Based)**:
    - Machine learning models trained to predict QBR and ELO from play-by-play features
    - Composite: 60% Predicted QBR + 40% Predicted ELO
    - Scale: 0-100
    - Philosophy: Learns patterns from existing rating systems (captures what QBR/ELO value)
    
    ---
    """)
    
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", all_years, default=[2024, 2025] if 2024 in all_years else all_years[:2], key="year_filter_tab6")
    
    # Filter to QBs with both ratings
    comparison_df = df[df['season'].isin(selected_years) & df['composite_rating'].notna()].copy()
    
    if len(comparison_df) > 0:
        # Scatter plot
        fig = px.scatter(
            comparison_df,
            x='composite_rating',
            y='custom_rating',
            text='display_name',
            color='season',
            labels={
                'composite_rating': 'ML Composite Rating (0-100)',
                'custom_rating': 'Custom Rating (50-100)',
                'season': 'Season'
            },
            hover_data=['season', 'display_name', 'predicted_qbr', 'predicted_elo']
        )
        fig.update_traces(textposition='top center', marker=dict(size=12))
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        # Calculate correlation
        corr = comparison_df[['custom_rating', 'composite_rating']].corr().iloc[0, 1]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Correlation", f"{corr:.3f}")
        with col2:
            avg_custom = comparison_df['custom_rating'].mean()
            st.metric("Avg Custom Rating", f"{avg_custom:.1f}")
        with col3:
            avg_composite = comparison_df['composite_rating'].mean()
            st.metric("Avg Composite Rating", f"{avg_composite:.1f}")
        
        # Top 20 comparison table
        st.subheader("Top 20 QBs - Rating Comparison")
        
        if len(selected_years) == 1:
            top_df = comparison_df.sort_values('custom_rating', ascending=False).head(20).copy()
        else:
            # Aggregate for multiple years
            agg_dict = {
                'custom_rating': 'mean',
                'composite_rating': 'mean',
                'display_name': 'first',
                'attempts': 'sum'
            }
            top_df = comparison_df.groupby('player_name', as_index=False).agg(agg_dict)
            top_df = top_df.sort_values('custom_rating', ascending=False).head(20)
        
        top_df['Rank_Custom'] = top_df['custom_rating'].rank(ascending=False, method='min').astype(int)
        top_df['Rank_Composite'] = top_df['composite_rating'].rank(ascending=False, method='min').astype(int)
        top_df['Rank_Diff'] = top_df['Rank_Composite'] - top_df['Rank_Custom']
        
        display_df = top_df[['display_name', 'custom_rating', 'Rank_Custom', 'composite_rating', 'Rank_Composite', 'Rank_Diff']].copy()
        display_df.columns = ['QB Name', 'Custom Rating', 'Custom Rank', 'Composite Rating', 'Composite Rank', 'Rank Difference']
        
        # Format and style
        styled = display_df.style.format({
            'Custom Rating': '{:.1f}',
            'Composite Rating': '{:.1f}',
            'Custom Rank': '{:.0f}',
            'Composite Rank': '{:.0f}',
            'Rank Difference': '{:+.0f}'
        }).background_gradient(subset=['Custom Rating'], cmap='RdYlGn', vmin=50, vmax=100)\
          .background_gradient(subset=['Composite Rating'], cmap='RdYlGn', vmin=0, vmax=100)\
          .background_gradient(subset=['Rank Difference'], cmap='RdBu_r', vmin=-10, vmax=10)
        
        st.dataframe(styled, use_container_width=True, height=600)
        
        st.markdown("""
        ### Interpretation
        
        **Rank Difference**:
        - **Positive** (red): Composite ranks them higher than Custom
        - **Negative** (blue): Custom ranks them higher than Composite
        - **Near Zero** (white): Both systems agree
        
        **Why Rankings Differ**:
        - **Custom** emphasizes efficiency and ball security (formula-driven)
        - **Composite** learns from QBR/ELO which include team context, win probability, and opponent strength
        - QBs ranked higher by Custom: Efficient, low turnovers, good under pressure
        - QBs ranked higher by Composite: High volume, team success, clutch moments valued by QBR/ELO
        """)
        
        # Biggest disagreements
        st.subheader("Biggest Disagreements")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Custom Rates HIGHER** (top 10)")
            higher_custom = comparison_df.copy()
            higher_custom['diff'] = higher_custom['custom_rating'] - (higher_custom['composite_rating'] * 0.5)  # Normalize scales
            higher_custom = higher_custom.nlargest(10, 'diff')[['display_name', 'season', 'custom_rating', 'composite_rating', 'efficiency_score', 'ball_security_score']]
            st.dataframe(higher_custom.style.format({
                'custom_rating': '{:.1f}',
                'composite_rating': '{:.1f}',
                'efficiency_score': '{:.1f}',
                'ball_security_score': '{:.1f}'
            }), use_container_width=True)
            st.caption("These QBs excel in efficiency and ball security")
        
        with col2:
            st.markdown("**Composite Rates HIGHER** (top 10)")
            higher_composite = comparison_df.copy()
            higher_composite['diff'] = (higher_composite['composite_rating'] * 0.5) - higher_composite['custom_rating']
            higher_composite = higher_composite.nlargest(10, 'diff')[['display_name', 'season', 'custom_rating', 'composite_rating', 'impact_score', 'volume_score']]
            st.dataframe(higher_composite.style.format({
                'custom_rating': '{:.1f}',
                'composite_rating': '{:.1f}',
                'impact_score': '{:.1f}',
                'volume_score': '{:.1f}'
            }), use_container_width=True)
            st.caption("These QBs excel in volume and clutch/team performance")
    else:
        st.warning("No composite rating data available for selected seasons")

# --- Tab 7: Interactive QB Journey Map ---
with tabs[6]:
    st.header("🗺️ Interactive QB Journey Map")
    st.markdown("""
    Trace individual QB careers across seasons. Select multiple QBs to compare their rating trajectories,
    peak performances, and career arcs side-by-side.
    """)
    
    # QB selection with multi-select
    available_qbs = sorted(df['display_name'].unique())
    
    # Suggested notable QBs for quick selection
    suggested_qbs = [qb for qb in ['Patrick Mahomes', 'Josh Allen', 'Joe Burrow', 'Lamar Jackson', 
                                     'Jalen Hurts', 'Aaron Rodgers', 'Tom Brady'] if qb in available_qbs]
    
    selected_qbs = st.multiselect(
        "Select QBs to Compare",
        options=available_qbs,
        default=suggested_qbs[:3] if len(suggested_qbs) >= 3 else suggested_qbs,
        help="Select up to 6 QBs for optimal visualization"
    )
    
    if selected_qbs:
        # Filter data for selected QBs
        journey_df = df[df['display_name'].isin(selected_qbs)].copy()
        journey_df = journey_df.sort_values(['display_name', 'season'])
        
        # Create interactive line chart
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set2[:len(selected_qbs)]
        
        for i, qb in enumerate(selected_qbs):
            qb_data = journey_df[journey_df['display_name'] == qb]
            
            # Main trajectory line
            fig.add_trace(go.Scatter(
                x=qb_data['season'],
                y=qb_data['custom_rating'],
                mode='lines+markers',
                name=qb,
                line=dict(width=3, color=colors[i % len(colors)]),
                marker=dict(size=10, symbol='circle', line=dict(width=2, color='white')),
                hovertemplate=(
                    '<b>%{fullData.name}</b><br>' +
                    'Season: %{x}<br>' +
                    'Rating: %{y:.1f}<br>' +
                    '<extra></extra>'
                )
            ))
            
            # Add peak marker
            peak_idx = qb_data['custom_rating'].idxmax()
            peak_season = qb_data.loc[peak_idx, 'season']
            peak_rating = qb_data.loc[peak_idx, 'custom_rating']
            
            fig.add_trace(go.Scatter(
                x=[peak_season],
                y=[peak_rating],
                mode='markers',
                marker=dict(size=18, symbol='star', color=colors[i % len(colors)], 
                           line=dict(width=2, color='gold')),
                name=f"{qb} Peak",
                showlegend=False,
                hovertemplate=(
                    f'<b>{qb} PEAK</b><br>' +
                    f'Season: {peak_season}<br>' +
                    f'Rating: {peak_rating:.1f}<br>' +
                    '<extra></extra>'
                )
            ))
        
        # Add league average reference line
        league_avg = df.groupby('season')['custom_rating'].mean().reset_index()
        fig.add_trace(go.Scatter(
            x=league_avg['season'],
            y=league_avg['custom_rating'],
            mode='lines',
            name='League Average',
            line=dict(width=2, dash='dash', color='gray'),
            hovertemplate=(
                '<b>League Average</b><br>' +
                'Season: %{x}<br>' +
                'Rating: %{y:.1f}<br>' +
                '<extra></extra>'
            )
        ))
        
        fig.update_layout(
            title="QB Rating Trajectories Over Time",
            xaxis_title="Season",
            yaxis_title="Custom Rating",
            height=600,
            hovermode='closest',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(255,255,255,0.8)"
            ),
            plot_bgcolor='rgba(240,240,240,0.3)',
            xaxis=dict(
                tickmode='linear',
                tick0=journey_df['season'].min(),
                dtick=1,
                gridcolor='lightgray'
            ),
            yaxis=dict(
                gridcolor='lightgray',
                range=[journey_df['custom_rating'].min() - 3, journey_df['custom_rating'].max() + 3]
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Career statistics comparison
        st.subheader("Career Statistics Comparison")
        
        career_stats = []
        for qb in selected_qbs:
            qb_data = journey_df[journey_df['display_name'] == qb]
            
            stats = {
                'QB': qb,
                'Seasons': len(qb_data),
                'Peak Rating': qb_data['custom_rating'].max(),
                'Avg Rating': qb_data['custom_rating'].mean(),
                'Current (2025)': qb_data[qb_data['season'] == 2025]['custom_rating'].values[0] if 2025 in qb_data['season'].values else 'N/A',
                'Archetype': qb_data['archetype'].mode()[0] if not qb_data['archetype'].mode().empty else 'N/A',
                'Total Attempts': qb_data['attempts'].sum()
            }
            career_stats.append(stats)
        
        career_df = pd.DataFrame(career_stats)
        
        # Format the dataframe
        st.dataframe(career_df.style.format({
            'Peak Rating': '{:.1f}',
            'Avg Rating': '{:.1f}',
            'Current (2025)': lambda x: f'{x:.1f}' if isinstance(x, (int, float)) else x,
            'Total Attempts': '{:,.0f}'
        }), use_container_width=True)
        
        # Playstyle evolution (for single QB selection)
        if len(selected_qbs) == 1:
            st.subheader(f"{selected_qbs[0]} - Playstyle Evolution")
            
            qb_journey = journey_df[journey_df['display_name'] == selected_qbs[0]]
            
            playstyle_cols = ['playmaking_rating', 'aggression_rating', 'accuracy_rating',
                            'ball_security_rating', 'pocket_presence_rating', 'mobility_rating']
            
            fig_evolution = go.Figure()
            
            playstyle_colors = {
                'playmaking_rating': '#FF6B6B',
                'aggression_rating': '#4ECDC4',
                'accuracy_rating': '#45B7D1',
                'ball_security_rating': '#96CEB4',
                'pocket_presence_rating': '#FFEAA7',
                'mobility_rating': '#DDA15E'
            }
            
            for col in playstyle_cols:
                display_name = col.replace('_rating', '').replace('_', ' ').title()
                
                fig_evolution.add_trace(go.Scatter(
                    x=qb_journey['season'],
                    y=qb_journey[col],
                    mode='lines+markers',
                    name=display_name,
                    line=dict(width=2.5, color=playstyle_colors[col]),
                    marker=dict(size=8)
                ))
            
            fig_evolution.update_layout(
                title=f"{selected_qbs[0]} Playstyle Ratings Evolution",
                xaxis_title="Season",
                yaxis_title="Playstyle Rating",
                height=500,
                hovermode='x unified',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01,
                    bgcolor="rgba(255,255,255,0.9)"
                ),
                xaxis=dict(tickmode='linear', dtick=1)
            )
            
            st.plotly_chart(fig_evolution, use_container_width=True)
            
    else:
        st.info("Please select at least one QB to view their journey.")

# Footer
st.markdown("---")
st.markdown("""
**Data Source**: Play-by-play data from nflfastR (2010-2025)  
**Minimum Qualification**: 150 pass attempts per season  
**Rating Scale**: 50-100 (F to A+, like traditional grading)  
**Methodology**: Transparent formula-based system emphasizing efficiency, impact, consistency, volume, ball security, and pressure performance
""")
