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
        df = pd.read_csv('qb_rankings_2021_2025.csv')
    else:
        # Load per-season data and filter
        df = pd.read_csv('qb_rankings_by_season.csv')
        df = df[df['season'] == int(season_filter)]
        
        # Calculate composite score for this season using same weights as notebook
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
        
        # Calculate composite score with notebook weights
        feature_weights = {
            'total_epa_per_play': 0.26,
            'cpoe_mean': 0.15,
            'yards_per_attempt': 0.13,
            'td_turnover_ratio': 0.11,
            'completion_pct': 0.09,
            'sack_rate_inv': 0.03
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
    
    # Calculate 5 playstyle dimensions (EXACT LOGIC FROM NOTEBOOK)
    # 1. Mobility: Rush yards per game
    top_30['mobility_score'] = top_30['rushing_yards'] / top_30['total_games']
    
    # 2. Aggression: Yards per attempt (deep ball tendency)
    top_30['aggression_score'] = top_30['yards_per_attempt']
    
    # 3. Accuracy: CPOE (Completion % over expected)
    top_30['accuracy_score'] = top_30['cpoe_mean']
    
    # 4. Ball Security: Turnover rate (INTs + fumbles lost per 100 plays)
    top_30['turnover_rate'] = ((top_30['interceptions'] + top_30['fumbles_lost']) / top_30['total_plays']) * 100
    top_30['ball_security_score'] = 100 - (top_30['turnover_rate'] * 10)
    
    # 5. Pocket Presence: Inverted sack rate
    top_30['pocket_presence_score'] = 100 - (top_30['sack_rate'] * 2)
    
    # Normalize all scores to 0-100 scale
    playstyle_dims = ['mobility_score', 'aggression_score', 'accuracy_score', 
                      'ball_security_score', 'pocket_presence_score']
    
    for dim in playstyle_dims:
        min_val = top_30[dim].min()
        max_val = top_30[dim].max()
        if max_val > min_val:
            top_30[dim] = 100 * (top_30[dim] - min_val) / (max_val - min_val)
        else:
            top_30[dim] = 50
    
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
selected_year = st.sidebar.selectbox(
    "Select Season",
    options=["All Years", "2021", "2022", "2023", "2024", "2025"],
    index=0,
    help="Filter all visualizations by season"
)

# Title
title_text = f"🏈 Top 30 NFL Quarterbacks ({selected_year if selected_year != 'All Years' else '2021-2025'})"
st.title(title_text)
st.markdown("Comprehensive playstyle analysis and rankings")

# Load the data with filter
try:
    df, top_30, qb_teams = load_data(season_filter=selected_year)
    
    # Create tabs
    tab1, tab2 = st.tabs(["📊 Top 30 Rankings", "🔍 Advanced Analysis"])
    
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
        from play-by-play data across the 2021-2025 seasons. Each chart reveals different dimensions of QB effectiveness.
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
            title="QB Performance: Total EPA vs CPOE (2021-2025)",
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
            title="QB Pocket Management vs Offensive Output (2021-2025)",
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
                situational_df = situational_df[situational_df['season'] == int(selected_year)]
            
            # Get top 20 QBs in order
            top_20_names = df.head(20)['passer_player_name'].tolist()
            
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
                
                # Reorder rows by top 20 ranking (inverted so best QBs at top)
                qb_order = [qb for qb in top_20_names if qb in heatmap_data.index]
                heatmap_data = heatmap_data.loc[qb_order[::-1]]  # Reverse order
                
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
                title_text="Situational QB Performance: Total EPA Across Game Contexts<br>(Top 20 QBs by Overall EPA/play - Passing + Rushing)",
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
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **Data Source:** nflfastR play-by-play data (2021-2025 seasons)
    
    **Playstyle Dimensions (0-100 scale):**
    - **Mobility**: Rushing yards per game
    - **Aggression**: Yards per pass attempt (deep ball tendency)
    - **Accuracy**: Completion % Over Expected (CPOE)
    - **Ball Security**: Inverted turnover rate
    - **Pocket Presence**: Inverted sack rate
    """)

except FileNotFoundError:
    st.error("⚠️ Data file 'qb_rankings_2021_2025.csv' not found. Please ensure the file is in the same directory as this app.")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
