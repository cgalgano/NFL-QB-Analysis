import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from math import pi

# Page configuration
st.set_page_config(
    page_title="NFL QB Top 30 Analysis",
    page_icon="🏈",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 20px;
    }
    h2 {
        color: #2c3e50;
        padding-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data(season_filter="All Years"):
    if season_filter == "All Years":
        # Load aggregate rankings (original format - one row per QB)
        df = pd.read_csv('qb_rankings_2010_2025.csv')
    else:
        # Load per-season data and filter
        df = pd.read_csv('qb_rankings_by_season.csv')
        
        # Handle multiple years (list) or single year (string)
        if isinstance(season_filter, list):
            # Handle empty list
            if not season_filter:
                # Fall back to all years
                df = pd.read_csv('qb_rankings_2010_2025.csv')
                return load_data("All Years")
            
            # Convert list elements to int if they're strings
            years = [int(y) if isinstance(y, str) else y for y in season_filter]
            df = df[df['season'].isin(years)]
            
            # Check if we have data after filtering
            if len(df) == 0:
                st.error(f"No data found for selected years: {season_filter}")
                return load_data("All Years")
            
            # Aggregate across selected years
            agg_funcs = {
                'pass_attempts': 'sum',
                'total_epa_per_play': 'mean',
                'cpoe_mean': 'mean',
                'sack_rate': 'mean',
                'yards_per_attempt': 'mean',
                'td_turnover_ratio': 'mean',
                'success_rate': 'mean',
                'completion_pct': 'mean',
                'rushing_yards': 'sum',
                'interceptions': 'sum',
                'fumbles_lost': 'sum',
                'total_plays': 'sum',
                'total_games': 'sum'
            }
            df = df.groupby('passer_player_name').agg(agg_funcs).reset_index()
        else:
            df = df[df['season'] == int(season_filter)]
        
        # Calculate composite score for filtered data using same weights as notebook
        feature_columns = ['total_epa_per_play', 'cpoe_mean', 'yards_per_attempt', 
                          'td_turnover_ratio', 'completion_pct']
        
        # Normalize features to 0-100
        X_normalized = df[feature_columns].copy()
        for col in feature_columns:
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                X_normalized[col] = 100 * (df[col] - min_val) / (max_val - min_val)
            else:
                X_normalized[col] = 50
        
        # Invert sack_rate (lower is better)
        min_val = df['sack_rate'].min()
        max_val = df['sack_rate'].max()
        if max_val > min_val:
            X_normalized['sack_rate_inv'] = 100 - (100 * (df['sack_rate'] - min_val) / (max_val - min_val))
        else:
            X_normalized['sack_rate_inv'] = 50
        
        # Calculate composite score with updated notebook weights
        feature_weights = {
            'total_epa_per_play': 0.25,
            'cpoe_mean': 0.15,
            'yards_per_attempt': 0.12,
            'td_turnover_ratio': 0.11,
            'completion_pct': 0.09,
            'sack_rate_inv': 0.05
        }
        
        df['composite_score'] = sum(
            X_normalized[col] * feature_weights[col] 
            for col in feature_weights.keys()
        )
        
        # Normalize to 0-100
        min_score = df['composite_score'].min()
        max_score = df['composite_score'].max()
        df['qb_rating'] = 100 * (df['composite_score'] - min_score) / (max_score - min_score)
        
        # Sort and rank
        df = df.sort_values('qb_rating', ascending=False).reset_index(drop=True)
        df['rank'] = range(1, len(df) + 1)
        df['percentile'] = 100 * (len(df) - df['rank'] + 1) / len(df)
    # Get top 30 and calculate playstyle dimensions
    top_30 = df.head(30).copy()
    
    # Calculate raw playstyle metrics first
    top_30['mobility_raw'] = top_30['rushing_yards'] / top_30['total_games']
    top_30['aggression_raw'] = top_30['yards_per_attempt']
    top_30['accuracy_raw'] = top_30['cpoe_mean']
    top_30['turnover_rate'] = ((top_30['interceptions'] + top_30['fumbles_lost']) / top_30['total_plays']) * 100
    
    # PER-SEASON NORMALIZATION (matching Career Progression)
    # When filtered to single season, normalize within that season
    # When "All Years", normalize within the full dataset
    
    if 'season' in df.columns and 'rush_attempts' in df.columns and isinstance(season_filter, (int, str)) and season_filter != "All Years":
        # Single season selected - use ONLY that season for normalization
        # For current year (2025), use lower threshold since season is incomplete
        # For completed seasons, require 300+ pass attempts to ensure qualified starters
        min_attempts = 120 if season_filter == 2025 else 300
        # Filter to the specific season AND pass attempts threshold
        season_df = df[(df['season'] == int(season_filter)) & (df['pass_attempts'] >= min_attempts)].copy()
        
        # Mobility: normalize within season (20+ rush attempts)
        # Calculate normalization pool ONCE for the entire season
        mobility_pool = season_df[season_df['rush_attempts'] >= 20].copy()
        if len(mobility_pool) > 1:
            mobility_pool['rush_ypg'] = mobility_pool['rushing_yards'] / mobility_pool['total_games']
            min_mob = mobility_pool['rush_ypg'].min()
            max_mob = mobility_pool['rush_ypg'].max()
            
            # Normalize each QB's mobility score
            if max_mob > min_mob:
                top_30['mobility_score'] = top_30['mobility_raw'].apply(
                    lambda x: max(0, min(100, 100 * (x - min_mob) / (max_mob - min_mob)))
                )
            else:
                top_30['mobility_score'] = 50
        else:
            top_30['mobility_score'] = 50
        
        # Aggression, Accuracy, Ball Security, Pocket Presence: normalize within season
        min_agg, max_agg = season_df['yards_per_attempt'].min(), season_df['yards_per_attempt'].max()
        if max_agg > min_agg:
            top_30['aggression_score'] = 100 * (top_30['aggression_raw'] - min_agg) / (max_agg - min_agg)
        else:
            top_30['aggression_score'] = 50
        
        min_acc, max_acc = season_df['cpoe_mean'].min(), season_df['cpoe_mean'].max()
        if max_acc > min_acc:
            top_30['accuracy_score'] = 100 * (top_30['accuracy_raw'] - min_acc) / (max_acc - min_acc)
        else:
            top_30['accuracy_score'] = 50
        
        season_df['to_rate'] = ((season_df['interceptions'] + season_df['fumbles_lost']) / season_df['total_plays']) * 100
        min_to, max_to = season_df['to_rate'].min(), season_df['to_rate'].max()
        if max_to > min_to:
            top_30['ball_security_score'] = 100 - (100 * (top_30['turnover_rate'] - min_to) / (max_to - min_to))
        else:
            top_30['ball_security_score'] = 50
        
        min_sack, max_sack = season_df['sack_rate'].min(), season_df['sack_rate'].max()
        if max_sack > min_sack:
            top_30['pocket_presence_score'] = 100 - (100 * (top_30['sack_rate'] - min_sack) / (max_sack - min_sack))
        else:
            top_30['pocket_presence_score'] = 50
    else:
        # All Years or multiple years - normalize within top 30 (original behavior)
        top_30['mobility_score'] = top_30['mobility_raw']
        top_30['aggression_score'] = top_30['aggression_raw']
        top_30['accuracy_score'] = top_30['accuracy_raw']
        top_30['ball_security_score'] = 100 - (top_30['turnover_rate'] * 10)
        top_30['pocket_presence_score'] = 100 - (top_30['sack_rate'] * 2)
        
        playstyle_dims = ['mobility_score', 'aggression_score', 'accuracy_score', 
                          'ball_security_score', 'pocket_presence_score']
        
        for dim in playstyle_dims:
            min_val = top_30[dim].min()
            max_val = top_30[dim].max()
            if max_val > min_val:
                top_30[dim] = 100 * (top_30[dim] - min_val) / (max_val - min_val)
            else:
                top_30[dim] = 50
    
    # Define playstyle_dims for rounding (used later in code)
    playstyle_dims = ['mobility_score', 'aggression_score', 'accuracy_score', 
                      'ball_security_score', 'pocket_presence_score']
    
    # Round playstyle scores to 1 decimal
    for dim in playstyle_dims:
        top_30[dim] = top_30[dim].round(1)
    
    # Round qb_rating to 1 decimal
    top_30['qb_rating'] = top_30['qb_rating'].round(1)
    
    # Assign custom archetypes (matching notebook logic)
    def assign_custom_archetype(row):
        mob = row['mobility_score']
        agg = row['aggression_score']
        acc = row['accuracy_score']
        sec = row['ball_security_score']
        pkt = row['pocket_presence_score']
        
        elite_dims = sum([mob > 75, agg > 75, acc > 75, sec > 75, pkt > 75])
        good_dims = sum([mob > 40, agg > 40, acc > 40, sec > 40, pkt > 40])
        poor_dims = sum([mob < 40, agg < 40, acc < 40, sec < 40, pkt < 40])
        
        if elite_dims >= 4:
            return 'All-Around Superstar'
        elif elite_dims == 3:
            return 'Triple-Threat Elite'
        elif good_dims == 5:
            return 'Complete All-Around QB'
        elif good_dims == 4 and poor_dims <= 1:
            return 'All-Around Threat'
        elif mob > 75 and agg > 75:
            return 'Mobile Downfield Attacker'
        elif mob > 75 and acc > 75:
            return 'Mobile Precision Passer'
        elif agg > 75 and acc > 75:
            return 'Elite Gunslinger'
        elif acc > 75 and sec > 75:
            return 'Efficient Ball Protector'
        elif agg > 75 and pkt > 75:
            return 'Fearless Deep Shooter'
        elif mob > 75 and pkt > 75:
            return 'Dual-Threat Scrambler'
        elif sec > 75 and pkt > 75:
            return 'Poised Protector'
        elif agg > 75 and sec > 75:
            return 'Aggressive Ball Protector'
        elif mob > 75 and sec > 75:
            return 'Mobile Ball Protector'
        elif acc > 75 and pkt > 75:
            return 'Accurate Pocket Commander'
        elif mob > 75 and good_dims < 4:
            return 'Dynamic Rusher'
        elif agg > 75 and good_dims < 4:
            return 'Deep Ball Specialist'
        elif acc > 75 and good_dims < 4:
            return 'Precision Passer'
        elif sec > 75 and good_dims < 4:
            return 'Safe Ball Handler'
        elif pkt > 75 and good_dims < 4:
            return 'Pressure Resistant'
        elif good_dims >= 3:
            return 'Well-Rounded Starter'
        elif poor_dims >= 4:
            return 'Game Manager'
        else:
            return 'Solid Starter'
    
    top_30['custom_archetype'] = top_30.apply(assign_custom_archetype, axis=1)
    
    # Assign primary archetype for color coding
    def get_primary_archetype(row):
        scores = {
            'Mobile Playmaker': row['mobility_score'],
            'Deep Threat': row['aggression_score'],
            'Efficient Passer': row['accuracy_score'],
            'Ball Protector': row['ball_security_score'],
            'Quick-Release Specialist': row['pocket_presence_score']
        }
        return max(scores, key=scores.get)
    
    top_30['primary_archetype'] = top_30.apply(get_primary_archetype, axis=1)
    
    # Add team assignments to both df and top_30
    qb_teams = {
        'J.Allen': 'BUF', 'P.Mahomes': 'KC', 'B.Purdy': 'SF', 'L.Jackson': 'BAL',
        'J.Hurts': 'PHI', 'J.Burrow': 'CIN', 'J.Goff': 'DET', 'D.Prescott': 'DAL',
        'J.Love': 'GB', 'T.Tagovailoa': 'MIA', 'J.Daniels': 'WAS', 'M.Stafford': 'LAR',
        'D.Maye': 'NE', 'T.Brady': 'TB', 'J.Herbert': 'LAC', 'K.Cousins': 'ATL',
        'J.Garoppolo': 'LV', 'T.Bridgewater': 'DET', 'D.Carr': 'NO', 'G.Smith': 'SEA',
        'K.Murray': 'ARI', 'A.Rodgers': 'NYJ', 'B.Mayfield': 'TB', 'C.Stroud': 'HOU',
        'R.Wilson': 'PIT', 'M.Mariota': 'WAS', 'S.Darnold': 'MIN', 'B.Nix': 'DEN',
        'D.Jones': 'NYG', 'R.Tannehill': 'TEN', 'D.Watson': 'CLE', 'T.Lawrence': 'JAX',
        'A.Richardson': 'IND', 'C.Williams': 'CHI', 'B.Young': 'CAR', 'W.Levis': 'TEN',
        'A.O\'Connell': 'NE', 'J.Fields': 'PIT', 'Z.Wilson': 'DEN', 'M.Jones': 'JAX',
        'K.Pickett': 'PHI', 'D.Lock': 'NYG', 'J.Winston': 'CLE', 'T.Huntley': 'MIA',
        'C.Rush': 'DAL', 'B.Rypien': 'LAR', 'M.White': 'MIA', 'J.Stidham': 'DEN',
        'C.McCoy': 'WAS', 'J.Dobbs': 'SF', 'J.Brissett': 'NE', 'T.Heinicke': 'ATL',
        'J.Flacco': 'IND', 'A.Dalton': 'CAR', 'T.Hill': 'NO', 'M.Glennon': 'NYG',
        'N.Mullens': 'MIN', 'C.Wentz': 'LAR', 'B.Hoyer': 'LV', 'G.Minshew': 'LV',
        'T.Siemian': 'CHI', 'J.Johnson': 'BAL', 'C.Hundley': 'ARI', 'S.Howell': 'SEA'
    }
    
    df['team'] = df['passer_player_name'].map(qb_teams)
    top_30['team'] = top_30['passer_player_name'].map(qb_teams)
    
    return df, top_30, qb_teams
# Sidebar for year selection
st.sidebar.header("Filter Options")

# Option to select single year or multiple years
filter_mode = st.sidebar.radio(
    "Filter Mode",
    options=["All Years", "Single Year", "Multiple Years", "Year Range"],
    index=0,
    help="Choose how to filter seasons"
)

if filter_mode == "Single Year":
    selected_year = st.sidebar.selectbox(
        "Select Season",
        options=["2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"],
        index=15,  # Default to 2025
        help="Select a single season"
    )
elif filter_mode == "Multiple Years":
    selected_years = st.sidebar.multiselect(
        "Select Seasons",
        options=["2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"],
        default=["2023", "2024", "2025"],
        help="Select one or more seasons"
    )
    # If no years selected, default to All Years
    if not selected_years:
        selected_year = "All Years"
    else:
        selected_year = selected_years
elif filter_mode == "Year Range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_year = st.selectbox("From", options=list(range(2010, 2026)), index=0)
    with col2:
        end_year = st.selectbox("To", options=list(range(2010, 2026)), index=15)
    
    if start_year > end_year:
        st.sidebar.error("Start year must be <= end year")
        selected_year = "All Years"
    else:
        selected_year = list(range(start_year, end_year + 1))
else:
    selected_year = "All Years"

# Title - format the year display nicely
if selected_year == "All Years":
    year_display = "2010-2025"
elif isinstance(selected_year, list):
    if len(selected_year) == 0:
        year_display = "2010-2025"
    elif len(selected_year) == 1:
        year_display = str(selected_year[0])
    else:
        # Convert to integers for comparison
        years_int = [int(y) if isinstance(y, str) else y for y in selected_year]
        years_sorted = sorted(years_int)
        
        # Check if consecutive
        if len(years_sorted) == len(range(min(years_sorted), max(years_sorted) + 1)):
            # Consecutive years
            year_display = f"{min(years_sorted)}-{max(years_sorted)}"
        else:
            # Non-consecutive years
            year_display = ", ".join(map(str, years_sorted))
else:
    year_display = str(selected_year)

title_text = f"🏈 Top 30 NFL Quarterbacks ({year_display})"
st.title(title_text)
st.markdown("Comprehensive playstyle analysis and rankings")

# Load the data with filter
try:
    df, top_30, qb_teams = load_data(season_filter=selected_year)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📊 Top 30 Rankings", "🔍 Advanced Analysis", "📈 Career Progression"])
    
    # TAB 1: Top 30 Rankings
    with tab1:
        # Section 1: Radar Charts for Top 30
        st.header("Playstyle Profiles - Top 30 QBs")
        st.markdown("Each QB is scored 0-100 on five dimensions: **Mobility**, **Aggression (Deep Ball)**, **Accuracy (CPOE)**, **Ball Security**, and **Pocket Presence**")
        
        # Create radar charts in rows of 5
        categories = ['Mobility', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket Presence']
        
        # Color mapping for primary archetypes
        archetype_colors = {
            'Mobile Playmaker': '#9467bd',
            'Deep Threat': '#d62728',
            'Quick-Release Specialist': '#2ca02c',
            'Ball Protector': '#1f77b4',
            'Efficient Passer': '#ff7f0e'
        }
        
        # NFL team colors and team assignments (2024-2025 season)
        nfl_colors = {
            'ARI': '#97233F', 'ATL': '#A71930', 'BAL': '#241773', 'BUF': '#00338D',
            'CAR': '#0085CA', 'CHI': '#C83803', 'CIN': '#FB4F14', 'CLE': '#311D00',
            'DAL': '#041E42', 'DEN': '#FB4F14', 'DET': '#0076B6', 'GB': '#203731',
            'HOU': '#03202F', 'IND': '#002C5F', 'JAX': '#006778', 'KC': '#E31837',
            'LAC': '#0080C6', 'LAR': '#003594', 'LV': '#000000', 'MIA': '#008E97',
            'MIN': '#4F2683', 'NE': '#002244', 'NO': '#D3BC8D', 'NYG': '#0B2265',
            'NYJ': '#125740', 'PHI': '#004C54', 'PIT': '#FFB612', 'SEA': '#002244',
            'SF': '#AA0000', 'TB': '#D50A0A', 'TEN': '#0C2340', 'WAS': '#5A1414'
        }
        
        # Add team colors to top_30
        top_30['team_color'] = top_30['team'].map(nfl_colors).fillna('#808080')
        
        # Display in rows of 5
        for row in range(6):  # 6 rows for 30 QBs
            cols = st.columns(5)
            for col_idx in range(5):
                qb_idx = row * 5 + col_idx
                if qb_idx < len(top_30):
                    qb = top_30.iloc[qb_idx]
                    
                    # Create radar chart
                    values = [
                        qb['mobility_score'],
                        qb['aggression_score'],
                        qb['accuracy_score'],
                        qb['ball_security_score'],
                        qb['pocket_presence_score']
                    ]
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=values + [values[0]],
                        theta=categories + [categories[0]],
                        fill='toself',
                        line_color=archetype_colors.get(qb['primary_archetype'], '#7f7f7f'),
                        fillcolor=archetype_colors.get(qb['primary_archetype'], '#7f7f7f'),
                        opacity=0.6,
                        name=qb['passer_player_name']
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)
                        ),
                        showlegend=False,
                        title=dict(
                            text=f"#{int(qb['rank'])} {qb['passer_player_name']}<br><sub>{qb['custom_archetype']}</sub>",
                            font=dict(size=11)
                        ),
                        height=300,
                        margin=dict(l=60, r=60, t=60, b=60)
                    )
                    
                    with cols[col_idx]:
                        st.plotly_chart(fig, use_container_width=True)
        
        # Section 2: Detailed Table
        st.header("Detailed Statistics - Top 30 QBs")
        
        display_df = top_30[[
            'rank', 'passer_player_name', 'team', 'custom_archetype', 'qb_rating',
            'mobility_score', 'aggression_score', 'accuracy_score',
            'ball_security_score', 'pocket_presence_score',
            'total_epa_per_play', 'cpoe_mean', 'yards_per_attempt',
            'completion_pct', 'sack_rate'
        ]].copy()
        
        # Round ALL numeric columns to 1 decimal place
        numeric_cols = ['qb_rating', 'mobility_score', 'aggression_score', 'accuracy_score',
                       'ball_security_score', 'pocket_presence_score', 'total_epa_per_play',
                       'cpoe_mean', 'yards_per_attempt', 'completion_pct', 'sack_rate']
        
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].round(1)
        
        # Rename columns for display
        display_df.columns = [
            'Rank', 'QB Name', 'Team', 'Archetype', 'Overall Rating',
            'Mobility', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket Presence',
            'EPA/Play', 'CPOE', 'Yards/Att', 'Comp %', 'Sack %'
        ]
        
        # Format the dataframe to display with 1 decimal place
        styled_df = display_df.style.format({
            'Overall Rating': '{:.1f}',
            'Mobility': '{:.1f}',
            'Aggression': '{:.1f}',
            'Accuracy': '{:.1f}',
            'Ball Security': '{:.1f}',
            'Pocket Presence': '{:.1f}',
            'EPA/Play': '{:.1f}',
            'CPOE': '{:.1f}',
            'Yards/Att': '{:.1f}',
            'Comp %': '{:.1f}',
            'Sack %': '{:.1f}'
        }).background_gradient(
            subset=['Overall Rating', 'Mobility', 'Aggression', 'Accuracy', 
                   'Ball Security', 'Pocket Presence'],
            cmap='RdYlGn'
        )
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=600
        )
        
        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Top 30 Data as CSV",
            data=csv,
            file_name='top_30_qb_analysis.csv',
            mime='text/csv',
        )
        
        # Section 3: Lollipop Chart with Team Colors
        st.header("QB Rankings - Lollipop Chart")
        
        # Create lollipop chart
        fig_lollipop = go.Figure()
        
        # Add stems with team colors
        for idx, row in top_30.iterrows():
            fig_lollipop.add_trace(go.Scatter(
                x=[0, row['qb_rating']],
                y=[row['rank'], row['rank']],
                mode='lines',
                line=dict(color=row['team_color'], width=3),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Add circles with team colors
        fig_lollipop.add_trace(go.Scatter(
            x=top_30['qb_rating'],
            y=top_30['rank'],
            mode='markers',
            marker=dict(
                size=12,
                color=top_30['team_color'],
                line=dict(color='black', width=2)
            ),
            text=[f"{row['passer_player_name']} ({row['team']})" for _, row in top_30.iterrows()],
            hovertemplate='<b>%{text}</b><br>Rating: %{x:.1f}<extra></extra>',
            showlegend=False
        ))
        
        fig_lollipop.update_layout(
            title="Top 30 QB Ratings (0-100 Scale) - Team Colors",
            xaxis_title="QB Rating",
            yaxis_title="",
            yaxis=dict(
                autorange='reversed',
                tickmode='array',
                tickvals=top_30['rank'].tolist(),
                ticktext=[f"#{int(r['rank'])} {r['passer_player_name']} ({r['team']})" for _, r in top_30.iterrows()],
                tickfont=dict(size=10)
            ),
            height=1000,
            showlegend=False,
            hovermode='closest'
        )
        
        st.plotly_chart(fig_lollipop, use_container_width=True)
    
    # TAB 2: Advanced Analysis
    with tab2:
        st.header("🔍 Advanced QB Performance Analysis")
        st.markdown("""
        These visualizations provide deeper insights into quarterback performance using advanced metrics 
        from play-by-play data across the 2010-2025 seasons. Each chart reveals different dimensions of QB effectiveness.
        """)
        
        # Add team colors to full dataframe for scatter plots
        df['team_color'] = df['team'].map(nfl_colors).fillna('#808080')
        
        # Visualization 1: Total EPA vs CPOE
        st.subheader("1️⃣ Total Value Creation vs Accuracy")
        
        with st.expander("ℹ️ What This Chart Shows", expanded=False):
            st.markdown("""
            **Axes Explained:**
            - **X-axis (CPOE)**: Completion % Over Expected - measures passing accuracy adjusted for throw difficulty
            - **Y-axis (Total EPA/Play)**: Expected Points Added per play - combines passing AND rushing value creation
            
            **Why It Matters:**
            - **EPA** = outcome quality (did it help the team win?)
            - **CPOE** = process quality (did the QB execute the throw well?)
            - Elite QBs excel at both: accurate throws that create value
            - This properly credits mobile QBs by including rushing EPA (Lamar Jackson, Josh Allen, Jalen Hurts)
            
            **Quadrant Interpretation:**
            - **Upper-right (Green)**: Elite tier - high value + accurate execution
            - **Upper-left (Yellow)**: Value creators with lower accuracy - often mobile QBs
            - **Lower-right (Yellow)**: Accurate but limited value generation
            - **Lower-left (Red)**: Below average in both dimensions
            """)
        
        # Create EPA vs CPOE scatter plot
        fig1 = go.Figure()
        
        # Add quadrant lines
        median_epa = df['total_epa_per_play'].median()
        median_cpoe = df['cpoe_mean'].median()
        
        fig1.add_hline(y=median_epa, line_dash="dash", line_color="gray", opacity=0.5)
        fig1.add_vline(x=median_cpoe, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Add scatter points with team colors
        fig1.add_trace(go.Scatter(
            x=df['cpoe_mean'],
            y=df['total_epa_per_play'],
            mode='markers+text',
            marker=dict(size=8, color=df['team_color'], opacity=0.8, line=dict(color='white', width=1)),
            text=df['passer_player_name'],
            textposition='top center',
            textfont=dict(size=11, color=df['team_color']),
            hovertemplate='<b>%{text}</b><br>CPOE: %{x:.2f}<br>Total EPA/Play: %{y:.3f}<extra></extra>',
            showlegend=False
        ))
        
        # Add quadrant labels
        x_range = df['cpoe_mean'].max() - df['cpoe_mean'].min()
        y_range = df['total_epa_per_play'].max() - df['total_epa_per_play'].min()
        
        # Upper-right (Elite)
        fig1.add_annotation(
            x=df['cpoe_mean'].max() - x_range*0.02,
            y=df['total_epa_per_play'].max() - y_range*0.02,
            text="Elite<br>(High EPA & CPOE)",
            showarrow=False,
            bgcolor="rgba(0, 255, 0, 0.2)",
            bordercolor="green",
            borderwidth=2,
            font=dict(size=10, color="darkgreen"),
            align="right",
            xanchor="right",
            yanchor="top"
        )
        
        # Upper-left (High EPA, Low CPOE)
        fig1.add_annotation(
            x=df['cpoe_mean'].min() + x_range*0.02,
            y=df['total_epa_per_play'].max() - y_range*0.02,
            text="High EPA<br>Lower CPOE",
            showarrow=False,
            bgcolor="rgba(255, 255, 0, 0.2)",
            bordercolor="orange",
            borderwidth=2,
            font=dict(size=10, color="darkorange"),
            align="left",
            xanchor="left",
            yanchor="top"
        )
        
        # Lower-right (High CPOE, Low EPA)
        fig1.add_annotation(
            x=df['cpoe_mean'].max() - x_range*0.02,
            y=df['total_epa_per_play'].min() + y_range*0.02,
            text="High CPOE<br>Lower EPA",
            showarrow=False,
            bgcolor="rgba(255, 255, 0, 0.2)",
            bordercolor="orange",
            borderwidth=2,
            font=dict(size=10, color="darkorange"),
            align="right",
            xanchor="right",
            yanchor="bottom"
        )
        
        # Lower-left (Below Average)
        fig1.add_annotation(
            x=df['cpoe_mean'].min() + x_range*0.02,
            y=df['total_epa_per_play'].min() + y_range*0.02,
            text="Below Average",
            showarrow=False,
            bgcolor="rgba(255, 0, 0, 0.2)",
            bordercolor="red",
            borderwidth=2,
            font=dict(size=10, color="darkred"),
            align="left",
            xanchor="left",
            yanchor="bottom"
        )
        
        fig1.update_layout(
            title="QB Performance: Total EPA vs CPOE",
            xaxis_title="CPOE (Completion % Over Expected)",
            yaxis_title="Total EPA per Play (Passing + Rushing)",
            height=700,
            hovermode='closest'
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        st.markdown(f"""
        **Key Statistics:**
        - Median Total EPA/play: **{median_epa:.3f}**
        - Median CPOE: **{median_cpoe:.2f}**
        - Total QBs analyzed: **{len(df)}** (≥300 pass attempts)
        """)
        
        # Visualization 2: Sack Rate vs Yards/Attempt
        st.subheader("2️⃣ Pocket Management vs Offensive Aggressiveness")
        
        with st.expander("ℹ️ What This Chart Shows", expanded=False):
            st.markdown("""
            **Axes Explained:**
            - **X-axis (Sack Rate)**: % of dropbacks resulting in sacks - measures pocket awareness and protection
            - **Y-axis (Yards/Attempt)**: Average yards per pass attempt - measures downfield aggressiveness
            
            **Why It Matters:**
            Reveals the trade-off between protection and explosiveness:
            - Some QBs avoid sacks but sacrifice yards (conservative)
            - Others push downfield despite pressure (aggressive)
            - Elite QBs avoid sacks WHILE generating high yards/attempt
            
            **Quadrant Interpretation:**
            - **Upper-left (Green)**: Elite - low sacks, high yards/attempt
            - **Upper-right (Yellow)**: High risk, high reward - takes sacks but generates yards
            - **Lower-left (Yellow)**: Conservative - protects ball but limited explosiveness
            - **Lower-right (Red)**: High risk, low reward - worst of both worlds
            
            **Note:** X-axis is inverted so better performance (lower sack rate) appears on the right
            """)
        
        # Create Sack Rate vs Y/A scatter plot
        fig2 = go.Figure()
        
        median_sack = df['sack_rate'].median()
        median_ya = df['yards_per_attempt'].median()
        
        fig2.add_hline(y=median_ya, line_dash="dash", line_color="gray", opacity=0.5)
        fig2.add_vline(x=median_sack, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig2.add_trace(go.Scatter(
            x=df['sack_rate'],
            y=df['yards_per_attempt'],
            mode='markers+text',
            marker=dict(size=8, color=df['team_color'], opacity=0.8, line=dict(color='white', width=1)),
            text=df['passer_player_name'],
            textposition='top center',
            textfont=dict(size=11, color=df['team_color']),
            hovertemplate='<b>%{text}</b><br>Sack Rate: %{x:.2f}%<br>Yards/Attempt: %{y:.2f}<extra></extra>',
            showlegend=False
        ))
        
        # Add quadrant labels (note: x-axis is inverted, so positions are reversed)
        x_range = df['sack_rate'].max() - df['sack_rate'].min()
        y_range = df['yards_per_attempt'].max() - df['yards_per_attempt'].min()
        
        # Upper-left (Elite - low sacks, high Y/A) - appears on right due to inversion
        fig2.add_annotation(
            x=df['sack_rate'].min() + x_range*0.02,
            y=df['yards_per_attempt'].max() - y_range*0.02,
            text="Elite<br>(Low Sacks, High Y/A)",
            showarrow=False,
            bgcolor="rgba(0, 255, 0, 0.2)",
            bordercolor="green",
            borderwidth=2,
            font=dict(size=10, color="darkgreen"),
            align="left",
            xanchor="left",
            yanchor="top"
        )
        
        # Upper-right (High Risk High Reward) - appears on left due to inversion
        fig2.add_annotation(
            x=df['sack_rate'].max() - x_range*0.02,
            y=df['yards_per_attempt'].max() - y_range*0.02,
            text="High Risk<br>High Reward",
            showarrow=False,
            bgcolor="rgba(255, 255, 0, 0.2)",
            bordercolor="orange",
            borderwidth=2,
            font=dict(size=10, color="darkorange"),
            align="right",
            xanchor="right",
            yanchor="top"
        )
        
        # Lower-left (Conservative) - appears on right due to inversion
        fig2.add_annotation(
            x=df['sack_rate'].min() + x_range*0.02,
            y=df['yards_per_attempt'].min() + y_range*0.02,
            text="Conservative<br>(Low Sacks, Low Y/A)",
            showarrow=False,
            bgcolor="rgba(255, 255, 0, 0.2)",
            bordercolor="orange",
            borderwidth=2,
            font=dict(size=10, color="darkorange"),
            align="left",
            xanchor="left",
            yanchor="bottom"
        )
        
        # Lower-right (High Risk Low Reward) - appears on left due to inversion
        fig2.add_annotation(
            x=df['sack_rate'].max() - x_range*0.02,
            y=df['yards_per_attempt'].min() + y_range*0.02,
            text="High Risk<br>Low Reward",
            showarrow=False,
            bgcolor="rgba(255, 0, 0, 0.2)",
            bordercolor="red",
            borderwidth=2,
            font=dict(size=10, color="darkred"),
            align="right",
            xanchor="right",
            yanchor="bottom"
        )
        
        fig2.update_layout(
            title="QB Pocket Management vs Offensive Output",
            xaxis_title="Sack Rate (%)",
            yaxis_title="Yards per Attempt",
            xaxis=dict(autorange='reversed'),  # Invert x-axis
            height=700,
            hovermode='closest'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown(f"""
        **Key Statistics:**
        - Median Sack Rate: **{median_sack:.2f}%**
        - Median Yards/Attempt: **{median_ya:.2f}**
        - Sack Rate Formula: Sacks / (Pass Attempts + Sacks)
        """)
        
        # Visualization 3: Situational Performance Heatmap
        st.subheader("3️⃣ Situational Performance: Top 20 QBs")
        
        with st.expander("ℹ️ What This Chart Shows", expanded=False):
            st.markdown("""
            **What You're Seeing:**
            Three heatmaps showing how the top 20 QBs perform across different game contexts
            
            **Heatmaps Explained:**
            1. **By Down**: EPA on 1st, 2nd, 3rd, and 4th downs
            2. **By Field Position**: EPA in different field zones (Red Zone, Scoring Range, Midfield, Own Territory)
            3. **By Score Differential**: EPA when trailing, tied/close, or leading
            
            **Why It's Valuable:**
            - **Green cells** = Positive EPA (effective in that situation)
            - **Red cells** = Negative EPA (struggles in that situation)
            - Elite QBs show green across all situations (consistent performance)
            - Reveals situational specialists vs all-around performers
            - Includes both passing and rushing EPA for complete evaluation
            
            **Example Insights:**
            - Some QBs excel on early downs but struggle on 3rd down
            - Red zone specialists vs open field playmakers
            - Comeback artists (high EPA when trailing) vs lead protectors
            """)
        
        # Load situational data
        try:
            situational_df = pd.read_csv('situational_epa_top20.csv')
            
            # Apply season filter if not "All Years"
            if selected_year != "All Years":
                if isinstance(selected_year, list):
                    # Filter for multiple years
                    years = [int(y) if isinstance(y, str) else y for y in selected_year]
                    situational_df = situational_df[situational_df['season'].isin(years)]
                else:
                    # Single year
                    situational_df = situational_df[situational_df['season'] == int(selected_year)]
            
            # Get top 20 QBs based on CURRENT filtered rankings (matches year filter)
            # This ensures we show top 20 QBs for the selected year, not overall
            top_20_names = df.head(20)['passer_player_name'].tolist()
            
            # Filter situational data to only include top 20 QBs
            # Only keep QBs that actually appear in the filtered situational data
            available_qbs = situational_df['qb_name'].unique()
            top_20_in_data = [qb for qb in top_20_names if qb in available_qbs]
            
            situational_df = situational_df[situational_df['qb_name'].isin(top_20_in_data)]
            
            # Define column orders for proper left-to-right display
            field_zone_order = ['Red Zone', 'Scoring Range', 'Midfield', 'Own Territory']
            score_situation_order = ['Down 2+ Scores', 'Down 4-8', 'Close', 'Up 4-8', 'Up 2+ Scores']
            
            # Create three heatmaps side by side
            situations = ['down', 'field_zone', 'score_situation']
            situation_labels = ['Down', 'Field Position', 'Score Differential']
            
            # Create subplots using plotly
            fig3 = make_subplots(
                rows=1, cols=3,
                subplot_titles=situation_labels,
                horizontal_spacing=0.12
            )
            
            for idx, (situation, label) in enumerate(zip(situations, situation_labels)):
                # Pivot data for heatmap
                heatmap_data = situational_df.pivot_table(
                    index='qb_name',
                    columns=situation,
                    values='epa',
                    aggfunc='mean'
                )
                
                # Reorder columns based on situation type
                if situation == 'field_zone':
                    heatmap_data = heatmap_data.reindex(columns=field_zone_order, fill_value=0)
                elif situation == 'score_situation':
                    heatmap_data = heatmap_data.reindex(columns=score_situation_order, fill_value=0)
                
                # Ensure all available top 20 QBs are in the heatmap (add missing ones with zeros)
                heatmap_data = heatmap_data.reindex(index=top_20_in_data, fill_value=0)
                
                # Reverse order so best QBs at top
                heatmap_data = heatmap_data.iloc[::-1]
                
                # Create heatmap
                heatmap = go.Heatmap(
                    z=heatmap_data.values,
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    colorscale='RdYlGn',
                    zmid=0,
                    zmin=-0.3,
                    zmax=0.3,
                    text=heatmap_data.values.round(2),
                    texttemplate='%{text}',
                    textfont={"size": 10},
                    colorbar=dict(title="EPA") if idx == 2 else dict(showticklabels=False),
                    showscale=(idx == 2)
                )
                
                fig3.add_trace(heatmap, row=1, col=idx+1)
            
            fig3.update_layout(
                title_text=f"Situational QB Performance: Total EPA Across Game Contexts<br>(Top 20 QBs by Overall Rating)",
                height=600,
                showlegend=False
            )
            
            # Update axes
            for i in range(1, 4):
                fig3.update_xaxes(title_text=situation_labels[i-1], row=1, col=i, tickangle=-45)
                if i == 1:
                    fig3.update_yaxes(title_text="Quarterback", row=1, col=i)
            
            st.plotly_chart(fig3, use_container_width=True)
            
            st.markdown("""
            **Situational Performance Insights:**
            - **Green (>0 EPA)**: Effective in that context
            - **Red (<0 EPA)**: Ineffective in that context
            - Elite QBs show consistently green across all situations
            - Specialists may excel in certain situations but struggle in others
            
            **Field Position Zones:**
            - **Red Zone**: 0-20 yards from end zone
            - **Scoring Range**: 20-50 yards from end zone
            - **Midfield**: 50-75 yards from end zone
            - **Own Territory**: 75-100 yards from end zone
            """)
            
        except FileNotFoundError:
            st.warning("""
            ⚠️ Situational data not found. Please run the notebook cell to export situational EPA data:
            
            1. Open `nfl_qb_analysis.ipynb`
            2. Run the cell after "VISUALIZATION 2" that exports `situational_epa_top20.csv`
            3. Refresh this dashboard
            """)
    
    # TAB 3: Career Progression
    with tab3:
        st.header("🏈 Career Progression Tracker")
        st.markdown("Analyze how QB performance and playstyle evolved over their careers")
        
        # Load full per-season data for career tracking
        try:
            career_df = pd.read_csv('qb_rankings_by_season.csv')
            
            # Get list of all QBs with at least 3 seasons
            qb_seasons = career_df.groupby('passer_player_name')['season'].count()
            eligible_qbs = qb_seasons[qb_seasons >= 3].sort_index().index.tolist()
            
            # Player selection
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Player 1")
                player1 = st.selectbox(
                    "Select QB",
                    options=eligible_qbs,
                    key="player1",
                    help="Must have at least 3 seasons"
                )
            
            with col2:
                st.subheader("Player 2 (Optional)")
                compare_enabled = st.checkbox("Compare with another QB")
                if compare_enabled:
                    player2 = st.selectbox(
                        "Select QB",
                        options=[qb for qb in eligible_qbs if qb != player1],
                        key="player2"
                    )
                else:
                    player2 = None
            
            # Get data for selected player(s)
            p1_data = career_df[career_df['passer_player_name'] == player1].sort_values('season')
            
            if player2:
                p2_data = career_df[career_df['passer_player_name'] == player2].sort_values('season')
            
            # Calculate playstyle dimensions for each season (normalized to 0-100)
            def calculate_playstyle_scores(df_subset, df_full):
                """Calculate normalized playstyle scores (0-100 scale) using PER-SEASON normalization"""
                scores = df_subset.copy()
                
                # Filter normalization pool to remove low-volume outliers
                # Use 300 pass attempts for qualified passers (or 120 for current year 2025)
                # Dynamic threshold: lower for incomplete seasons
                def get_min_attempts(season):
                    return 120 if season == 2025 else 300
                
                # Apply threshold per season in the pool
                qualified_pool = df_full[
                    df_full.apply(lambda row: row['pass_attempts'] >= get_min_attempts(row['season']), axis=1)
                ].copy()
                
                # Calculate raw metrics first
                scores['mobility_raw'] = scores['rushing_yards'] / scores['total_games']
                scores['aggression_raw'] = scores['yards_per_attempt']
                scores['accuracy_raw'] = scores['cpoe_mean']
                scores['turnover_rate'] = ((scores['interceptions'] + scores['fumbles_lost']) / scores['total_plays']) * 100
                
                # ALL DIMENSIONS NOW USE PER-SEASON NORMALIZATION (matching First Page when filtered)
                # This compares QBs to their contemporaries in each season
                
                # Mobility - PER-SEASON normalization with 20+ rush attempts
                mobility_scores = []
                for idx, row in scores.iterrows():
                    season_pool = qualified_pool[
                        (qualified_pool['season'] == row['season']) & 
                        (qualified_pool['rush_attempts'] >= 20)
                    ].copy()
                    if len(season_pool) > 1:
                        season_pool['rush_ypg'] = season_pool['rushing_yards'] / season_pool['total_games']
                        min_mob = season_pool['rush_ypg'].min()
                        max_mob = season_pool['rush_ypg'].max()
                        if max_mob > min_mob:
                            mob_score = 100 * (row['mobility_raw'] - min_mob) / (max_mob - min_mob)
                            mobility_scores.append(max(0, min(100, mob_score)))
                        else:
                            mobility_scores.append(50)
                    else:
                        mobility_scores.append(50)
                scores['mobility_score'] = mobility_scores
                
                # Aggression - PER-SEASON normalization
                aggression_scores = []
                for idx, row in scores.iterrows():
                    season_pool = qualified_pool[qualified_pool['season'] == row['season']].copy()
                    if len(season_pool) > 1:
                        min_agg = season_pool['yards_per_attempt'].min()
                        max_agg = season_pool['yards_per_attempt'].max()
                        if max_agg > min_agg:
                            agg_score = 100 * (row['aggression_raw'] - min_agg) / (max_agg - min_agg)
                            aggression_scores.append(max(0, min(100, agg_score)))
                        else:
                            aggression_scores.append(50)
                    else:
                        aggression_scores.append(50)
                scores['aggression_score'] = aggression_scores
                
                # Accuracy - PER-SEASON normalization
                accuracy_scores = []
                for idx, row in scores.iterrows():
                    season_pool = qualified_pool[qualified_pool['season'] == row['season']].copy()
                    if len(season_pool) > 1:
                        min_acc = season_pool['cpoe_mean'].min()
                        max_acc = season_pool['cpoe_mean'].max()
                        if max_acc > min_acc:
                            acc_score = 100 * (row['accuracy_raw'] - min_acc) / (max_acc - min_acc)
                            accuracy_scores.append(max(0, min(100, acc_score)))
                        else:
                            accuracy_scores.append(50)
                    else:
                        accuracy_scores.append(50)
                scores['accuracy_score'] = accuracy_scores
                
                # Ball Security - PER-SEASON normalization (inverted turnover rate)
                ball_security_scores = []
                for idx, row in scores.iterrows():
                    season_pool = qualified_pool[qualified_pool['season'] == row['season']].copy()
                    if len(season_pool) > 1:
                        season_pool['to_rate'] = ((season_pool['interceptions'] + season_pool['fumbles_lost']) / season_pool['total_plays']) * 100
                        min_to = season_pool['to_rate'].min()
                        max_to = season_pool['to_rate'].max()
                        if max_to > min_to:
                            sec_score = 100 - (100 * (row['turnover_rate'] - min_to) / (max_to - min_to))
                            ball_security_scores.append(max(0, min(100, sec_score)))
                        else:
                            ball_security_scores.append(50)
                    else:
                        ball_security_scores.append(50)
                scores['ball_security_score'] = ball_security_scores
                
                # Pocket Presence - PER-SEASON normalization (inverted sack rate)
                pocket_scores = []
                for idx, row in scores.iterrows():
                    season_pool = qualified_pool[qualified_pool['season'] == row['season']].copy()
                    if len(season_pool) > 1:
                        min_sack = season_pool['sack_rate'].min()
                        max_sack = season_pool['sack_rate'].max()
                        if max_sack > min_sack:
                            pkt_score = 100 - (100 * (row['sack_rate'] - min_sack) / (max_sack - min_sack))
                            pocket_scores.append(max(0, min(100, pkt_score)))
                        else:
                            pocket_scores.append(50)
                    else:
                        pocket_scores.append(50)
                scores['pocket_presence_score'] = pocket_scores
                
                return scores
            
            p1_scores = calculate_playstyle_scores(p1_data, career_df)
            if player2:
                p2_scores = calculate_playstyle_scores(p2_data, career_df)
            
            # Section 1: Comprehensive Year-by-Year Statistics Table (MOVED TO TOP)
            st.subheader("📊 Comprehensive Year-by-Year Statistics")
            
            # Calculate ranking and archetype for each season
            def calculate_season_rankings(career_df_full):
                """Calculate rank and archetype for each QB season"""
                rankings_list = []
                
                for season in career_df_full['season'].unique():
                    season_data = career_df_full[career_df_full['season'] == season].copy()
                    
                    # Calculate composite score for ranking (using same weights as main model)
                    feature_columns = ['total_epa_per_play', 'cpoe_mean', 'yards_per_attempt', 
                                      'td_turnover_ratio', 'completion_pct']
                    
                    X_norm = season_data[feature_columns].copy()
                    for col in feature_columns:
                        min_val = season_data[col].min()
                        max_val = season_data[col].max()
                        if max_val > min_val:
                            X_norm[col] = 100 * (season_data[col] - min_val) / (max_val - min_val)
                        else:
                            X_norm[col] = 50
                    
                    # Invert sack_rate
                    min_val = season_data['sack_rate'].min()
                    max_val = season_data['sack_rate'].max()
                    if max_val > min_val:
                        X_norm['sack_rate_inv'] = 100 - (100 * (season_data['sack_rate'] - min_val) / (max_val - min_val))
                    else:
                        X_norm['sack_rate_inv'] = 50
                    
                    # Calculate composite score
                    feature_weights = {
                        'total_epa_per_play': 0.25,
                        'cpoe_mean': 0.15,
                        'yards_per_attempt': 0.12,
                        'td_turnover_ratio': 0.11,
                        'completion_pct': 0.09,
                        'sack_rate_inv': 0.05
                    }
                    
                    season_data['composite_score'] = sum(
                        X_norm[col] * feature_weights[col] 
                        for col in feature_weights.keys()
                    )
                    
                    # Rank within season
                    season_data = season_data.sort_values('composite_score', ascending=False)
                    season_data['rank'] = range(1, len(season_data) + 1)
                    
                    rankings_list.append(season_data)
                
                return pd.concat(rankings_list, ignore_index=True)
            
            # Calculate rankings for all seasons
            career_df_with_ranks = calculate_season_rankings(career_df)
            
            # Filter to qualified QBs for performance metric normalization (300+ attempts)
            qualified_for_ratings = career_df_with_ranks[career_df_with_ranks['pass_attempts'] >= 300].copy()
            
            # Normalize performance metrics to 0-100 across QUALIFIED data only
            performance_metrics = ['total_epa_per_play', 'cpoe_mean', 'yards_per_attempt', 'completion_pct', 'td_turnover_ratio']
            
            for metric in performance_metrics:
                min_val = qualified_for_ratings[metric].min()
                max_val = qualified_for_ratings[metric].max()
                if max_val > min_val:
                    career_df_with_ranks[f'{metric}_rating'] = 100 * (career_df_with_ranks[metric] - min_val) / (max_val - min_val)
                    career_df_with_ranks[f'{metric}_rating'] = career_df_with_ranks[f'{metric}_rating'].clip(0, 100)
                else:
                    career_df_with_ranks[f'{metric}_rating'] = 50
            
            # Normalize sack_rate (inverted - lower is better)
            min_val = qualified_for_ratings['sack_rate'].min()
            max_val = qualified_for_ratings['sack_rate'].max()
            if max_val > min_val:
                career_df_with_ranks['sack_rate_rating'] = 100 - (100 * (career_df_with_ranks['sack_rate'] - min_val) / (max_val - min_val))
                career_df_with_ranks['sack_rate_rating'] = career_df_with_ranks['sack_rate_rating'].clip(0, 100)
            else:
                career_df_with_ranks['sack_rate_rating'] = 50
            
            # Normalize composite_score to 0-100 for overall rating
            min_score = qualified_for_ratings['composite_score'].min()
            max_score = qualified_for_ratings['composite_score'].max()
            if max_score > min_score:
                career_df_with_ranks['overall_rating'] = 100 * (career_df_with_ranks['composite_score'] - min_score) / (max_score - min_score)
                career_df_with_ranks['overall_rating'] = career_df_with_ranks['overall_rating'].clip(0, 100)
            else:
                career_df_with_ranks['overall_rating'] = 50
            
            # Get ranked data for selected players
            p1_data_ranked = career_df_with_ranks[career_df_with_ranks['passer_player_name'] == player1].sort_values('season')
            if player2:
                p2_data_ranked = career_df_with_ranks[career_df_with_ranks['passer_player_name'] == player2].sort_values('season')
            
            # Recalculate scores with ranked data (pass career_df_with_ranks for normalization)
            p1_scores = calculate_playstyle_scores(p1_data_ranked, career_df_with_ranks)
            if player2:
                p2_scores = calculate_playstyle_scores(p2_data_ranked, career_df_with_ranks)
            
            # Prepare comprehensive display data - NEW ORDER with rank, team, archetype
            def prepare_detailed_table(qb_data, qb_scores):
                """Combine base stats with calculated playstyle scores - NEW order"""
                detailed = qb_data.copy()
                
                # Add playstyle scores
                detailed['mobility_score'] = qb_scores['mobility_score']
                detailed['aggression_score'] = qb_scores['aggression_score']
                detailed['accuracy_score'] = qb_scores['accuracy_score']
                detailed['ball_security_score'] = qb_scores['ball_security_score']
                detailed['pocket_presence_score'] = qb_scores['pocket_presence_score']
                
                # Add team placeholder (you can enhance this with actual team data if available)
                detailed['team'] = 'N/A'  # Placeholder - would need team data by season
                
                # Simple archetype based on dominant playstyle
                def assign_archetype(row):
                    scores = {
                        'Mobility': row['mobility_score'],
                        'Aggression': row['aggression_score'],
                        'Accuracy': row['accuracy_score'],
                        'Ball Security': row['ball_security_score'],
                        'Pocket Presence': row['pocket_presence_score']
                    }
                    max_dim = max(scores, key=scores.get)
                    return f"{max_dim} Specialist"
                
                detailed['archetype'] = detailed.apply(assign_archetype, axis=1)
                
                # Overall rating already calculated above (normalized composite_score)
                # Now select rating columns instead of raw stats
                
                # Select and order columns - ratings instead of raw stats
                display_cols = [
                    'rank', 'season', 'team', 'archetype', 'overall_rating',
                    # Playstyle Dimensions (0-100 scale)
                    'mobility_score', 'aggression_score', 'accuracy_score',
                    'ball_security_score', 'pocket_presence_score',
                    # Performance Metrics (0-100 ratings)
                    'total_epa_per_play_rating', 'cpoe_mean_rating', 'yards_per_attempt_rating',
                    'completion_pct_rating', 'sack_rate_rating'
                ]
                
                return detailed[display_cols]
            
            p1_detailed = prepare_detailed_table(p1_data_ranked, p1_scores)
            
            if player2:
                p2_detailed = prepare_detailed_table(p2_data_ranked, p2_scores)
                
                # Side-by-side comparison
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"### {player1}")
                    styled_p1 = p1_detailed.style.format({
                        'rank': '{:.0f}',
                        'overall_rating': '{:.1f}',
                        'mobility_score': '{:.1f}',
                        'aggression_score': '{:.1f}',
                        'accuracy_score': '{:.1f}',
                        'ball_security_score': '{:.1f}',
                        'pocket_presence_score': '{:.1f}',
                        'total_epa_per_play_rating': '{:.1f}',
                        'cpoe_mean_rating': '{:.1f}',
                        'yards_per_attempt_rating': '{:.1f}',
                        'completion_pct_rating': '{:.1f}',
                        'sack_rate_rating': '{:.1f}'
                    }).background_gradient(
                        subset=['overall_rating', 'mobility_score', 'aggression_score', 'accuracy_score',
                               'ball_security_score', 'pocket_presence_score',
                               'total_epa_per_play_rating', 'cpoe_mean_rating', 'yards_per_attempt_rating',
                               'completion_pct_rating', 'sack_rate_rating'],
                        cmap='RdYlGn'
                    )
                    
                    st.dataframe(styled_p1, hide_index=True, use_container_width=True, height=400)
                    
                    # Download button for player 1
                    csv1 = p1_detailed.to_csv(index=False)
                    st.download_button(
                        label=f"📥 Download {player1} Data",
                        data=csv1,
                        file_name=f'{player1.replace(".", "_")}_career_stats.csv',
                        mime='text/csv',
                        key="download_p1"
                    )
                
                with col2:
                    st.markdown(f"### {player2}")
                    styled_p2 = p2_detailed.style.format({
                        'rank': '{:.0f}',
                        'overall_rating': '{:.1f}',
                        'mobility_score': '{:.1f}',
                        'aggression_score': '{:.1f}',
                        'accuracy_score': '{:.1f}',
                        'ball_security_score': '{:.1f}',
                        'pocket_presence_score': '{:.1f}',
                        'total_epa_per_play_rating': '{:.1f}',
                        'cpoe_mean_rating': '{:.1f}',
                        'yards_per_attempt_rating': '{:.1f}',
                        'completion_pct_rating': '{:.1f}',
                        'sack_rate_rating': '{:.1f}'
                    }).background_gradient(
                        subset=['overall_rating', 'mobility_score', 'aggression_score', 'accuracy_score',
                               'ball_security_score', 'pocket_presence_score',
                               'total_epa_per_play_rating', 'cpoe_mean_rating', 'yards_per_attempt_rating',
                               'completion_pct_rating', 'sack_rate_rating'],
                        cmap='RdYlGn'
                    )
                    
                    st.dataframe(styled_p2, hide_index=True, use_container_width=True, height=400)
                    
                    # Download button for player 2
                    csv2 = p2_detailed.to_csv(index=False)
                    st.download_button(
                        label=f"📥 Download {player2} Data",
                        data=csv2,
                        file_name=f'{player2.replace(".", "_")}_career_stats.csv',
                        mime='text/csv',
                        key="download_p2"
                    )
            else:
                # Single player - full width
                st.markdown(f"### {player1} - Complete Career Statistics")
                
                styled_p1 = p1_detailed.style.format({
                    'rank': '{:.0f}',
                    'overall_rating': '{:.1f}',
                    'mobility_score': '{:.1f}',
                    'aggression_score': '{:.1f}',
                    'accuracy_score': '{:.1f}',
                    'ball_security_score': '{:.1f}',
                    'pocket_presence_score': '{:.1f}',
                    'total_epa_per_play_rating': '{:.1f}',
                    'cpoe_mean_rating': '{:.1f}',
                    'yards_per_attempt_rating': '{:.1f}',
                    'completion_pct_rating': '{:.1f}',
                    'sack_rate_rating': '{:.1f}'
                }).background_gradient(
                    subset=['overall_rating', 'mobility_score', 'aggression_score', 'accuracy_score',
                           'ball_security_score', 'pocket_presence_score',
                           'total_epa_per_play_rating', 'cpoe_mean_rating', 'yards_per_attempt_rating',
                           'completion_pct_rating', 'sack_rate_rating'],
                    cmap='RdYlGn'
                )
                
                st.dataframe(styled_p1, hide_index=True, use_container_width=True, height=600)
                
                # Download button
                csv1 = p1_detailed.to_csv(index=False)
                st.download_button(
                    label=f"📥 Download {player1} Career Data",
                    data=csv1,
                    file_name=f'{player1.replace(".", "_")}_career_stats.csv',
                    mime='text/csv',
                )
            
            # Add column descriptions
            with st.expander("📖 Column Descriptions"):
                st.markdown("""
                **All metrics shown as 0-100 ratings for easy interpretation:**
                
                - `Overall Rating`: Weighted composite of all performance metrics (normalized across qualified QBs 2010-2025)
                  - 100 = Best QB-season since 2010, 0 = Worst QB-season since 2010
                
                **Playstyle Dimensions (0-100 scale, PER-SEASON normalization):**
                - `Mobility`: Rush yards per game (normalized **per-season** among QBs with 20+ rush attempts)
                - `Aggression`: Deep ball tendency / yards per attempt (normalized **per-season**)
                - `Accuracy`: CPOE (Completion % Over Expected) (normalized **per-season**)
                - `Ball Security`: Inverted turnover rate (normalized **per-season** - higher = fewer turnovers)
                - `Pocket Presence`: Inverted sack rate (normalized **per-season** - higher = fewer sacks)
                
                **Performance Metric Ratings (0-100 scale, normalized across qualified QBs with 300+ attempts):**
                - `EPA/Play Rating`: Expected Points Added per play performance
                - `CPOE Rating`: Completion % Over Expected accuracy rating
                - `Y/A Rating`: Yards per attempt efficiency rating
                - `Comp % Rating`: Completion percentage rating
                - `Sack Rate Rating`: Sack avoidance rating (inverted - higher is better)
                
                **Normalization:** **ALL playstyle dimensions now use per-season normalization**, comparing QBs to their contemporaries in each season. This matches the First Page when filtered to a single year. Performance metric ratings use all-time normalization (2010-2025).
                
                *Playstyle scores show "best in that season" rankings - a 100.0 means the QB was the best in that dimension for their season.*
                """)
            
            st.markdown("---")
            
            # Section 2: Performance Metrics Over Time (MOVED DOWN)
            st.subheader("📈 Performance Metrics Over Time")
            
            metric_choice = st.selectbox(
                "Select Metric",
                options=[
                    "Total EPA per Play",
                    "CPOE (Accuracy)",
                    "Yards per Attempt",
                    "Completion %",
                    "Sack Rate",
                    "TD/Turnover Ratio",
                    "Success Rate"
                ],
                key="metric_choice"
            )
            
            # Map display names to column names
            metric_map = {
                "Total EPA per Play": "total_epa_per_play",
                "CPOE (Accuracy)": "cpoe_mean",
                "Yards per Attempt": "yards_per_attempt",
                "Completion %": "completion_pct",
                "Sack Rate": "sack_rate",
                "TD/Turnover Ratio": "td_turnover_ratio",
                "Success Rate": "success_rate"
            }
            
            metric_col = metric_map[metric_choice]
            
            # Create line chart
            fig_metric = go.Figure()
            
            fig_metric.add_trace(go.Scatter(
                x=p1_scores['season'],
                y=p1_scores[metric_col],
                mode='lines+markers',
                name=player1,
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=10)
            ))
            
            if player2:
                fig_metric.add_trace(go.Scatter(
                    x=p2_scores['season'],
                    y=p2_scores[metric_col],
                    mode='lines+markers',
                    name=player2,
                    line=dict(color='#ff7f0e', width=3),
                    marker=dict(size=10)
                ))
            
            fig_metric.update_layout(
                title=f"{metric_choice} by Season",
                xaxis_title="Season",
                yaxis_title=metric_choice,
                height=400,
                hovermode='x unified',
                showlegend=True
            )
            
            st.plotly_chart(fig_metric, use_container_width=True)
            
            # Section 2: Playstyle Evolution
            st.subheader("🎯 Playstyle Evolution")
            
            playstyle_metric = st.selectbox(
                "Select Playstyle Dimension",
                options=[
                    "Mobility (Rush Yards/Game)",
                    "Aggression (Yards/Attempt)",
                    "Accuracy (CPOE)",
                    "Ball Security",
                    "Pocket Presence"
                ],
                key="playstyle_choice"
            )
            
            playstyle_map = {
                "Mobility (Rush Yards/Game)": "mobility_score",
                "Aggression (Yards/Attempt)": "aggression_score",
                "Accuracy (CPOE)": "accuracy_score",
                "Ball Security": "ball_security_score",
                "Pocket Presence": "pocket_presence_score"
            }
            
            playstyle_col = playstyle_map[playstyle_metric]
            
            # Create playstyle line chart
            fig_style = go.Figure()
            
            fig_style.add_trace(go.Scatter(
                x=p1_scores['season'],
                y=p1_scores[playstyle_col],
                mode='lines+markers',
                name=player1,
                line=dict(color='#2ca02c', width=3),
                marker=dict(size=10)
            ))
            
            if player2:
                fig_style.add_trace(go.Scatter(
                    x=p2_scores['season'],
                    y=p2_scores[playstyle_col],
                    mode='lines+markers',
                    name=player2,
                    line=dict(color='#d62728', width=3),
                    marker=dict(size=10)
                ))
            
            fig_style.update_layout(
                title=f"{playstyle_metric} by Season",
                xaxis_title="Season",
                yaxis_title=playstyle_metric,
                height=400,
                hovermode='x unified',
                showlegend=True
            )
            
            st.plotly_chart(fig_style, use_container_width=True)
            
            st.markdown("---")
            
            # Section 4: Career Summary Stats
            st.subheader("🏆 Career Summary")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"### {player1}")
                st.metric("Seasons", len(p1_data))
                st.metric("Total Pass Attempts", f"{p1_data['pass_attempts'].sum():,.0f}")
                st.metric("Avg EPA/Play", f"{p1_data['total_epa_per_play'].mean():.3f}")
                st.metric("Avg CPOE", f"{p1_data['cpoe_mean'].mean():.1f}")
                st.metric("Career Rush Yards", f"{p1_data['rushing_yards'].sum():,.0f}")
            
            if player2:
                with col2:
                    st.markdown(f"### {player2}")
                    st.metric("Seasons", len(p2_data))
                    st.metric("Total Pass Attempts", f"{p2_data['pass_attempts'].sum():,.0f}")
                    st.metric("Avg EPA/Play", f"{p2_data['total_epa_per_play'].mean():.3f}")
                    st.metric("Avg CPOE", f"{p2_data['cpoe_mean'].mean():.1f}")
                    st.metric("Career Rush Yards", f"{p2_data['rushing_yards'].sum():,.0f}")
            
        except FileNotFoundError:
            st.error("⚠️ Career progression data not available. Please ensure 'qb_rankings_by_season.csv' exists.")
        except Exception as e:
            st.error(f"Error loading career data: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **Data Source:** nflfastR play-by-play data (2010-2025 seasons)
    
    **Playstyle Dimensions (0-100 scale):**
    - **Mobility**: Rushing yards per game
    - **Aggression**: Yards per pass attempt (deep ball tendency)
    - **Accuracy**: Completion % Over Expected (CPOE)
    - **Ball Security**: Inverted turnover rate
    - **Pocket Presence**: Inverted sack rate
    """)

except FileNotFoundError:
    st.error("⚠️ Data file 'qb_rankings_2010_2025.csv' not found. Please ensure the file is in the same directory as this app.")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
