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
    """Load QB ratings data from CSV files (optimized for cloud deployment)."""
    try:
        # Load custom ratings
        df = pd.read_csv('modeling/models/custom_qb_ratings.csv')
        
        # Remove duplicates - keep the entry with more attempts for each player_id + season combination
        df = df.sort_values('attempts', ascending=False).drop_duplicates(subset=['player_id', 'season'], keep='first')
        
        # Load composite ratings from ML model
        composite_df = pd.read_csv('modeling/models/qb_composite_ratings.csv')
        composite_df = composite_df[['player_id', 'season', 'composite_rating', 'predicted_qbr', 'predicted_elo']]
        
        # Merge composite ratings
        df = df.merge(composite_df, on=['player_id', 'season'], how='left')
        
        # Calculate yards per attempt from CSV data (no database needed for cloud deployment)
        if 'pass_yards_per_game' in df.columns and 'attempts' in df.columns:
            df['yards_per_attempt'] = (df['pass_yards_per_game'] * 17.0) / df['attempts']
        else:
            df['yards_per_attempt'] = 7.0  # Fallback
        
        # Use player_name from CSV as display name
        df['display_name'] = df['player_name']
        
        # Calculate archetypes
        df['archetype'] = df.apply(assign_custom_archetype, axis=1)
        
        # For last refresh, use CSV file modification time
        last_refresh = None
        csv_path = Path('modeling/models/custom_qb_ratings.csv')
        if csv_path.exists():
            import os
            from datetime import datetime
            mtime = os.path.getmtime(csv_path)
            last_refresh = datetime.fromtimestamp(mtime).isoformat()
        
        return df, last_refresh
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        raise

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
    - **Efficiency (30%)**: Total Pass EPA (50%) + Success Rate (30%) + CPOE (20%)
    - **Impact (17.5%)**: Total WPA (50%) + High Leverage EPA (30%) + TD Rate (20%)
    - **Consistency (22.5%)**: 3rd Down Success (40%) + Red Zone EPA (35%) + Completion % (25%)
    - **Volume (10%)**: Pass Yards/Game (40%) + Rush Yards/Game (40%) + Total TDs/Game (20%)
    - **Ball Security (10%)**: Turnover Rate inverted (40%) + Sack Rate inverted (60%)
    - **Pressure Performance (10%)**: EPA Under Pressure (100%)
    
    **Data Source**: Play-by-play data (2010-2025) aggregated to season level. Minimum 150 attempts per season.
    """)

# --- Streamlit App ---
st.set_page_config(page_title="Custom NFL QB Rankings", layout="wide")

# Load data
df, last_refresh = load_data()

# Header with last updated info
col1, col2 = st.columns([3, 1])
with col1:
    st.title("Custom NFL QB Rankings (2010-2025)")
with col2:
    if last_refresh:
        from datetime import datetime
        refresh_dt = datetime.fromisoformat(last_refresh)
        st.caption(f"Data as of: {refresh_dt.strftime('%Y-%m-%d')}")

tabs = st.tabs(["Best Current QBs", "Top QBs by Year", "Player Career View", "Component Scores Analysis", "EPA vs CPOE Scatter", "Sack Rate vs Y/A Scatter", "Custom vs ML Composite", "Interactive QB Journey Map", "Contract Value Analysis"])

# --- Tab 1: Best Current QBs (Current Players Ranked by Weighted Recent + Career Performance) ---
with tabs[0]:
    st.header("Best Quarterbacks Right Now")
    st.markdown("**If you had to draft a QB today, who would you pick?**")
    st.markdown("Rankings combine recent performance (2024-2025 heavily weighted) with full career history for current active players.")
    
    st.info("ℹ️ **Rating Scale:** All ratings are normalized across 2010-2025 (15 years) on a 50-100 scale. **100 = highest value**, 50 = lowest.")
    
    try:
        # Define current players as those who played in 2024 or 2025
        current_seasons = [2024, 2025]
        current_players = df[df['season'].isin(current_seasons)]['player_name'].unique()
        current_df = df[df['player_name'].isin(current_players)].copy()
        
        # Calculate weighted rating for each QB
        rankings = []
        
        for qb in current_players:
            qb_data = current_df[current_df['player_name'] == qb].sort_values('season')
            
            if len(qb_data) == 0:
                continue
            
            # Get most recent season data
            latest_season = qb_data.iloc[-1]
            
            # Separate recent (2024-2025) and historical data
            recent_data = qb_data[qb_data['season'].isin([2024, 2025])]
            historical_data = qb_data[~qb_data['season'].isin([2024, 2025])]
            
            # Calculate weighted components
            if len(recent_data) > 0:
                # Recent performance (70% weight) - average of 2024-2025
                recent_rating = recent_data['custom_rating'].mean()
                recent_weight = 0.70
            else:
                recent_rating = 0
                recent_weight = 0
            
            # Career performance (30% weight)
            if len(historical_data) > 0:
                # Weight more recent historical years more (last 3 years = 50%, rest = 50%)
                last_3_years = historical_data[historical_data['season'] >= 2021]
                older_years = historical_data[historical_data['season'] < 2021]
                
                if len(last_3_years) > 0 and len(older_years) > 0:
                    career_rating = (last_3_years['custom_rating'].mean() * 0.7 + 
                                   older_years['custom_rating'].mean() * 0.3)
                elif len(last_3_years) > 0:
                    career_rating = last_3_years['custom_rating'].mean()
                else:
                    career_rating = older_years['custom_rating'].mean()
                
                career_weight = 0.30
            else:
                # No historical data means rookie/new player - use only recent
                career_rating = recent_rating
                career_weight = 0.0
                recent_weight = 1.0
            
            # Final weighted rating
            if recent_weight + career_weight > 0:
                weighted_rating = (recent_rating * recent_weight + career_rating * career_weight)
            else:
                weighted_rating = latest_season['custom_rating']
            
            # Get additional context
            total_seasons = len(qb_data)
            total_attempts = qb_data['attempts'].sum()
            seasons_played = sorted(qb_data['season'].unique())
            
            rankings.append({
                'player_name': qb,
                'weighted_rating': weighted_rating,
                'recent_rating': recent_rating if len(recent_data) > 0 else latest_season['custom_rating'],
                'career_rating': qb_data['custom_rating'].mean(),
                'latest_season': latest_season['season'],
                'seasons_played': len(seasons_played),
                'first_season': min(seasons_played),
                'last_season': max(seasons_played),
                'total_attempts': total_attempts,
                'archetype': latest_season.get('archetype', 'N/A'),
                'mobility': latest_season['mobility_rating'],
                'aggression': latest_season['aggression_rating'],
                'accuracy': latest_season['accuracy_rating'],
                'ball_security': latest_season['ball_security_rating'],
                'pocket_presence': latest_season['pocket_presence_rating'],
                'playmaking': latest_season['playmaking_rating']
            })
        
        # Create rankings dataframe
        rankings_df = pd.DataFrame(rankings).sort_values('weighted_rating', ascending=False).reset_index(drop=True)
        rankings_df['rank'] = range(1, len(rankings_df) + 1)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_seasons = st.slider("Minimum Seasons Played", 1, int(rankings_df['seasons_played'].max()), 1, key="min_seasons_filter")
        
        with col2:
            min_attempts = st.slider("Minimum Career Attempts", 0, int(rankings_df['total_attempts'].max()), 500, step=100, key="min_attempts_filter")
        
        with col3:
            show_top_n = st.slider("Show Top N QBs", 10, 50, 25, step=5, key="show_top_n")
        
        # Apply filters
        filtered_rankings = rankings_df[
            (rankings_df['seasons_played'] >= min_seasons) &
            (rankings_df['total_attempts'] >= min_attempts)
        ].head(show_top_n)
        
        # Display rankings table
        st.markdown("---")
        st.subheader(f"Top {len(filtered_rankings)} Current QBs")
        
        display_df = filtered_rankings[[
            'rank', 'player_name', 'weighted_rating', 'recent_rating', 'career_rating',
            'seasons_played', 'archetype', 'playmaking', 'aggression', 'accuracy', 
            'ball_security', 'pocket_presence', 'mobility'
        ]].copy()
        
        display_df.columns = ['Rank', 'Player', 'Overall Score', 
                             '2024-25 (70%)', 'Career (30%)', 
                             'Seasons', 'Playstyle', 
                             'Playmaking', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket', 'Mobility']
        
        # Round numeric columns to 1 decimal
        display_df['Overall Score'] = display_df['Overall Score'].round(1)
        display_df['2024-25 (70%)'] = display_df['2024-25 (70%)'].round(1)
        display_df['Career (30%)'] = display_df['Career (30%)'].round(1)
        display_df['Playmaking'] = display_df['Playmaking'].round(1)
        display_df['Aggression'] = display_df['Aggression'].round(1)
        display_df['Accuracy'] = display_df['Accuracy'].round(1)
        display_df['Ball Security'] = display_df['Ball Security'].round(1)
        display_df['Pocket'] = display_df['Pocket'].round(1)
        display_df['Mobility'] = display_df['Mobility'].round(1)
        
        # Style the dataframe using RdYlGn gradient like Top 32 QBs tab
        gradient_cols = ['Overall Score', '2024-25 (70%)', 'Career (30%)', 
                        'Playmaking', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket', 'Mobility']
        
        styled_df = display_df.style\
            .background_gradient(subset=gradient_cols, cmap='RdYlGn', vmin=50, vmax=100)\
            .format({
                'Overall Score': '{:.1f}',
                '2024-25 (70%)': '{:.1f}',
                'Career (30%)': '{:.1f}',
                'Playmaking': '{:.1f}',
                'Aggression': '{:.1f}',
                'Accuracy': '{:.1f}',
                'Ball Security': '{:.1f}',
                'Pocket': '{:.1f}',
                'Mobility': '{:.1f}'
            })
        
        st.dataframe(styled_df, use_container_width=True, height=600)
        
        # Visualizations
        st.markdown("---")
        st.subheader("Rankings Insights")
        
        # Career trajectory: Recent vs Career Average with range visualization
        filtered_rankings['trajectory'] = filtered_rankings['recent_rating'] - filtered_rankings['career_rating']
        
        # Prepare data - top 20 by ranking
        trajectory_data = filtered_rankings.head(20).sort_values('weighted_rating', ascending=True).copy()
        
        fig_trajectory = go.Figure()
        
        # Add range lines (career to recent)
        for idx, row in trajectory_data.iterrows():
            color = 'green' if row['trajectory'] >= 0 else 'red'
            fig_trajectory.add_trace(go.Scatter(
                x=[row['career_rating'], row['recent_rating']],
                y=[row['player_name'], row['player_name']],
                mode='lines',
                line=dict(color=color, width=2),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Add career average dots
        fig_trajectory.add_trace(go.Scatter(
            x=trajectory_data['career_rating'],
            y=trajectory_data['player_name'],
            mode='markers',
            marker=dict(size=8, color='gray', symbol='circle'),
            name='Career Avg',
            hovertemplate='<b>%{y}</b><br>Career Average: %{x:.1f}<extra></extra>'
        ))
        
        # Add recent performance dots
        trajectory_data['status'] = trajectory_data['trajectory'].apply(
            lambda x: 'Improving ↑' if x > 0 else 'Declining ↓' if x < 0 else 'Steady →'
        )
        
        fig_trajectory.add_trace(go.Scatter(
            x=trajectory_data['recent_rating'],
            y=trajectory_data['player_name'],
            mode='markers',
            marker=dict(
                size=10, 
                color=trajectory_data['trajectory'],
                colorscale='RdYlGn',
                cmid=0,
                symbol='circle',
                line=dict(width=1, color='DarkSlateGrey')
            ),
            name='Recent (2024-25)',
            hovertemplate='<b>%{y}</b><br>' +
                         'Recent Rating: %{x:.1f}<br>' +
                         'Career Avg: ' + trajectory_data['career_rating'].apply(lambda x: f'{x:.1f}').astype(str) + '<br>' +
                         'Change: ' + trajectory_data['trajectory'].apply(lambda x: f'{x:+.1f}').astype(str) + '<br>' +
                         'Overall Score: ' + trajectory_data['weighted_rating'].apply(lambda x: f'{x:.1f}').astype(str) +
                         '<extra></extra>',
            customdata=trajectory_data[['career_rating', 'trajectory', 'weighted_rating']]
        ))
        
        fig_trajectory.update_layout(
            title='Recent Form vs Career Average (Top 20 QBs)',
            xaxis_title='Rating',
            yaxis_title='',
            height=700,
            hovermode='closest',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_trajectory, use_container_width=True)
        
        st.caption("**Gray dot** = Career average | **Colored dot** = Recent (2024-25) | **Green line** = Improving | **Red line** = Declining")
        
        # New row: Attribute hexbin and Prime years analysis
        viz_col3, viz_col4 = st.columns(2)
        
        with viz_col3:
            # Playstyle attribute heatmap
            top_qbs = filtered_rankings.head(15).copy()
            heatmap_data = top_qbs[['player_name', 'playmaking', 'aggression', 'accuracy', 'ball_security', 'pocket_presence', 'mobility']].set_index('player_name')
            heatmap_data.columns = ['Playmaking', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket', 'Mobility']
            
            fig_heat = px.imshow(
                heatmap_data.T,
                labels=dict(x="Player", y="Attribute", color="Rating"),
                title="Top 15 QBs - Attribute Strengths",
                color_continuous_scale='RdYlGn',
                aspect="auto"
            )
            fig_heat.update_xaxes(side="bottom", tickangle=-45)
            fig_heat.update_layout(height=400)
            st.plotly_chart(fig_heat, use_container_width=True)
            
            st.caption("**Darker green** = Strength | **Yellow/Red** = Weakness")
        
        with viz_col4:
            # Prime vs Past Prime analysis
            filtered_rankings['prime_status'] = filtered_rankings['seasons_played'].apply(
                lambda x: 'Rookie/2nd Year' if x <= 2 else 
                         ('Prime Years (3-10)' if x <= 10 else 'Veteran (11+)')
            )
            
            fig_prime = px.box(
                filtered_rankings,
                x='prime_status',
                y='weighted_rating',
                color='prime_status',
                points='all',
                hover_data={
                    'player_name': True,
                    'weighted_rating': ':.1f',
                    'seasons_played': True,
                    'prime_status': False
                },
                labels={
                    'prime_status': 'Career Stage',
                    'weighted_rating': 'Overall Score',
                    'player_name': 'Player'
                },
                title='Performance by Career Stage',
                color_discrete_map={
                    'Rookie/2nd Year': '#3498db',
                    'Prime Years (3-10)': '#2ecc71',
                    'Veteran (11+)': '#e67e22'
                }
            )
            fig_prime.update_layout(height=400, showlegend=False)
            fig_prime.update_xaxes(tickangle=-20)
            st.plotly_chart(fig_prime, use_container_width=True)
            
            st.caption("**Distribution shows**: Are veterans maintaining elite play? Are young QBs outperforming expectations?")
        
        # Individual QB comparison
        st.markdown("---")
        st.subheader("Compare QBs")
        
        compare_qbs = st.multiselect(
            "Select QBs to compare",
            options=filtered_rankings['player_name'].tolist(),
            default=filtered_rankings['player_name'].head(3).tolist(),
            key="compare_qbs"
        )
        
        if compare_qbs:
            compare_data = filtered_rankings[filtered_rankings['player_name'].isin(compare_qbs)]
            
            # Radar chart
            categories = ['Playmaking', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket', 'Mobility']
            
            fig_radar = go.Figure()
            
            for _, qb in compare_data.iterrows():
                fig_radar.add_trace(go.Scatterpolar(
                    r=[qb['playmaking'], qb['aggression'], qb['accuracy'], qb['ball_security'], qb['pocket_presence'], qb['mobility']],
                    theta=categories,
                    fill='toself',
                    name=qb['player_name']
                ))
            
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[50, 100])),
                showlegend=True,
                title='QB Attribute Comparison',
                height=500
            )
            
            st.plotly_chart(fig_radar, use_container_width=True)
            
            # Stats comparison table
            compare_table = compare_data[[
                'rank', 'player_name', 'weighted_rating', 'recent_rating', 'career_rating',
                'seasons_played', 'total_attempts', 'archetype'
            ]].copy()
            
            compare_table.columns = ['Rank', 'Player', 'Overall', '2024-25', 'Career', 'Seasons', 'Att', 'Style']
            compare_table['Overall'] = compare_table['Overall'].round(1)
            compare_table['2024-25'] = compare_table['2024-25'].round(1)
            compare_table['Career'] = compare_table['Career'].round(1)
            
            st.dataframe(compare_table, use_container_width=True, hide_index=True)
        
        # Methodology explanation
        with st.expander("📊 How Rankings Are Calculated"):
            st.markdown("""
            ### Weighted Rating Formula
            
            **Overall Score = (Recent Performance × 70%) + (Career Performance × 30%)**
            
            **Recent Performance (70% weight)**:
            - Average rating from 2024-2025 seasons
            - Reflects current form and abilities
            
            **Career Performance (30% weight)**:
            - Weighted average of all seasons before 2024
            - Recent years (2021-2023) weighted 70%
            - Older years (pre-2021) weighted 30%
            
            ### Why This Approach?
            
            - **Recent performance matters most** - A QB's last two seasons best predict future success
            - **Career context is important** - Consistent excellence across years vs one-year wonders
            - **Experience counts** - Battle-tested QBs with proven track records ranked appropriately
            - **Fair to rookies** - Young players aren't overly penalized for lack of history
            
            ### Current Player Definition
            
            Players who appeared in the 2024 or 2025 season are considered "current."
            
            ### Use Case
            
            This ranking answers: **"If I'm building a team today and can choose any QB, who should I pick?"**
            
            Perfect for:
            - GM/Team building decisions
            - Fantasy draft rankings
            - Trade value assessments
            - Understanding QB market value
            """)
    
    except Exception as e:
        st.error(f"Error calculating current QB rankings: {e}")
        st.exception(e)

# --- Tab 2: Top 32 QBs Table ---
with tabs[1]:
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

# --- Tab 3: Player Career Ratings Table ---
with tabs[2]:
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

# --- Tab 4: Component Scores Analysis ---
with tabs[3]:
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
        'efficiency_score': 'Efficiency (30%)',
        'impact_score': 'Impact (17.5%)',
        'consistency_score': 'Consistency (22.5%)',
        'volume_score': 'Volume (10%)',
        'ball_security_score': 'Ball Security (10%)',
        'pressure_score': 'Pressure (10%)'
    }
    
    table = display_df[show_cols].rename(columns=rename_dict)
    gradient_cols = [
        'Overall', 'Efficiency (30%)', 'Impact (17.5%)', 'Consistency (22.5%)',
        'Volume (10%)', 'Ball Security (10%)', 'Pressure (10%)'
    ]
    format_dict = {col: "{:.1f}" for col in gradient_cols}
    
    styled = table.style.format(format_dict).background_gradient(
        subset=gradient_cols, cmap='RdYlGn', vmin=50, vmax=100
    )
    st.dataframe(styled, use_container_width=True, height=800)
    
    st.markdown("""
    ### Component Score Interpretation
    
    Each component is normalized to a 50-100 scale and weighted to create the overall rating:
    
    - **Efficiency (30%)**: How much value created per play (EPA, Success Rate, CPOE)
    - **Impact (17.5%)**: Big plays and clutch performance (WPA, High Leverage EPA, TD Rate)
    - **Consistency (22.5%)**: Performance in key situations (3rd downs, red zone, completion %)
    - **Volume (10%)**: Raw production per game (pass yards/game, rush yards/game, total TDs/game)
    - **Ball Security (10%)**: Avoiding mistakes (low turnover rate, low sack rate)
    - **Pressure Performance (10%)**: Effectiveness when under pressure
    
    **Higher scores are better** - Each component ranges from 50 (worst) to 100 (best).
    """)

# --- Tab 5: EPA vs CPOE Scatter Plot ---
with tabs[4]:
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

# --- Tab 6: Sack Rate vs Yards/Attempt Scatter Plot ---
with tabs[5]:
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
        
    else:
        agg_df = pd.DataFrame()
    
    if not agg_df.empty:
        # Invert sack rate so lower values are on the right (elite in top-right)
        agg_df['inv_sack_rate'] = -agg_df['sack_rate']
        
        fig2 = px.scatter(
            agg_df,
            x='inv_sack_rate',
            y='yards_per_attempt',
            text='display_name',
            color='custom_rating',
            color_continuous_scale='RdYlGn',
            range_color=[50, 100],
            labels={
                'inv_sack_rate': 'Sack Rate (Lower is Right)',
                'yards_per_attempt': 'Yards per Attempt',
                'custom_rating': 'Custom Rating'
            },
            hover_data=['custom_rating', 'sack_rate', 'yards_per_attempt', 'attempts']
        )
        fig2.update_traces(textposition='top center', marker=dict(size=14, line=dict(width=1, color='DarkSlateGrey')))
        
        # Add quadrant lines at median
        median_inv_sack = agg_df['inv_sack_rate'].median()
        median_ya = agg_df['yards_per_attempt'].median()
        fig2.add_shape(type="line", x0=median_inv_sack, x1=median_inv_sack, 
                       y0=agg_df['yards_per_attempt'].min(), y1=agg_df['yards_per_attempt'].max(),
                       line=dict(color="gray", dash="dash"))
        fig2.add_shape(type="line", x0=agg_df['inv_sack_rate'].min(), x1=agg_df['inv_sack_rate'].max(), 
                       y0=median_ya, y1=median_ya,
                       line=dict(color="gray", dash="dash"))
        
        # Add quadrant labels (elite in top-right: low sacks = right side when inverted)
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
        
        fig2.update_layout(height=700, xaxis_title="Sack Rate % (Lower is Right →)", 
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

# --- Tab 7: Custom vs ML Composite Comparison ---
with tabs[6]:
    st.header("Custom Rating vs ML Composite Rating")
    
    st.markdown("""
    ### Comparing Two Approaches to QB Rating
    
    **Custom Rating (Formula-Based)**:
    - Transparent weighted formula: 30% Efficiency + 17.5% Impact + 22.5% Consistency + 10% Volume + 10% Ball Security + 10% Pressure
    - Scale: 50-100 (traditional grading)
    - Philosophy: Balances efficiency with situational performance, ball security, and pressure execution
    
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

# --- Tab 8: Interactive QB Journey Map ---
with tabs[7]:
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

# --- Tab 9: Contract Value Analysis ---
with tabs[8]:
    st.header("💰 QB Contract Value Analysis")
    st.markdown("""
    Compare QB performance against what their salary suggests they should deliver. QBs performing above 
    their expected rating provide **good value**, while those below are **overpaid**.
    """)
    
    try:
        # Load contract value data from CSV (optimized for cloud deployment)
        contract_df = pd.read_csv('modeling/models/qb_contract_value.csv')
        
        # Year filter
        all_contract_years = sorted(contract_df['season'].unique(), reverse=True)
        selected_year = st.selectbox(
            "Select Season", 
            options=all_contract_years, 
            index=0 if len(all_contract_years) > 0 else None,
            key="contract_year_filter"
        )
        
        year_data = contract_df[contract_df['season'] == selected_year].copy()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("QBs Analyzed", len(year_data))
        with col2:
            avg_salary = year_data['salary_millions'].mean()
            st.metric("Avg Salary", f"${avg_salary:.1f}M")
        with col3:
            avg_outperform = year_data['value_over_expected'].mean()
            st.metric("Avg Value", f"{avg_outperform:+.1f} pts", 
                     delta_color="normal" if avg_outperform > 0 else "inverse")
        with col4:
            elite_value_count = len(year_data[year_data['value_category'] == 'Elite Value'])
            st.metric("Elite Value QBs", elite_value_count)
        
        st.markdown("---")
        
        # Best and Worst Value Tables
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🟢 Best Contract Value (Outperforming)")
            best_value = year_data.nlargest(10, 'value_over_expected')[[
                'player_name', 'team', 'actual_rating', 'expected_rating', 'salary_millions', 'value_over_expected', 'value_pct'
            ]].reset_index(drop=True)
            best_value.index = best_value.index + 1
            best_value.columns = ['Player', 'Team', 'Actual', 'Expected', 'Salary ($M)', 'Difference', '% Better']
            
            # Color code the dataframe
            def highlight_best(row):
                if row['Difference'] > 10:
                    return ['background-color: #d4edda'] * len(row)
                elif row['Difference'] > 5:
                    return ['background-color: #d1ecf1'] * len(row)
                else:
                    return [''] * len(row)
            
            st.dataframe(
                best_value.style.apply(highlight_best, axis=1).format({
                    'Actual': '{:.1f}',
                    'Expected': '{:.1f}',
                    'Salary ($M)': '${:.1f}M',
                    'Difference': '{:+.1f}',
                    '% Better': '{:+.1f}%'
                }),
                use_container_width=True,
                height=400
            )
        
        with col2:
            st.subheader("🔴 Worst Contract Value (Underperforming)")
            worst_value = year_data.nsmallest(10, 'value_over_expected')[[
                'player_name', 'team', 'actual_rating', 'expected_rating', 'salary_millions', 'value_over_expected', 'value_pct'
            ]].reset_index(drop=True)
            worst_value.index = worst_value.index + 1
            worst_value.columns = ['Player', 'Team', 'Actual', 'Expected', 'Salary ($M)', 'Difference', '% Worse']
            
            # Color code the dataframe
            def highlight_worst(row):
                if row['Difference'] < -10:
                    return ['background-color: #f8d7da'] * len(row)
                elif row['Difference'] < -5:
                    return ['background-color: #fff3cd'] * len(row)
                else:
                    return [''] * len(row)
            
            st.dataframe(
                worst_value.style.apply(highlight_worst, axis=1).format({
                    'Actual': '{:.1f}',
                    'Expected': '{:.1f}',
                    'Salary ($M)': '${:.1f}M',
                    'Difference': '{:+.1f}',
                    '% Worse': '{:+.1f}%'
                }),
                use_container_width=True,
                height=400
            )
        
        st.markdown("---")
        
        # Scatter plot: Actual vs Expected Rating
        st.subheader("Actual vs Expected Performance")
        
        # Add diagonal line data for "fair value"
        min_rating = year_data[['actual_rating', 'expected_rating']].min().min()
        max_rating = year_data[['actual_rating', 'expected_rating']].max().max()
        
        fig = go.Figure()
        
        # Add diagonal "fair value" line
        fig.add_trace(go.Scatter(
            x=[min_rating, max_rating],
            y=[min_rating, max_rating],
            mode='lines',
            name='Fair Value',
            line=dict(color='gray', dash='dash', width=2),
            hoverinfo='skip'
        ))
        
        # Add QB data points
        fig.add_trace(go.Scatter(
            x=year_data['expected_rating'],
            y=year_data['actual_rating'],
            mode='markers+text',
            name='QBs',
            marker=dict(
                size=12,
                color=year_data['value_over_expected'],
                colorscale='RdYlGn',
                colorbar=dict(title="Value<br>Over<br>Expected"),
                line=dict(width=1, color='DarkSlateGrey'),
                cmin=-15,
                cmax=15
            ),
            text=year_data['player_name'],
            textposition='top center',
            textfont=dict(size=9),
            customdata=year_data[['team', 'salary_millions', 'value_over_expected', 'value_pct']],
            hovertemplate='<b>%{text}</b><br>' +
                          'Team: %{customdata[0]}<br>' +
                          'Salary: $%{customdata[1]:.1f}M<br>' +
                          'Expected Rating: %{x:.1f}<br>' +
                          'Actual Rating: %{y:.1f}<br>' +
                          'Value Over Expected: %{customdata[2]:+.1f}<br>' +
                          'Performance: %{customdata[3]:+.1f}%<br>' +
                          '<extra></extra>'
        ))
        
        fig.update_layout(
            xaxis_title="Expected Rating (Based on Salary)",
            yaxis_title="Actual Rating (Performance)",
            hovermode='closest',
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Value category breakdown
        st.markdown("---")
        st.subheader("Value Category Distribution")
        
        category_order = ['Elite Value', 'Good Value', 'Fair Value', 'Overpaid', 'Severely Overpaid']
        category_counts = year_data['value_category'].value_counts().reindex(category_order, fill_value=0)
        
        fig_bar = px.bar(
            x=category_counts.index,
            y=category_counts.values,
            labels={'x': 'Value Category', 'y': 'Number of QBs'},
            color=category_counts.index,
            color_discrete_map={
                'Elite Value': '#2ecc71',
                'Good Value': '#27ae60',
                'Fair Value': '#f39c12',
                'Overpaid': '#e74c3c',
                'Severely Overpaid': '#c0392b'
            }
        )
        
        fig_bar.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Explanation
        with st.expander("ℹ️ How Contract Value is Calculated"):
            st.markdown("""
            **Expected Rating Approach:**
            
            1. For each season, we calculate what rating a QB *should* have based on their salary
            2. Higher paid QBs are expected to perform better (linear relationship within each season)
            3. **Value Over Expected = Actual Rating - Expected Rating**
            
            **Examples:**
            - QB paid $55M should perform at 85 → actually performs at 75 → **-10 (Overpaid)**
            - QB paid $5M should perform at 65 → actually performs at 80 → **+15 (Elite Value)**
            
            **Value Categories:**
            - **Elite Value** (>+10 pts): Performing 10+ rating points above expectation
            - **Good Value** (+5 to +10 pts): Solid performance above salary level
            - **Fair Value** (-5 to +5 pts): Performing as expected for their salary
            - **Overpaid** (-10 to -5 pts): Underperforming relative to salary
            - **Severely Overpaid** (<-10 pts): Significantly underperforming for their contract
            
            This approach is intuitive: you can directly see if a QB is performing better or worse than their contract suggests they should.
            """)
    
    except Exception as e:
        st.error(f"Error loading contract value data: {e}")
        st.info("Make sure qb_contract_value.csv exists in modeling/models/ directory.")

# Footer
st.markdown("---")
st.markdown("""
**Data Source**: Play-by-play data from nflfastR (2010-2025)  
**Minimum Qualification**: 150 pass attempts per season  
**Rating Scale**: 50-100 (F to A+, like traditional grading)  
**Methodology**: Transparent formula-based system emphasizing efficiency, impact, consistency, volume, ball security, and pressure performance
""")
