import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Load ratings data
@st.cache_data
def load_data():
    df = pd.read_csv('qb_madden_ratings.csv')
    return df

df = load_data()

# Always add team colors for all tabs (prevents KeyError)
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
if 'team' in df.columns:
    df['team_color'] = df['team'].map(nfl_colors).fillna('#808080')
else:
    df['team_color'] = '#808080'

st.set_page_config(page_title="NFL QB Madden-Style Ratings", layout="wide")

st.title("NFL QB Madden-Style Ratings (Mini App)")

tab1, tab2, tab3 = st.tabs(["Madden-Style Rankings", "Player Career Radar", "Advanced Analysis"])

with tab1:
    st.subheader("Madden-Style QB Rankings Table")
    # Season selector
    seasons = sorted(df['season'].unique())
    selected_season = st.selectbox("Select Season", seasons, index=len(seasons)-1)
    season_data = df[df['season'] == selected_season].copy()
    season_data = season_data.sort_values('overall_rating', ascending=False)
    # Columns to show
    table_cols = [
        'passer_player_name', 'overall_rating', 'mobility_rating', 'aggression_rating',
        'accuracy_rating', 'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating', 'archetype'
    ]
    display_df = season_data[table_cols].reset_index(drop=True)
    display_df.index = display_df.index + 1
    # Conditional formatting
    def color_rating(val):
        if isinstance(val, int) or isinstance(val, float):
            # Red = best, white = mid, blue = worst
            if val >= 90:
                color = '#d73027'  # strong red
            elif val >= 80:
                color = '#fc8d59'  # orange-red
            elif val >= 75:
                color = '#fee090'  # light orange
            elif val >= 70:
                color = '#e0f3f8'  # very light blue
            else:
                color = '#4575b4'  # strong blue
            return f'background-color: {color}'
        return ''
    st.dataframe(
        display_df.style.applymap(color_rating, subset=[
            'overall_rating', 'mobility_rating', 'aggression_rating',
            'accuracy_rating', 'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating'])
        .format({'overall_rating': '{:.0f}', 'mobility_rating': '{:.0f}', 'aggression_rating': '{:.0f}',
                 'accuracy_rating': '{:.0f}', 'ball_security_rating': '{:.0f}', 'pocket_presence_rating': '{:.0f}', 'playmaking_rating': '{:.0f}'})
        .set_properties(**{'font-size': '15px'}),
        use_container_width=True,
        height=900
    )
    st.caption("OVR=Overall, MOB=Mobility, AGG=Aggression, ACC=Accuracy, SEC=Ball Security, POC=Pocket Presence, PLY=Playmaking")

with tab2:
    st.subheader("Player Career Progression (Radar Chart)")
    player_names = sorted(df['passer_player_name'].unique())
    selected_player = st.selectbox("Select Player", player_names)
    player_data = df[df['passer_player_name'] == selected_player].sort_values('season')
    if len(player_data) == 0:
        st.warning(f"No data for {selected_player}.")
    else:
        import plotly.graph_objects as go
        radar_cols = ['mobility_rating', 'aggression_rating', 'accuracy_rating', 'ball_security_rating', 'pocket_presence_rating', 'playmaking_rating']
        radar_labels = ['Mobility', 'Aggression', 'Accuracy', 'Ball Security', 'Pocket Presence', 'Playmaking']
        for _, row in player_data.iterrows():
            values = [row[col] for col in radar_cols]
            values += [values[0]]  # close the radar
            labels_closed = radar_labels + [radar_labels[0]]
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=labels_closed,
                fill='toself',
                name=f"{row['season']}",
                line_color='#1f77b4',
                opacity=0.7
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[50, 99])),
                showlegend=False,
                title=f"{selected_player} - {row['season']} ({row['archetype']}) - OVR: {row['overall_rating']}"
            )
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("🔍 Advanced QB Performance Analysis")
    st.markdown("""These visualizations provide deeper insights into quarterback performance using advanced metrics from play-by-play data. Each chart reveals different dimensions of QB effectiveness.""")

    # 1️⃣ Total EPA vs CPOE
    st.subheader("1️⃣ Total Value Creation vs Accuracy")
    median_epa = df['total_epa_per_play'].median()
    median_cpoe = df['cpoe_mean'].median()
    fig1 = go.Figure()
    fig1.add_hline(y=median_epa, line_dash="dash", line_color="gray", opacity=0.5)
    fig1.add_vline(x=median_cpoe, line_dash="dash", line_color="gray", opacity=0.5)
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
    fig1.update_layout(
        title="QB Performance: Total EPA vs CPOE",
        xaxis_title="CPOE (Completion % Over Expected)",
        yaxis_title="Total EPA per Play (Passing + Rushing)",
        height=600,
        hovermode='closest'
    )
    st.plotly_chart(fig1, use_container_width=True)

    # 2️⃣ Sack Rate vs Yards/Attempt
    st.subheader("2️⃣ Pocket Management vs Offensive Aggressiveness")
    median_sack = df['sack_rate'].median()
    median_ya = df['yards_per_attempt'].median()
    fig2 = go.Figure()
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
    fig2.update_layout(
        title="QB Pocket Management vs Offensive Output",
        xaxis_title="Sack Rate (%)",
        yaxis_title="Yards per Attempt",
        xaxis=dict(autorange='reversed'),
        height=600,
        hovermode='closest'
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 3️⃣ Situational Performance Heatmap (Top 40 QBs)
    st.subheader("3️⃣ Situational Performance: Top 40 QBs")
    try:
        situational_df = pd.read_csv('situational_epa_top20.csv')  # file may still be named top20, but we use top 40 QBs
        # Get top 40 QBs by overall_rating for 2025 from the Madden ratings
        if 'season' in df.columns:
            top_40_names = df[df['season'] == 2025].sort_values('overall_rating', ascending=False).head(40)['passer_player_name'].tolist()
        else:
            top_40_names = df.sort_values('overall_rating', ascending=False).head(40)['passer_player_name'].tolist()
        situational_df = situational_df[(situational_df['qb_name'].isin(top_40_names)) & (situational_df['season'] == 2025)]
        field_zone_order = ['Red Zone', 'Scoring Range', 'Midfield', 'Own Territory']
        score_situation_order = ['Down 2+ Scores', 'Down 4-8', 'Close', 'Up 4-8', 'Up 2+ Scores']
        situations = ['down', 'field_zone', 'score_situation']
        situation_labels = ['Down', 'Field Position', 'Score Differential']
        from plotly.subplots import make_subplots
        fig3 = make_subplots(rows=1, cols=3, subplot_titles=situation_labels, horizontal_spacing=0.12)
        for idx, (situation, label) in enumerate(zip(situations, situation_labels)):
            heatmap_data = situational_df.pivot_table(
                index='qb_name', columns=situation, values='epa', aggfunc='mean')
            if situation == 'field_zone':
                heatmap_data = heatmap_data.reindex(columns=field_zone_order, fill_value=0)
            elif situation == 'score_situation':
                heatmap_data = heatmap_data.reindex(columns=score_situation_order, fill_value=0)
            # Sort by overall_rating from Madden ratings (top to bottom)
            heatmap_data = heatmap_data.reindex(index=top_40_names, fill_value=0)
            # Do NOT reverse the order; top overall rating should be at the top
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
            title_text="Situational QB Performance: Total EPA Across Game Contexts<br>(Top 40 QBs by Overall Rating, 2025)",
            height=1200,
            showlegend=False
        )
        for i in range(1, 4):
            fig3.update_xaxes(title_text=situation_labels[i-1], row=1, col=i, tickangle=-45)
            if i == 1:
                fig3.update_yaxes(title_text="Quarterback", row=1, col=i)
        st.plotly_chart(fig3, use_container_width=True)
    except FileNotFoundError:
        st.warning("Situational data not found. Please export 'situational_epa_top20.csv' from your analysis notebook.")
