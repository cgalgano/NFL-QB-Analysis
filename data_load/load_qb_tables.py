"""
Refresh the qb_statistics and next_gen_stats tables from nflreadpy, and seed the
espn_qbr / nflelo_qb_rankings tables from tracked snapshots when they are missing.
Existing tables only have the last two seasons replaced; missing tables are built in full.
"""

import sqlite3
import sys
from pathlib import Path

import nflreadpy
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent
DB_PATH = DATA_DIR / "nfl_qb_data.db"
REFERENCE_DIR = DATA_DIR / "reference"
START_YEAR = 2010
NGS_START_YEAR = 2016
CURRENT_SEASON = nflreadpy.get_current_season()


def table_columns(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def seasons_to_load(conn, table, start_year):
    if table_columns(conn, table):
        return [CURRENT_SEASON - 1, CURRENT_SEASON]
    return list(range(start_year, CURRENT_SEASON + 1))


def write_seasons(conn, table, df, seasons):
    existing_cols = table_columns(conn, table)
    if not existing_cols:
        df.to_sql(table, conn, index=False)
        return
    placeholders = ",".join("?" * len(seasons))
    conn.execute(f"DELETE FROM {table} WHERE season IN ({placeholders})", seasons)
    df[[c for c in df.columns if c in existing_cols]].to_sql(table, conn, if_exists="append", index=False)


def refresh_qb_statistics(conn):
    seasons = seasons_to_load(conn, "qb_statistics", START_YEAR)
    stats = nflreadpy.load_player_stats(seasons).to_pandas()
    stats = stats[stats["position"] == "QB"]
    # The database stores full names in player_name (e.g. 'Lamar Jackson')
    stats = stats.drop(columns="player_name").rename(columns={"player_display_name": "player_name"})
    write_seasons(conn, "qb_statistics", stats, seasons)
    print(f"qb_statistics: {len(stats):,} rows for {seasons[0]}-{seasons[-1]}")


def refresh_next_gen_stats(conn):
    seasons = seasons_to_load(conn, "next_gen_stats", NGS_START_YEAR)
    ngs = nflreadpy.load_nextgen_stats(seasons).to_pandas()
    ngs = ngs.rename(columns={"player_gsis_id": "player_id"})
    write_seasons(conn, "next_gen_stats", ngs, seasons)
    print(f"next_gen_stats: {len(ngs):,} rows for {seasons[0]}-{seasons[-1]}")


def refresh_player_contracts(conn):
    contracts = nflreadpy.load_contracts().to_pandas()
    contracts = contracts.drop(columns=["season_history", "contract_history"], errors="ignore")
    contracts = contracts.rename(columns={"player": "player_name", "gsis_id": "player_id"})
    contracts.to_sql("player_contracts", conn, if_exists="replace", index=False)
    print(f"player_contracts: {len(contracts):,} rows")


def seed_reference_tables(conn):
    for table in ["espn_qbr", "nflelo_qb_rankings"]:
        if not table_columns(conn, table):
            pd.read_csv(REFERENCE_DIR / f"{table}.csv").to_sql(table, conn, index=False)
            print(f"{table}: loaded from reference snapshot")


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        refresh_qb_statistics(conn)
        refresh_next_gen_stats(conn)
        refresh_player_contracts(conn)
        seed_reference_tables(conn)
        conn.commit()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
