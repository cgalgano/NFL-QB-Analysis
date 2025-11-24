import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('qb_madden_ratings.csv')
    return df

df = load_data()

# --- Helper: Explanation of Ratings ---
def rating_explanation():
    st.markdown("""
    ### What Each Rating Means
    - **Overall**: Weighted composite of EPA/play, CPOE, YPA, TD/TO ratio, completion %, and sack rate.
    - **Mobility**: Rushing yards per game (percentile-based).
    - **Aggression**: Yards per attempt (deep ball tendency).
    - **Accuracy**: Completion % Over Expected (CPOE).
    - **Ball Security**: Inverse of turnover rate (lower is better).
    - **Pocket Presence**: Inverse of sack rate (lower is better).
    - **Playmaking**: EPA per play (value creation).
    
    #### How Ratings Are Calculated
    - Each stat is converted to a percentile among all qualified QBs (min 150 attempts).
    - Percentiles are mapped to Madden-style ratings (50–99 scale).
    - Overall rating uses a weighted composite model (see notebook for details).
    """)

# --- Streamlit App ---
st.set_page_config(page_title="NFL QB Madden-Style Rankings", layout="wide")
st.title("NFL QB Madden-Style Rankings")

tabs = st.tabs(["Top 32 QBs", "Player Career View", "Advanced Analysis", "EPA vs CPOE Scatter", "Sack Rate vs Y/A Scatter"])

# --- Tab 1: Top 32 QBs Table ---
with tabs[0]:
    st.header("Top 32 QBs (Madden-Style Ratings)")
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", options=all_years, default=all_years, format_func=str, key="year_filter_tab0")
    filtered_df = df[df['season'].isin(selected_years)]
    # If only one year is selected, show that year's ratings as before
    if len(selected_years) == 1:
        season_df = filtered_df.sort_values('overall_rating', ascending=False).head(32).reset_index(drop=True)
        season_df['Rank'] = season_df.index + 1
    else:
        # Aggregate over career for each QB (average ratings, use most common archetype)
        agg_dict = {
            'overall_rating': 'mean',
            'mobility_rating': 'mean',
            'aggression_rating': 'mean',
            'accuracy_rating': 'mean',
            'ball_security_rating': 'mean',
            'pocket_presence_rating': 'mean',
            'playmaking_rating': 'mean',
            'archetype': lambda x: x.mode().iat[0] if not x.mode().empty else x.iloc[0]
        }
        season_df = filtered_df.groupby('passer_player_name', as_index=False).agg(agg_dict)
        season_df = season_df.sort_values('overall_rating', ascending=False).head(32).reset_index(drop=True)
        season_df['Rank'] = season_df.index + 1
    show_cols = [
        'Rank', 'passer_player_name', 'overall_rating', 'mobility_rating', 'aggression_rating',
        'accuracy_rating', 'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating', 'archetype'
    ]
    rename_dict = {
        'Rank': 'Rank',
        'passer_player_name': 'QB Name',
        'overall_rating': 'Overall Rating',
        'mobility_rating': 'Mobility',
        'aggression_rating': 'Aggression',
        'accuracy_rating': 'Accuracy',
        'ball_security_rating': 'Ball Security',
        'pocket_presence_rating': 'Pocket Presence',
        'playmaking_rating': 'Playmaking',
        'archetype': 'Archetype'
    }
    table = season_df[show_cols].rename(columns=rename_dict)
    gradient_cols = [
        'Overall Rating', 'Mobility', 'Aggression', 'Accuracy',
        'Ball Security', 'Pocket Presence', 'Playmaking'
    ]
    gradient_cols = [col for col in gradient_cols if col in table.columns]
    format_dict = {col: "{:.0f}" for col in gradient_cols}
    styled = table.style.format(format_dict).background_gradient(
        subset=gradient_cols, cmap='RdYlGn'  # green is high, red is low
    )
    st.dataframe(styled, use_container_width=True, height=800)
    rating_explanation()

import matplotlib.pyplot as plt
import seaborn as sns
import io

# --- Tab 2: Player Career Ratings Table ---
with tabs[1]:
    st.header("Player Career Ratings Table")
    player = st.selectbox("Select Player", sorted(df['passer_player_name'].unique()))
    player_df = df[df['passer_player_name'] == player].sort_values('season')
    if not player_df.empty:
        # Compute rank for each season (by overall_rating, descending)
        df_ranks = df[df['season'].isin(player_df['season'])].copy()
        df_ranks['Rank'] = df_ranks.groupby('season')['overall_rating'].rank(ascending=False, method='min')
        player_df = player_df.merge(df_ranks[['season', 'passer_player_name', 'Rank']], on=['season', 'passer_player_name'], how='left')
        show_cols = [
            'season', 'Rank', 'overall_rating', 'mobility_rating', 'aggression_rating',
            'accuracy_rating', 'ball_security_rating', 'pocket_presence_rating',
            'playmaking_rating', 'archetype'
        ]
        rename_dict = {
            'season': 'Season',
            'Rank': 'Rank',
            'overall_rating': 'Overall Rating',
            'mobility_rating': 'Mobility',
            'aggression_rating': 'Aggression',
            'accuracy_rating': 'Accuracy',
            'ball_security_rating': 'Ball Security',
            'pocket_presence_rating': 'Pocket Presence',
            'playmaking_rating': 'Playmaking',
            'archetype': 'Archetype'
        }
        table = player_df[show_cols].rename(columns=rename_dict)
        gradient_cols = [
            'Overall Rating', 'Mobility', 'Aggression', 'Accuracy',
            'Ball Security', 'Pocket Presence', 'Playmaking'
        ]
        format_dict = {col: "{:.0f}" for col in gradient_cols}
        format_dict['Rank'] = "{:.0f}"
        styled = table.style.format(format_dict).background_gradient(
            subset=gradient_cols, cmap='RdYlGn'
        )
        st.dataframe(styled, use_container_width=True, height=600)
        rating_explanation()
    else:
        st.info("No data for this player.")

# --- Tab 3: Advanced Analysis (Situational EPA Heatmaps) ---
with tabs[2]:
    st.header("Advanced Analysis: Situational EPA Heatmaps")
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", all_years, default=[2025] if 2025 in all_years else [all_years[0]], key="year_filter_tab2")
    try:
        situational_df = pd.read_csv('situational_epa_top20.csv')
        ratings_filtered = df[df['season'].isin(selected_years)]
        # If only one year is selected, show as before
        if len(selected_years) == 1:
            year = selected_years[0]
            st.subheader(f"Situational EPA Heatmaps ({year})")
            ratings_year = ratings_filtered[ratings_filtered['season'] == year].sort_values('overall_rating', ascending=False)
            top_40_names = ratings_year['passer_player_name'].head(40).tolist()
            situational_year = situational_df[(situational_df['qb_name'].isin(top_40_names)) & (situational_df['season'] == year)]
            field_zone_order = ['Red Zone', 'Scoring Range', 'Midfield', 'Own Territory']
            score_situation_order = ['Down 2+ Scores', 'Down 4-8', 'Close', 'Up 4-8', 'Up 2+ Scores']
            situations = ['down', 'field_zone', 'score_situation']
            situation_labels = ['Down', 'Field Position', 'Score Differential']
            fig, axes = plt.subplots(1, 3, figsize=(21, 18))
            for idx, (situation, label) in enumerate(zip(situations, situation_labels)):
                ax = axes[idx]
                heatmap_data = situational_year.pivot_table(index='qb_name', columns=situation, values='epa', aggfunc='mean', fill_value=0)
                if situation == 'field_zone':
                    heatmap_data = heatmap_data.reindex(columns=field_zone_order, fill_value=0)
                elif situation == 'score_situation':
                    heatmap_data = heatmap_data.reindex(columns=score_situation_order, fill_value=0)
                # Sort by overall_rating from Madden ratings (top to bottom)
                heatmap_data = heatmap_data.reindex(index=top_40_names, fill_value=0)
                show_cbar = (idx == 2)
                sns.heatmap(
                    heatmap_data, ax=ax, cmap='RdYlGn', center=0, vmin=-0.3, vmax=0.3, annot=True, fmt='.2f',
                    cbar=show_cbar, cbar_kws={'label': 'EPA'} if show_cbar else None, linewidths=0.5, annot_kws={"size": 12}
                )
                ax.set_title(f'EPA by {label}', fontsize=22, fontweight='bold', pad=18)
                ax.xaxis.set_label_position('top')
                ax.xaxis.tick_top()
                ax.set_xlabel(label, fontsize=18, fontweight='bold')
                ax.tick_params(axis='x', labelsize=15, rotation=40)
                ax.set_ylabel("")
                ax.tick_params(axis='y', labelsize=13)
                if situation == 'down':
                    new_labels = []
                    for lbl in ax.get_xticklabels():
                        lbl_text = lbl.get_text()
                        try:
                            new_labels.append(str(int(float(lbl_text))))
                        except (ValueError, TypeError):
                            new_labels.append(lbl_text)
                    ax.set_xticklabels(new_labels, fontsize=15, rotation=40)
            plt.tight_layout(rect=[0, 0, 1, 0.98])
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            plt.close(fig)
            st.image(buf.getvalue(), caption=f'Situational EPA Heatmaps ({year})', use_container_width=True)
        else:
            # Aggregate ratings and situational EPA over selected years for each QB
            agg_dict = {
                'overall_rating': 'mean',
                'mobility_rating': 'mean',
                'aggression_rating': 'mean',
                'accuracy_rating': 'mean',
                'ball_security_rating': 'mean',
                'pocket_presence_rating': 'mean',
                'playmaking_rating': 'mean',
                'archetype': lambda x: x.mode().iat[0] if not x.mode().empty else x.iloc[0]
            }
            ratings_agg = ratings_filtered.groupby('passer_player_name', as_index=False).agg(agg_dict)
            top_40_names = ratings_agg.sort_values('overall_rating', ascending=False)['passer_player_name'].head(40).tolist()
            situational_agg = situational_df[situational_df['season'].isin(selected_years) & situational_df['qb_name'].isin(top_40_names)]
            # Aggregate EPA by mean for each QB and situation
            situations = ['down', 'field_zone', 'score_situation']
            situation_labels = ['Down', 'Field Position', 'Score Differential']
            field_zone_order = ['Red Zone', 'Scoring Range', 'Midfield', 'Own Territory']
            score_situation_order = ['Down 2+ Scores', 'Down 4-8', 'Close', 'Up 4-8', 'Up 2+ Scores']
            st.subheader(f"Situational EPA Heatmaps (Aggregate: {', '.join(map(str, selected_years))})")
            fig, axes = plt.subplots(1, 3, figsize=(21, 18))
            for idx, (situation, label) in enumerate(zip(situations, situation_labels)):
                ax = axes[idx]
                heatmap_data = situational_agg.pivot_table(index='qb_name', columns=situation, values='epa', aggfunc='mean', fill_value=0)
                if situation == 'field_zone':
                    heatmap_data = heatmap_data.reindex(columns=field_zone_order, fill_value=0)
                elif situation == 'score_situation':
                    heatmap_data = heatmap_data.reindex(columns=score_situation_order, fill_value=0)
                # Sort by overall_rating from Madden ratings (top to bottom)
                heatmap_data = heatmap_data.reindex(index=top_40_names, fill_value=0)
                show_cbar = (idx == 2)
                sns.heatmap(
                    heatmap_data, ax=ax, cmap='RdYlGn', center=0, vmin=-0.3, vmax=0.3, annot=True, fmt='.2f',
                    cbar=show_cbar, cbar_kws={'label': 'EPA'} if show_cbar else None, linewidths=0.5, annot_kws={"size": 12}
                )
                ax.set_title(f'EPA by {label}', fontsize=22, fontweight='bold', pad=18)
                ax.xaxis.set_label_position('top')
                ax.xaxis.tick_top()
                ax.set_xlabel(label, fontsize=18, fontweight='bold')
                ax.tick_params(axis='x', labelsize=15, rotation=40)
                ax.set_ylabel("")
                ax.tick_params(axis='y', labelsize=13)
                if situation == 'down':
                    new_labels = []
                    for lbl in ax.get_xticklabels():
                        lbl_text = lbl.get_text()
                        try:
                            new_labels.append(str(int(float(lbl_text))))
                        except (ValueError, TypeError):
                            new_labels.append(lbl_text)
                    ax.set_xticklabels(new_labels, fontsize=15, rotation=40)
            plt.tight_layout(rect=[0, 0, 1, 0.98])
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            plt.close(fig)
            st.image(buf.getvalue(), caption=f'Situational EPA Heatmaps (Aggregate: {', '.join(map(str, selected_years))})', use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load or plot situational EPA data: {e}")

import plotly.express as px

# --- Tab 4: EPA vs CPOE Scatter Plot ---
with tabs[3]:
    st.header("Total EPA vs CPOE Scatter Plot")
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", all_years, default=all_years, key="year_filter_tab3")
    filtered_df = df[df['season'].isin(selected_years)]
    fig = px.scatter(
        filtered_df,
        x='cpoe_mean',
        y='total_epa_per_play',
        text='passer_player_name',
        color='overall_rating',
        color_continuous_scale='RdYlGn',
        labels={
            'cpoe_mean': 'CPOE',
            'total_epa_per_play': 'Total EPA per Play',
            'overall_rating': 'Overall Rating',
            'season': 'Season'
        },
        hover_data=['season', 'overall_rating']
    )
    fig.update_traces(textposition='top center', marker=dict(size=14, line=dict(width=1, color='DarkSlateGrey')))
    # Add quadrant lines
    median_epa = filtered_df['total_epa_per_play'].median()
    median_cpoe = filtered_df['cpoe_mean'].median()
    fig.add_shape(type="line", x0=median_cpoe, x1=median_cpoe, y0=filtered_df['total_epa_per_play'].min(), y1=filtered_df['total_epa_per_play'].max(),
                  line=dict(color="gray", dash="dash"))
    fig.add_shape(type="line", x0=filtered_df['cpoe_mean'].min(), x1=filtered_df['cpoe_mean'].max(), y0=median_epa, y1=median_epa,
                  line=dict(color="gray", dash="dash"))
    # Add quadrant labels
    fig.add_annotation(x=filtered_df['cpoe_mean'].max(), y=filtered_df['total_epa_per_play'].max(),
        text="Elite<br>(High Total EPA & CPOE)", showarrow=False, xanchor="right", yanchor="top",
        font=dict(size=13, color="green"), bgcolor="rgba(0,255,0,0.08)")
    fig.add_annotation(x=filtered_df['cpoe_mean'].min(), y=filtered_df['total_epa_per_play'].max(),
        text="High Total EPA<br>Low CPOE", showarrow=False, xanchor="left", yanchor="top",
        font=dict(size=13, color="orange"), bgcolor="rgba(255,255,0,0.08)")
    fig.add_annotation(x=filtered_df['cpoe_mean'].max(), y=filtered_df['total_epa_per_play'].min(),
        text="High CPOE<br>Low Total EPA", showarrow=False, xanchor="right", yanchor="bottom",
        font=dict(size=13, color="orange"), bgcolor="rgba(255,255,0,0.08)")
    fig.add_annotation(x=filtered_df['cpoe_mean'].min(), y=filtered_df['total_epa_per_play'].min(),
        text="Below Average", showarrow=False, xanchor="left", yanchor="bottom",
        font=dict(size=13, color="red"), bgcolor="rgba(255,0,0,0.08)")
    fig.update_layout(height=700, xaxis_title="CPOE (Completion % Over Expected)", yaxis_title="Total EPA per Play (Passing + Rushing)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("""
**Quadrant Interpretation:**

- **Upper-right:** Elite (High Total EPA & CPOE)
- **Upper-left:** High Total EPA, Low CPOE
- **Lower-right:** High CPOE, Low Total EPA
- **Lower-left:** Below Average

Total EPA/play = (Passing EPA + Rushing EPA) / Total plays
CPOE = Completion % Over Expected (passing accuracy relative to difficulty)
""")

# --- Tab 5: Sack Rate vs Yards/Attempt Scatter Plot ---
with tabs[4]:
    st.header("Sack Rate vs Yards/Attempt Scatter Plot")
    all_years = sorted(df['season'].unique(), reverse=True)
    selected_years = st.multiselect("Select Year(s)", all_years, default=all_years, key="year_filter_tab4")
    filtered_df = df[df['season'].isin(selected_years)]
    # Invert sack rate for plotting (so lower sack rate is to the right)
    filtered_df = filtered_df.copy()
    filtered_df['inv_sack_rate'] = -filtered_df['sack_rate']
    fig2 = px.scatter(
        filtered_df,
        x='inv_sack_rate',
        y='yards_per_attempt',
        text='passer_player_name',
        color='overall_rating',
        color_continuous_scale='RdYlGn',
        labels={
            'inv_sack_rate': 'Sack Rate (Inverted)',
            'yards_per_attempt': 'Yards per Attempt',
            'overall_rating': 'Overall Rating',
            'season': 'Season'
        },
        hover_data=['season', 'overall_rating']
    )
    fig2.update_traces(textposition='top center', marker=dict(size=14, line=dict(width=1, color='DarkSlateGrey')))
    # Add quadrant lines
    median_inv_sack = -filtered_df['sack_rate'].median()
    median_ya = filtered_df['yards_per_attempt'].median()
    fig2.add_shape(type="line", x0=median_inv_sack, x1=median_inv_sack, y0=filtered_df['yards_per_attempt'].min(), y1=filtered_df['yards_per_attempt'].max(),
                  line=dict(color="gray", dash="dash"))
    fig2.add_shape(type="line", x0=filtered_df['inv_sack_rate'].min(), x1=filtered_df['inv_sack_rate'].max(), y0=median_ya, y1=median_ya,
                  line=dict(color="gray", dash="dash"))
    # Add quadrant labels
    fig2.add_annotation(x=filtered_df['inv_sack_rate'].max(), y=filtered_df['yards_per_attempt'].max(),
        text="Elite\n(Low Sacks, High Y/A)", showarrow=False, xanchor="right", yanchor="top",
        font=dict(size=13, color="green"), bgcolor="rgba(0,255,0,0.08)")
    fig2.add_annotation(x=filtered_df['inv_sack_rate'].min(), y=filtered_df['yards_per_attempt'].max(),
        text="High Risk High Reward\n(High Sacks, High Y/A)", showarrow=False, xanchor="left", yanchor="top",
        font=dict(size=13, color="orange"), bgcolor="rgba(255,255,0,0.08)")
    fig2.add_annotation(x=filtered_df['inv_sack_rate'].max(), y=filtered_df['yards_per_attempt'].min(),
        text="Conservative\n(Low Sacks, Low Y/A)", showarrow=False, xanchor="right", yanchor="bottom",
        font=dict(size=13, color="orange"), bgcolor="rgba(255,255,0,0.08)")
    fig2.add_annotation(x=filtered_df['inv_sack_rate'].min(), y=filtered_df['yards_per_attempt'].min(),
        text="High Risk Low Reward\n(High Sacks, Low Y/A)", showarrow=False, xanchor="left", yanchor="bottom",
        font=dict(size=13, color="red"), bgcolor="rgba(255,0,0,0.08)")
    fig2.update_layout(height=700, xaxis_title="Sack Rate (Inverted: Lower = Right)", yaxis_title="Yards per Attempt")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("""
**Quadrant Interpretation:**

- **Upper-left:** High Risk High Reward (High Sacks, High Y/A)
- **Upper-right:** Elite (Low Sacks, High Y/A)
- **Lower-left:** High Risk Low Reward (High Sacks, Low Y/A)
- **Lower-right:** Conservative (Low Sacks, Low Y/A)

Sack Rate = Sacks / (Pass Attempts + Sacks)
Y/A = Yards per Attempt (downfield aggressiveness and completion efficiency)
""")
