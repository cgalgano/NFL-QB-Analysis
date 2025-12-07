# NFL QB Database - Complete Tables Reference

## Overview

This database contains comprehensive NFL quarterback data from 2010-2025, integrating multiple data sources to enable deep analysis of QB performance, contracts, and play-by-play execution. The database combines traditional statistics, advanced analytics (EPA, CPOE), player tracking metrics (Next Gen Stats), expert ratings (QBR, ELO), and financial data.

**Database Location:** `data_load/nfl_qb_data.db`  
**Total Tables:** 8 (6 primary analysis tables + 2 system tables)  
**Total Size:** ~1.4 GB  
**Time Period:** 2010-2025 (754,858 plays, 10,029 QB game logs)  
**Primary Use:** Custom QB rating systems, performance analysis, contract evaluation, situational analytics

### Database Purpose

This database supports multi-dimensional quarterback analysis by providing play-level, weekly, and season-level data across performance, tracking, and financial metrics. All tables are linked via `player_id` (GSIS unique identifier) enabling cross-table analysis.

---

## Database Schema & Relationships

![QB Database ERD](updated_qb_erd.png)

### Table Hierarchy by Granularity

**Season-level tables** (one row per QB per season):  
- `espn_qbr` - QBR components and EPA (502 rows)
- `nflelo_qb_rankings` - Comprehensive stats with ELO ratings (687 rows)

**Week-level tables** (one row per QB per week):  
- `next_gen_stats` - Advanced tracking metrics, week 0 = season total (5,697 rows)
- `qb_statistics` - Game logs with EPA and CPOE (10,029 rows)

**Contract-level tables** (one row per contract):  
- `player_contracts` - Salary and biographical info (1,939 rows)

**Play-level tables** (one row per play):  
- `play_by_play` - Every play with full context and analytics (754,858 rows)

### Join Relationships

```
espn_qbr
    |-- player_id / Season
    |
next_gen_stats
    |-- player_id / season / week
    |
nflelo_qb_rankings
    |-- player_id / Season
    |
qb_statistics
    |-- player_id / season / week
    |
player_contracts
    |-- player_id
    |
play_by_play
    |-- player_id / season / week
```

### Primary Join Keys

| Join Type | Use This Field | Notes |
|-----------|----------------|-------|
| **Cross-table QB identification** | `player_id` | GSIS ID (e.g., "00-0033873"), unique and consistent across all tables |
| **Season aggregation** | `Season` or `season` | Some tables capitalize, some don't - be mindful |
| **Week matching** | `week` | Only in weekly tables (qb_statistics, next_gen_stats) |
| **Game matching** | `game_id` | Only in play_by_play |

### Important Notes

1. **player_id is the primary key:**
   - Use `player_id` for all joins (GSIS ID like "00-0033873")
   - Never changes even if player switches teams
   - More reliable than player names which may have spelling variations

2. **Season field naming:**
   - `Season` (capitalized): `espn_qbr`, `nflelo_qb_rankings`
   - `season` (lowercase): All other tables

3. **Week 0 in next_gen_stats:**
   - `week = 0` represents season totals
   - Use this for season-level joins with other tables

4. **Contract matching:**
   - Use `is_active = 1` to get current contracts only
   - Multiple contracts per player possible (extensions, new teams)

---

## Table of Contents
1. [ESPN QBR](#espn-qbr) - Season-level QBR ratings
2. [Next Gen Stats](#next-gen-stats) - Advanced tracking metrics
3. [NFL ELO QB Rankings](#nfl-elo-qb-rankings) - Comprehensive season stats
4. [QB Statistics](#qb-statistics) - Weekly game-by-game stats
5. [Player Contracts](#player-contracts) - Contract & salary data
6. [Play-by-Play](#play-by-play) - Every play 2010-2025

---

## ESPN QBR

**Table:** `espn_qbr`  
**Granularity:** Season-level (one row per QB per season)  
**Rows:** 502  
**Time Period:** 2010-2025  
**Purpose:** ESPN's proprietary Total Quarterback Rating with component breakdowns

### What This Table Tells You
ESPN QBR is a 0-100 rating that measures QB contribution to winning, accounting for every action on every play. This table provides the overall QBR plus its underlying components (passing, rushing, sacks, penalties) and relates it to EPA and Points Added Above Average.

### Fields (14 columns)

| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `RK` | INTEGER | Season rank by QBR | `1` |
| `QBR` | REAL | Total QBR score (0-100, higher is better) | `79.1` |
| `PAA` | REAL | Points Added Above Average per game | `52.0` |
| `PLAYS` | INTEGER | Total plays evaluated for QBR | `574` |
| `EPA` | REAL | Expected Points Added (total contribution) | `79.1` |
| `PASS` | REAL | QBR points from passing plays | `66.7` |
| `RUN` | REAL | QBR points from rushing plays | `0.8` |
| `SACK` | REAL | QBR points lost to sacks (negative) | `-8.9` |
| `PEN` | REAL | QBR points from penalty plays | `2.8` |
| `RAW` | REAL | Raw QBR before opponent adjustments | `78.3` |
| `Season` | INTEGER | NFL season year | `2024` |
| `NAME` | TEXT | Abbreviated name from ESPN | `"L.Jackson"` |
| `player_name` | TEXT | Full name (standardized for joins) | `"Lamar Jackson"` |
| `player_id` | TEXT | GSIS player ID (unique identifier) | `"00-0036389"` |

### Notes
- QBR accounts for situations (score, time, field position), unlike passer rating
- PAA measures points above a replacement-level QB
- Each season is a separate row (Mahomes 2023 vs Mahomes 2024)

---

## Next Gen Stats

**Table:** `next_gen_stats`  
**Granularity:** Week-level (separate row for each QB each week, plus season totals)  
**Rows:** 5,697  
**Time Period:** 2016-2025 (NGS tracking started in 2016)  
**Purpose:** Advanced tracking metrics from player tracking technology (time to throw, throw depth, completion probability)

### What This Table Tells You
Next Gen Stats uses player tracking technology (chips in shoulder pads) to measure throwing mechanics and decision-making that traditional stats miss. This includes how fast a QB releases the ball, how deep they throw, how tight the windows are, and whether they're beating expected completion rates.

### Fields (30 columns)

#### Identifiers
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `season` | INTEGER | NFL season year | `2024` |
| `season_type` | TEXT | Regular/postseason | `"REG"` |
| `week` | INTEGER | Week number (0 = season total) | `1` or `0` |
| `player_id` | TEXT | GSIS unique identifier | `"00-0036389"` |
| `player_name` | TEXT | Full name for joins | `"Lamar Jackson"` |
| `player_display_name` | TEXT | Display format | `"Lamar Jackson"` |
| `player_first_name` | TEXT | First name | `"Lamar"` |
| `player_last_name` | TEXT | Last name | `"Jackson"` |
| `player_short_name` | TEXT | Abbreviated | `"L.Jackson"` |
| `player_jersey_number` | INTEGER | Jersey # | `8` |
| `player_position` | TEXT | Position | `"QB"` |
| `team_abbr` | TEXT | Team abbreviation | `"BAL"` |

#### Throwing Mechanics & Decision Making
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `avg_time_to_throw` | REAL | Seconds from snap to release | `2.58` |
| `avg_completed_air_yards` | REAL | Air distance on completions only | `6.2` |
| `avg_intended_air_yards` | REAL | Air distance on all throws (inc incomplete) | `7.9` |
| `avg_air_yards_differential` | REAL | Completed - intended (measures risk) | `-1.7` |
| `aggressiveness` | REAL | % of passes into tight coverage (≤1 yd separation) | `18.2` |
| `max_completed_air_distance` | REAL | Longest completed air yards | `58.4` |
| `avg_air_yards_to_sticks` | REAL | How far past/short of 1st down marker | `-0.8` |
| `avg_air_distance` | REAL | Average intended depth of target | `8.7` |
| `max_air_distance` | REAL | Deepest throw attempted | `62.1` |

#### Completion Probability (AI-Powered)
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `expected_completion_percentage` | REAL | AI model prediction based on coverage, distance, etc. | `62.5` |
| `completion_percentage_above_expectation` | REAL | **CPOE** - actual minus expected (key metric) | `+5.2` |

#### Traditional Stats (for context)
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `attempts` | INTEGER | Pass attempts | `387` |
| `pass_yards` | INTEGER | Passing yards | `3,678` |
| `pass_touchdowns` | INTEGER | TD passes | `28` |
| `interceptions` | INTEGER | INTs thrown | `9` |
| `passer_rating` | REAL | NFL passer rating | `102.7` |
| `completions` | INTEGER | Completed passes | `267` |
| `completion_percentage` | REAL | Completion % | `69.0` |

### Notes
- Fast release: < 2.4s, Slow: > 2.8s
- CPOE measures accuracy independent of receiver quality
- Week 0 represents full season totals for season-level analysis
- Aggressiveness measures throws into tight coverage

---

## NFL ELO QB Rankings

**Table:** `nflelo_qb_rankings`  
**Granularity:** Season-level (one row per QB per season)  
**Rows:** 687  
**Time Period:** 2010-2025  
**Purpose:** Most comprehensive season stats table - combines traditional stats, advanced analytics, ELO ratings, and situational metrics

### What This Table Tells You
Most comprehensive season stats table combining traditional box scores, advanced efficiency metrics (EPA, WPA, CPOE), ELO ratings, air yards, and clutch performance indicators.

### Fields (47 columns)

#### Identifiers
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `player_name` | TEXT | Full name (standardized) | `"Patrick Mahomes"` |
| `player_id` | TEXT | GSIS unique identifier | `"00-0033873"` |
| `Season` | INTEGER | NFL season year | `2024` |
| `Starts` | INTEGER | Games started | `17` |

#### ELO & Win Probability
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `QB Elo` | REAL | ELO rating (1200-1800 range, higher = better) | `1687.5` |
| `Change_Week` | REAL | Average weekly ELO change | `+2.3` |
| `Change_year` | REAL | Total season ELO change | `+45.8` |
| `Total WPA` | REAL | Total win probability added (season sum) | `3.47` |
| `WPA / DB` | REAL | Win probability added per dropback | `0.068` |
| `Points` | REAL | Expected points contribution | `127.8` |
| `Total` | REAL | Total points above average | `89.2` |
| `/ DB` | REAL | Points per dropback | `0.18` |

#### Passing Efficiency
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `Comp` | INTEGER | Completions | `401` |
| `Atts` | INTEGER | Pass attempts | `597` |
| `Comp_percent` | REAL | Completion % (0-100) | `67.2` |
| `CPOE` | REAL | Completion % Over Expected (-20 to +20) | `+4.8` |
| `Yards` | INTEGER | Passing yards | `4,183` |
| `YPA` | REAL | Yards per attempt | `7.01` |
| `ANY/A` | REAL | Adjusted Net Yards/Attempt (best efficiency metric) | `6.89` |
| `Passer Rtg` | REAL | NFL passer rating (0-158.3) | `92.6` |

#### Passing Outcomes
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `TDs` | INTEGER | Passing touchdowns | `29` |
| `INTs` | INTEGER | Interceptions thrown | `14` |
| `TD%` | REAL | TD rate (% of attempts) | `4.86` |
| `INT%` | REAL | INT rate (% of attempts) | `2.35` |
| `TD%-INT%` | REAL | TD rate minus INT rate (higher = better) | `2.51` |
| `Inc` | REAL | Incompletion rate | `32.8` |

#### Passing Detail
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `Air Yards` | REAL | Total air yards (before catch) | `2,847` |
| `YAC` | REAL | Total yards after catch | `1,336` |
| `aDOT` | REAL | Average depth of target (air yards/attempt) | `8.2` |
| `vs Sticks` | REAL | Avg throw distance vs 1st down marker | `-0.3` |

#### Rushing
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `Carries` | INTEGER | Rush attempts | `58` |
| `Yards.1` | INTEGER | Rushing yards | `423` |
| `YPC` | REAL | Yards per carry | `7.29` |
| `TDs.1` | INTEGER | Rushing touchdowns | `2` |
| `Rushing` | REAL | Expected points from rushing | `12.3` |

#### Sacks & Pressure
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `Sacks` | INTEGER | Times sacked | `29` |
| `Sacks.1` | REAL | Sack rate or EPA impact | `-8.7` |

#### Team Performance & Clutch
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `W` | INTEGER | Wins as starter | `11` |
| `L` | INTEGER | Losses as starter | `6` |
| `T` | INTEGER | Ties | `0` |
| `CB` | INTEGER | 4th quarter comebacks | `3` |
| `CB Opps` | INTEGER | Comeback opportunities (games trailing in 4Q) | `7` |
| `CB%` | REAL | Comeback success rate | `42.9` |

#### Other
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `QBR` | REAL | ESPN Total QBR (0-100) | `79.1` |
| `Success` | REAL | Success rate (% of plays gaining expected value) | `51.2` |
| `Penalties` | REAL | Penalty rate | `2.1` |

### Notes
- ELO adjusts for opponent strength and era (1600+ elite, 1500-1600 very good, 1400-1500 average)
- ANY/A is the best single efficiency metric (accounts for TDs, INTs, sacks)
- TD%-INT% benchmarks: elite 3%+, average 1.5-2.5%

---

## QB Statistics

**Table:** `qb_statistics`  
**Granularity:** Weekly game-level (one row per QB per game)  
**Rows:** 10,029  
**Time Period:** 2010-2025  
**Purpose:** Detailed week-by-week game logs from nflreadpy with EPA, CPOE, and advanced metrics

### What This Table Tells You
This is your most granular traditional stats view - every QB appearance in every game is a separate row. Unlike season aggregations, you can see game-to-game variance, matchup effects, and performance trends. Includes EPA and CPOE at the game level, making it perfect for analyzing consistency and situational performance.

### Fields (41 columns)

#### Identifiers & Context
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `player_id` | TEXT | GSIS unique identifier | `"00-0034857"` |
| `player_name` | TEXT | Full name (standardized) | `"Josh Allen"` |
| `position` | TEXT | Position | `"QB"` |
| `position_group` | TEXT | Position group | `"QB"` |
| `headshot_url` | TEXT | URL to player photo | `"https://..."` |
| `season` | INTEGER | NFL season year | `2024` |
| `week` | INTEGER | Week number (1-18) | `12` |
| `season_type` | TEXT | Regular/postseason | `"REG"` (or `"POST"`, `"PRE"`) |
| `team` | TEXT | QB's team abbreviation | `"BUF"` |
| `opponent_team` | TEXT | Opposing team | `"KC"` |

#### Passing Statistics
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `completions` | INTEGER | Passes completed | `23` |
| `attempts` | INTEGER | Pass attempts | `34` |
| `completion_pct` | REAL | Completion % (0-100) | `67.6` |
| `passing_yards` | INTEGER | Passing yards | `237` |
| `yards_per_attempt` | REAL | Yards per attempt | `6.97` |
| `passing_tds` | INTEGER | Passing touchdowns | `2` |
| `passing_interceptions` | INTEGER | Interceptions thrown | `0` |
| `td_int_ratio` | REAL | TD/INT ratio (null if 0 INTs) | `null` |

#### Passing Detail
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `passing_air_yards` | INTEGER | Total air yards (before catch) | `312` |
| `passing_yards_after_catch` | INTEGER | Total yards after catch | `-75` (negative if sacks) |
| `pacr` | REAL | Pass Air Conversion Ratio (completions/air yards) | `0.76` |
| `passing_first_downs` | INTEGER | First downs via pass | `14` |
| `passing_2pt_conversions` | INTEGER | 2-point conversion passes | `0` |

#### Advanced Passing Metrics
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `passing_epa` | REAL | Expected Points Added from passing | `8.3` |
| `passing_cpoe` | REAL | Completion % Over Expected | `+2.1` |

#### Sacks
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `sacks_suffered` | INTEGER | Times sacked | `2` |
| `sack_yards_lost` | INTEGER | Yards lost to sacks | `12` |
| `sack_fumbles` | INTEGER | Fumbles on sacks | `0` |
| `sack_fumbles_lost` | INTEGER | Lost fumbles on sacks | `0` |

#### Rushing Statistics
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `carries` | INTEGER | Rush attempts | `8` |
| `rushing_yards` | INTEGER | Rushing yards | `48` |
| `rushing_tds` | INTEGER | Rushing touchdowns | `1` |
| `rushing_fumbles` | INTEGER | Rush fumbles (includes lost + recovered) | `1` |
| `rushing_fumbles_lost` | INTEGER | Lost rush fumbles | `0` |
| `rushing_first_downs` | INTEGER | First downs via rush | `3` |
| `rushing_2pt_conversions` | INTEGER | 2-point rush conversions | `0` |

#### Advanced Rushing Metrics
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `rushing_epa` | REAL | Expected Points Added from rushing | `4.2` |

#### Aggregate Metrics
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `total_epa` | REAL | Combined passing + rushing EPA | `12.5` |
| `dropbacks` | INTEGER | Total dropbacks (attempts + sacks) | `36` |
| `turnover_pct` | REAL | Turnover rate (turnovers/touches %) | `0.0` |
| `negative_play_pct` | REAL | % of plays losing yards | `16.7` |

### Notes
- EPA per game: positive = above average, negative = below
- Total EPA combines passing and rushing for dual-threat QBs
- Dropbacks = attempts + sacks (more accurate than attempts alone)

---

## Player Contracts

**Table:** `player_contracts`  
**Granularity:** Contract-level (one row per QB contract)  
**Rows:** 1,939  
**Time Period:** 2006-present (only QBs signed after 2005)  
**Purpose:** Contract details including salary, guarantees, inflation adjustments, and draft information

### What This Table Tells You
Every QB contract signed since 2006 with financial details and player biographical info. Use this to analyze QB market value, correlate performance with salary, identify value contracts, and understand draft pedigree. Inflation-adjusted fields allow fair comparisons across eras.

### Fields (26 columns)

#### Contract Financial Overview
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `contract_id` | INTEGER | Unique contract identifier | `12345` |
| `player_name` | TEXT | Full name (standardized) | `"Patrick Mahomes"` |
| `player_id` | TEXT | GSIS unique identifier | `"00-0033873"` |
| `position` | TEXT | Position (always QB in this table) | `"QB"` |
| `team` | TEXT | Team abbreviation | `"KC"` |
| `is_active` | INTEGER | 1 if contract still active, 0 if expired | `1` |
| `year_signed` | INTEGER | Year contract was signed | `2020` |
| `years` | INTEGER | Contract length in years | `10` |
| `value` | REAL | Total contract value in millions | `450.0` |
| `apy` | REAL | Average per year in millions | `45.0` |
| `guaranteed` | REAL | Guaranteed money in millions | `141.4` |
| `apy_cap_pct` | REAL | APY as % of salary cap (0-1 scale) | `0.208` |

#### Inflation-Adjusted (2025 dollars)
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `inflated_value` | REAL | Contract value adjusted to 2025 dollars | `487.2` |
| `inflated_apy` | REAL | APY adjusted to 2025 dollars | `48.7` |
| `inflated_guaranteed` | REAL | Guaranteed $ adjusted to 2025 dollars | `153.1` |

#### Player Biographical Info
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `player_page` | TEXT | URL to Over The Cap player page | `"https://overthecap.com/player/..."` |
| `otc_id` | INTEGER | Over The Cap database ID | `5678` |
| `date_of_birth` | TEXT | Date of birth | `"1995-09-17"` |
| `height` | REAL | Height in inches | `74.0` (6'2") |
| `weight` | REAL | Weight in pounds | `230.0` |
| `college` | TEXT | College attended | `"Texas Tech"` |

#### Draft Information
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `draft_year` | INTEGER | Year drafted | `2017` |
| `draft_round` | INTEGER | Draft round | `1` |
| `draft_overall` | INTEGER | Overall pick number | `10` |
| `draft_team` | TEXT | Team that drafted player | `"KC"` |

#### Detailed Breakdown
| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `cols` | TEXT | JSON array with year-by-year cap hits, bonuses, guarantees | `"[{\"year\": 2020, \"cap_hit\": 5.3M...}]"` |

### Notes
- APY cap % benchmarks: elite 15-22%, good starters 8-15%, backups < 5%
- Use `inflated_` fields for fair cross-era comparisons
- Filter `is_active = 1` for current contracts

---

## Play-by-Play

**Table:** `play_by_play`  
**Granularity:** Play-level (one row per play)  
**Rows:** 754,858  
**Time Period:** 2010-2025  
**Purpose:** Every single play from 2010-2025 with QB-relevant analytics

### What This Table Tells You
This is the most granular data in the database - every play is a row. Contains 131 QB-relevant fields including EPA, WPA, CPOE, air yards, pressure metrics, and situational context. Use this for play-level analysis, building custom aggregations, or studying specific game situations.

### Quick Reference

**Total Fields:** 132 (131 original + `player_name` added for joins)

#### Key Field Categories:
- **Identifiers:** `play_id`, `game_id`, `passer_player_id`, `passer_player_name`, `player_name`
- **Context:** `season`, `week`, `down`, `ydstogo`, `yardline_100`, `score_differential`, `half_seconds_remaining`
- **Core Metrics:** `epa`, `cpoe`, `wpa`, `success`
- **Passing:** `air_yards`, `yards_after_catch`, `complete_pass`, `pass_touchdown`, `interception`, `pass_length`, `pass_location`
- **Pressure:** `qb_hit`, `sack`, `qb_scramble`, `time_to_throw`
- **Expected:** `xyac_epa`, `xpass`, `pass_oe`
- **Receiver:** `receiver_player_name`, `target_share`, `air_yards_share`

#### Example Field Values:
| Field | Example Value | Meaning |
|-------|---------------|----------|
| `epa` | `+2.3` | Added 2.3 expected points (great play) |
| `cpoe` | `+8.2` | 8.2% more likely to complete than expected |
| `air_yards` | `45` | Threw 45 yards in the air |
| `yards_after_catch` | `12` | Receiver gained 12 yards after catch |
| `qb_hit` | `1` | QB was hit on this play |
| `success` | `1` | Play was successful (gained expected value) |
| `pass_location` | `"middle"` | Pass was to the middle of the field |
| `pass_length` | `"deep"` | Deep pass (> 20 yards) |

### Complete Documentation
For full field descriptions, data types, and usage examples, see:

**[PLAYBYPLAY_FIELDS_GUIDE.md](PLAYBYPLAY_FIELDS_GUIDE.md)**

The separate guide includes:
- All 131 fields with descriptions and examples
- Field categories (EPA, passing, rushing, situational, etc.)
- Common query patterns for play-by-play analysis
- Analysis ideas and use cases
- Database index information

### Notes
- 754,858 total plays across 16 seasons
- Indexed on `player_id`, `season`, `week`, `game_id`, `play_type`
- Filter `qb_dropback = 1` for QB-specific plays (327,577 plays)
