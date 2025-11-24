import pandas as pd

df = pd.read_csv('qb_rankings_by_season.csv')

# Filter 2025 with dynamic threshold
s25 = df[(df['season'] == 2025) & (df['pass_attempts'] >= 120) & (df['rush_attempts'] >= 20)].copy()
s25['rush_ypg'] = s25['rushing_yards'] / s25['total_games']

print('='*80)
print('2025 MOBILE QBs (120+ pass attempts, 20+ rush attempts):')
print('='*80)
result = s25[['passer_player_name', 'rush_ypg', 'rushing_yards', 'rush_attempts', 'total_games']].sort_values('rush_ypg', ascending=False)
print(result.to_string(index=False))

print(f'\n\nMin Rush YPG: {s25["rush_ypg"].min():.2f}')
print(f'Max Rush YPG: {s25["rush_ypg"].max():.2f}')
print(f'\nQBs at maximum: {len(s25[s25["rush_ypg"] == s25["rush_ypg"].max()])}')

if len(s25[s25["rush_ypg"] == s25["rush_ypg"].max()]) > 1:
    print('\n⚠️ MULTIPLE QBs have the EXACT same max rush YPG (actual tie)')
else:
    print('\n✓ Only ONE QB has the max (correct - should only be one 100 score)')
