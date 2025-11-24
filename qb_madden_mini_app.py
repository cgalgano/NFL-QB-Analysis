import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Load ratings data
@st.cache_data
def load_data():
    df = pd.read_csv('qb_madden_ratings.csv')
    return df

df = load_data()

st.set_page_config(page_title="NFL QB Madden-Style Ratings", layout="wide")

st.title("NFL QB Madden-Style Ratings (Mini App)")

# Tabs
tab1, tab2 = st.tabs(["Top 32 QBs", "Player Career View"])

with tab1:
    st.header("Top 32 QBs - Madden-Style Ratings")
    season = st.selectbox("Select Season", sorted(df['season'].unique(), reverse=True))
    season_data = df[df['season'] == season].copy()
    season_data = season_data.sort_values('overall_rating', ascending=False).head(32)

    # Display table with conditional formatting
    show_cols = [
        'passer_player_name', 'overall_rating', 'mobility_rating', 'aggression_rating', 'accuracy_rating',
        'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating', 'archetype'
    ]
    styled = season_data[show_cols].style \
        .background_gradient(subset=['overall_rating'], cmap='YlOrRd') \
        .background_gradient(subset=['mobility_rating', 'aggression_rating', 'accuracy_rating',
                                    'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating'], cmap='Blues') \
        .format({col: '{:.0f}' for col in show_cols if 'rating' in col or col == 'overall_rating'})
    st.dataframe(styled, use_container_width=True, hide_index=True)

    with st.expander("ℹ️ What do these ratings mean?"):
        st.markdown("""
        **Madden-Style Ratings Explained:**
        - **Overall (OVR):** Composite score reflecting total QB value, scaled to Madden's 50-99 range.
        - **Mobility:** Rushing yards per game, percentile-ranked and mapped to Madden scale.
        - **Aggression:** Yards per attempt (deep ball tendency), percentile-ranked.
        - **Accuracy:** Completion % Over Expected (CPOE), percentile-ranked.
        - **Ball Security:** Inverse of turnover rate (INT+Fumbles per play), percentile-ranked (lower is better).
        - **Pocket Presence:** Inverse of sack rate, percentile-ranked (lower is better).
        - **Playmaking:** EPA per play (value creation), percentile-ranked.
        
        **How are ratings calculated?**
        1. Each stat is converted to a percentile rank among all QBs.
        2. Percentile is mapped to Madden's 50-99 scale using a custom formula (see notebook for details).
        3. Overall is a weighted blend of key stats, then mapped to 50-99.
        """)

with tab2:
    st.header("Player Career Ratings (Radar Chart)")
    player_names = sorted(df['passer_player_name'].unique())
    player = st.selectbox("Select QB", player_names)
    player_data = df[df['passer_player_name'] == player].sort_values('season')

    if len(player_data) == 0:
        st.warning("No data for this player.")
    else:
        # Radar chart for each season
        rating_cols = [
            'mobility_rating', 'aggression_rating', 'accuracy_rating',
            'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating'
        ]
        categories = ['Mobility', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket Presence', 'Playmaking']

        # Show a season selector
        seasons = player_data['season'].tolist()
        season_selected = st.selectbox("Select Season", seasons, index=len(seasons)-1)
        row = player_data[player_data['season'] == season_selected].iloc[0]
        values = [row[col] for col in rating_cols]
        values += [values[0]]  # close the radar
        categories_closed = categories + [categories[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories_closed,
            fill='toself',
            name=f"{player} ({season_selected})",
            line_color='#1f77b4',
            fillcolor='#1f77b4',
            opacity=0.7
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[50, 99],
                    tickvals=[60, 70, 80, 90],
                    tickfont=dict(size=10)
                )
            ),
            showlegend=False,
            title=f"{player} Madden-Style Ratings ({season_selected})"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Show table of all seasons for this player
        st.markdown("#### Ratings by Season")
        st.dataframe(player_data[['season', 'overall_rating'] + rating_cols + ['archetype']], hide_index=True)
