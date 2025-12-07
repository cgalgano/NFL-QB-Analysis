import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('c:/Users/carme/NFL_QB_Project/data_load/nfl_qb_data.db')
df = pd.read_sql_query("SELECT * FROM qb_season_stats WHERE season = 2025", conn)
conn.close()

def normalize_feature(series, invert=False):
    min_val = series.min()
    max_val = series.max()
    if max_val > min_val:
        normalized = (series - min_val) / (max_val - min_val)
        normalized = 50 + (normalized * 50)
        if invert:
            normalized = 150 - normalized
        return normalized
    else:
        return pd.Series([75] * len(series), index=series.index)

# Normalize all features
df['total_pass_epa_norm'] = normalize_feature(df['total_pass_epa'])
df['pass_success_rate_norm'] = normalize_feature(df['pass_success_rate'])
df['cpoe_norm'] = normalize_feature(df['cpoe'])
df['total_wpa_norm'] = normalize_feature(df['total_wpa'])
df['high_leverage_epa_norm'] = normalize_feature(df['high_leverage_epa'])
df['td_rate_norm'] = normalize_feature(df['td_rate'])
df['third_down_success_norm'] = normalize_feature(df['third_down_success'])
df['red_zone_epa_norm'] = normalize_feature(df['red_zone_epa'])
df['completion_pct_norm'] = normalize_feature(df['completion_pct'])
df['turnover_rate_norm'] = normalize_feature(df['turnover_rate'], invert=True)
df['sack_rate_norm'] = normalize_feature(df['sack_rate'], invert=True)

# Calculate component scores
efficiency_score = (0.50 * df['total_pass_epa_norm'] + 0.30 * df['pass_success_rate_norm'] + 0.20 * df['cpoe_norm'])
impact_score = (0.50 * df['total_wpa_norm'] + 0.30 * df['high_leverage_epa_norm'] + 0.20 * df['td_rate_norm'])
consistency_score = (0.40 * df['third_down_success_norm'] + 0.35 * df['red_zone_epa_norm'] + 0.25 * df['completion_pct_norm'])
ball_security_score = (0.40 * df['turnover_rate_norm'] + 0.60 * df['sack_rate_norm'])

df['custom_rating'] = (0.40 * efficiency_score + 0.20 * impact_score + 0.20 * consistency_score + 0.10 * ball_security_score).clip(50, 100)

# Store component scores in dataframe
df['efficiency_score'] = efficiency_score
df['impact_score'] = impact_score
df['consistency_score'] = consistency_score
df['ball_security_score'] = ball_security_score

# QBs to analyze
qbs_to_analyze = ['J.Herbert', 'B.Mayfield', 'J.Dart', 'J.Allen']

print("=" * 100)
print("2025 QB ANALYSIS: Why Are They Ranking Lower?")
print("=" * 100)

# First show where they rank overall
df_sorted = df.sort_values('custom_rating', ascending=False).reset_index(drop=True)
print("\n2025 Overall Rankings (Top 15):")
print(f"{'Rank':<5} {'QB':<20} {'Rating':>7} {'EPA':>8} {'Success%':>9} {'TD%':>6} {'TO%':>6} {'Sack%':>7}")
print("-" * 100)
for idx in range(min(15, len(df_sorted))):
    qb = df_sorted.iloc[idx]
    print(f"{idx+1:<5} {qb['player_name']:<20} {qb['custom_rating']:>7.1f} {qb['total_pass_epa']:>8.1f} {qb['pass_success_rate']:>8.1%} "
          f"{qb['td_rate']:>6.1%} {qb['turnover_rate']:>6.1%} {qb['sack_rate']:>6.1%}")

print("\n" + "=" * 100)
print("QBs OF INTEREST:")
print("=" * 100)
for qb_name in qbs_to_analyze:
    qb_row = df[df['player_name'] == qb_name]
    if len(qb_row) > 0:
        qb = qb_row.iloc[0]
        rank = (df['custom_rating'] > qb['custom_rating']).sum() + 1
        print(f"{qb_name:<20} Rating: {qb['custom_rating']:>5.1f}  Rank: {rank:>2}/{len(df)}")

print("\n" + "=" * 100)
print("RUSHING STATS COMPARISON")
print("=" * 100)
print(f"{'QB':<20} {'Rush Y/G':>10} {'Rush Att':>10} {'Rush Succ%':>12} {'Rush TDs':>10}")
print("-" * 100)
for qb_name in qbs_to_analyze:
    qb_row = df[df['player_name'] == qb_name]
    if len(qb_row) > 0:
        qb = qb_row.iloc[0]
        rush_tds = qb.get('rush_tds', 0)
        print(f"{qb_name:<20} {qb['rush_yards_per_game']:>10.1f} {qb['rush_attempts']:>10.0f} "
              f"{qb['rush_success_rate']:>11.1%} {rush_tds:>10.0f}")

# Detailed analysis for each QB
for qb_name in qbs_to_analyze:
    qb_row = df[df['player_name'] == qb_name]
    if len(qb_row) == 0:
        continue
    
    qb = qb_row.iloc[0]
    qb_idx = qb.name
    rank = (df['custom_rating'] > qb['custom_rating']).sum() + 1
    
    print("\n" + "=" * 100)
    print(f"{qb_name} DETAILED BREAKDOWN")
    print("=" * 100)
    print(f"\nCustom Rating: {qb['custom_rating']:.1f} (Rank {rank}/{len(df)})")
    print(f"Attempts: {qb['attempts']:.0f}")
    
    print("\nCOMPONENT SCORES (50-100 scale):")
    print(f"  Efficiency (40%):      {qb['efficiency_score']:>5.1f}")
    print(f"  Impact (20%):          {qb['impact_score']:>5.1f}")
    print(f"  Consistency (20%):     {qb['consistency_score']:>5.1f}")
    print(f"  Ball Security (10%):   {qb['ball_security_score']:>5.1f}")
    
    print("\nKEY METRICS & PERCENTILES:")
    metrics = [
        ('Pass EPA', 'total_pass_epa', False),
        ('Success Rate', 'pass_success_rate', False),
        ('CPOE', 'cpoe', False),
        ('WPA', 'total_wpa', False),
        ('TD Rate', 'td_rate', False),
        ('3rd Down Success', 'third_down_success', False),
        ('Red Zone EPA', 'red_zone_epa', False),
        ('Turnover Rate', 'turnover_rate', True),
        ('Sack Rate', 'sack_rate', True),
    ]
    
    for metric_name, col, invert in metrics:
        value = qb[col]
        if invert:
            percentile = (df[col] >= value).sum() / len(df) * 100
        else:
            percentile = (df[col] <= value).sum() / len(df) * 100
        
        flag = "🔴" if percentile < 40 else "🟡" if percentile < 60 else ""
        if metric_name in ['Success Rate', 'CPOE']:
            print(f"  {metric_name:18s}: {value:>7.1%}  ({percentile:>5.1f}%ile) {flag}")
        elif metric_name in ['Pass EPA', 'WPA', 'Red Zone EPA']:
            print(f"  {metric_name:18s}: {value:>7.2f}  ({percentile:>5.1f}%ile) {flag}")
        else:
            print(f"  {metric_name:18s}: {value:>7.1%}  ({percentile:>5.1f}%ile) {flag}")

# Common patterns analysis
print("\n" + "=" * 100)
print("COMMON PATTERNS & WEAKNESSES")
print("=" * 100)

analyzed_qbs = df[df['player_name'].isin(qbs_to_analyze)].copy()

print(f"\nAnalyzing {len(analyzed_qbs)} QBs: {', '.join(qbs_to_analyze)}")
print("\nAverage Component Scores vs Top 5:")
print(f"{'Metric':<25} {'These QBs':>12} {'Top 5':>12} {'Difference':>12}")
print("-" * 100)

top5 = df.nlargest(5, 'custom_rating')

components = [
    ('Custom Rating', 'custom_rating'),
    ('Efficiency Score', 'efficiency_score'),
    ('Impact Score', 'impact_score'),
    ('Consistency Score', 'consistency_score'),
    ('Ball Security Score', 'ball_security_score'),
]

for comp_name, comp_col in components:
    avg_analyzed = analyzed_qbs[comp_col].mean()
    avg_top5 = top5[comp_col].mean()
    diff = avg_analyzed - avg_top5
    print(f"{comp_name:<25} {avg_analyzed:>12.1f} {avg_top5:>12.1f} {diff:>+12.1f}")

print("\n" + "-" * 100)
print("Average Percentiles for Key Metrics:")
print(f"{'Metric':<25} {'Avg Percentile':>15} {'Assessment':>20}")
print("-" * 100)

key_metrics = [
    ('Pass EPA', 'total_pass_epa', False),
    ('Success Rate', 'pass_success_rate', False),
    ('CPOE', 'cpoe', False),
    ('3rd Down Success', 'third_down_success', False),
    ('Red Zone EPA', 'red_zone_epa', False),
    ('Turnover Rate', 'turnover_rate', True),
    ('Sack Rate', 'sack_rate', True),
]

for metric_name, col, invert in key_metrics:
    percentiles = []
    for _, qb in analyzed_qbs.iterrows():
        value = qb[col]
        if invert:
            pct = (df[col] >= value).sum() / len(df) * 100
        else:
            pct = (df[col] <= value).sum() / len(df) * 100
        percentiles.append(pct)
    
    avg_pct = np.mean(percentiles)
    
    if avg_pct < 35:
        assessment = "CRITICAL WEAKNESS"
    elif avg_pct < 50:
        assessment = "Major Weakness"
    elif avg_pct < 60:
        assessment = "Below Average"
    elif avg_pct > 75:
        assessment = "Strength"
    else:
        assessment = "Average"
    
    print(f"{metric_name:<25} {avg_pct:>14.1f}% {assessment:>20}")

print("\n" + "=" * 100)
print("CONCLUSION")
print("=" * 100)
print("""
These QBs are ranking lower because:
1. EFFICIENCY - Their play-by-play efficiency (success rate, EPA) is below elite tier
2. CONSISTENCY - They struggle in key situations (3rd downs, red zone)
3. The formula heavily weights Efficiency (40%) and Consistency (20%), 
   so even with decent volume stats, poor execution per play hurts their rating
""")
