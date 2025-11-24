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

tabs = st.tabs(["Top 32 QBs", "Player Career View", "Advanced Analysis"])

# --- Tab 1: Top 32 QBs Table ---
with tabs[0]:
    st.header("Top 32 QBs (Madden-Style Ratings)")
    season = st.selectbox("Select Season", sorted(df['season'].unique(), reverse=True))
    season_df = df[df['season'] == season].sort_values('overall_rating', ascending=False).head(32).reset_index(drop=True)
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
    # Columns to apply background gradient (all rating/stat columns)
    gradient_cols = [
        'Overall Rating', 'Mobility', 'Aggression', 'Accuracy',
        'Ball Security', 'Pocket Presence', 'Playmaking'
    ]
    gradient_cols = [col for col in gradient_cols if col in table.columns]
    # Format dictionary for numeric columns
    format_dict = {col: "{:.0f}" for col in gradient_cols}
    styled = table.style.format(format_dict).background_gradient(
        subset=gradient_cols, cmap='RdYlGn'  # green is high, red is low
    )
    st.dataframe(styled, use_container_width=True, height=800)
    rating_explanation()

import matplotlib.pyplot as plt
import seaborn as sns
import io

# --- Tab 2: Player Career Radar Chart ---
with tabs[1]:
    st.header("Player Career Radar Chart")
    player = st.selectbox("Select Player", sorted(df['passer_player_name'].unique()))
    player_df = df[df['passer_player_name'] == player].sort_values('season')
    if not player_df.empty:
        categories = ['Mobility', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket Presence', 'Playmaking']
        rating_cols = [
            'mobility_rating', 'aggression_rating', 'accuracy_rating',
            'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating'
        ]
        fig = go.Figure()
        for _, row in player_df.iterrows():
            values = [row[col] for col in rating_cols]
            values += [values[0]]  # close the radar
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill='toself',
                name=str(row['season']),
                opacity=0.5
            ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[50, 99])),
            showlegend=True,
            title=f"{player} Career Ratings (Madden-Style)"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(player_df[['season', 'overall_rating'] + rating_cols + ['archetype']], use_container_width=True)

    else:
        st.info("No data for this player.")

# --- Tab 3: Advanced Analysis (Situational EPA Heatmaps) ---
with tabs[2]:
    st.header("Advanced Analysis: Situational EPA Heatmaps (2025)")
    st.markdown("""
    This section visualizes situational EPA (Expected Points Added) for the top 40 QBs in the 2025 season across three game contexts:
    - **Down** (1st, 2nd, 3rd, 4th)
    - **Field Position** (Red Zone, Scoring Range, Midfield, Own Territory)
    - **Score Differential** (Down 2+ Scores, Down 4-8, Close, Up 4-8, Up 2+ Scores)
    
    Each heatmap shows EPA by QB (rows, sorted by overall rating) and the situational context (columns). Green = high EPA, red = low EPA.
    """)
    try:
        situational_df = pd.read_csv('situational_epa_top20.csv')
        ratings_2025 = df[df['season'] == 2025].sort_values('overall_rating', ascending=False)
        top_40_names = ratings_2025['passer_player_name'].head(40).tolist()
        situational_df = situational_df[(situational_df['qb_name'].isin(top_40_names)) & (situational_df['season'] == 2025)]
        field_zone_order = ['Red Zone', 'Scoring Range', 'Midfield', 'Own Territory']
        score_situation_order = ['Down 2+ Scores', 'Down 4-8', 'Close', 'Up 4-8', 'Up 2+ Scores']
        situations = ['down', 'field_zone', 'score_situation']
        situation_labels = ['Down', 'Field Position', 'Score Differential']
        fig, axes = plt.subplots(1, 3, figsize=(21, 18))
        for idx, (situation, label) in enumerate(zip(situations, situation_labels)):
            ax = axes[idx]
            heatmap_data = situational_df.pivot_table(index='qb_name', columns=situation, values='epa', aggfunc='mean', fill_value=0)
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
            # Move x-axis label and tick labels to the top
            ax.xaxis.set_label_position('top')
            ax.xaxis.tick_top()
            ax.set_xlabel(label, fontsize=18, fontweight='bold')
            ax.tick_params(axis='x', labelsize=15, rotation=40)
            # Show y-tick labels (QB names) on all charts, but remove y-axis label
            ax.set_ylabel("")
            ax.tick_params(axis='y', labelsize=13)
            # For the Down chart, format x-axis labels as integers (no decimals)
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
        st.image(buf.getvalue(), caption='Situational EPA Heatmaps (2025)', use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load or plot situational EPA data: {e}")
