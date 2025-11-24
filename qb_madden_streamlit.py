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

tabs = st.tabs(["Top 32 QBs", "Player Career View"])

# --- Tab 1: Top 32 QBs Table ---
with tabs[0]:
    st.header("Top 32 QBs (Madden-Style Ratings)")
    season = st.selectbox("Select Season", sorted(df['season'].unique(), reverse=True))
    season_df = df[df['season'] == season].sort_values('overall_rating', ascending=False).head(32).reset_index(drop=True)

    # Conditional formatting helper
    def color_rating(val):
        if val >= 95:
            color = '#FFD700'  # Gold
        elif val >= 90:
            color = '#C0C0C0'  # Silver
        elif val >= 85:
            color = '#CD7F32'  # Bronze
        elif val >= 80:
            color = '#A9DFBF'  # Green
        elif val >= 75:
            color = '#F9E79F'  # Yellow
        else:
            color = '#F5B7B1'  # Red
        return f'background-color: {color}'

    show_cols = [
        'passer_player_name', 'overall_rating', 'mobility_rating', 'aggression_rating',
        'accuracy_rating', 'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating', 'archetype'
    ]
    styled = season_df[show_cols].style.applymap(color_rating, subset=[
        'overall_rating', 'mobility_rating', 'aggression_rating', 'accuracy_rating',
        'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating'])
    st.dataframe(styled, use_container_width=True, height=800)
    rating_explanation()

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
