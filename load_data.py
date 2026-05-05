"""
HoopBase — Data Loader (Shot Log Edition)
CSC 353, Davidson College, Spring 2026

Reads all per-game CSV files from a folder and loads them into MySQL.
Each CSV is one game (~1400 shot rows). Handles 4000+ files.

Prerequisites:  pip install mysql-connector-python pandas

Usage:
  1. Put all your game CSV files in a folder (e.g. ./data/)
  2. Update DB_CONFIG below with your MySQL password
  3. Update DATA_DIR to point at your CSV folder
  4. Run:  python load_data.py
"""

import os
import glob
import pandas as pd
import mysql.connector
from mysql.connector import Error

# ── config ────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "gha$bbhisA23rtyuiop0999",   # ← update this
    "database": "hoopbase2",
}

# Folder containing all your game CSV files
DATA_DIR = "data"

# How many rows to INSERT per batch (tune if you hit memory issues)
BATCH_SIZE = 2000
COMMIT_EVERY = 50
# ─────────────────────────────────────────────────────────────────────────────


def get_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


def parse_game_id(game_id):
    """
    game_id format: YYYYMMDD0XXX  e.g. '202203130ATL'
    Returns (date, home_team, season_year)
    Season year = calendar year, but Jan/Feb belong to previous season
    e.g. games in Jan 2022 are season 2021-22 → season_year = 2021
    """
    try:
        date_str  = game_id[:8]
        home_team = game_id[9:]
        from datetime import datetime
        game_date = datetime.strptime(date_str, "%Y%m%d").date()
        season_year = game_date.year if game_date.month >= 10 else game_date.year - 1
        return game_date, home_team, season_year
    except Exception:
        return None, game_id[-3:], None


def load_all(conn):
    cursor = conn.cursor()

    csv_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    if not csv_files:
        print(f"  ✗ No CSV files found in '{DATA_DIR}'. Check DATA_DIR in load_data.py.")
        return

    print(f"  Found {len(csv_files)} CSV files.\n")

    games_inserted = 0
    shots_inserted = 0
    files_skipped  = 0
    skipped_files = []

    player_cache = {}

    for i, filepath in enumerate(csv_files, 1):
        filename = os.path.basename(filepath)
        if i % 100 == 0 or i == 1:
            print(f"  [{i}/{len(csv_files)}] Processing {filename}…")

        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            print(f"    ⚠ Could not read {filename}: {e}")
            files_skipped += 1
            skipped_files.append(filename)
            continue

        # ── drop the duplicate index columns Kaggle adds ──────────────────
        drop_cols = [c for c in df.columns if c.startswith("Unnamed")]
        df = df.drop(columns=drop_cols)

        # Normalise column names (lowercase, strip spaces)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        if df.empty or ("game_id" not in df.columns and "match_id" not in df.columns):
            files_skipped += 1
            skipped_files.append(filename)
            continue

        # ── one game_id per file ─────────────────────────────────────────
        game_id = str(df["game_id"].iloc[0]) if "game_id" in df.columns else str(df["match_id"].iloc[0])
        game_date, home_team, season_year = parse_game_id(game_id)

        opponent_team = None
        if "opp" in df.columns:
            opponent_team = str(df["opp"].iloc[0]).replace("'", "").strip().upper()

        # Insert teams first because Game and Shot reference Team
        teams_in_file = set()

        if home_team:
            teams_in_file.add(home_team.strip().upper())
        if opponent_team:
            teams_in_file.add(opponent_team)

        if "team" in df.columns:
            teams_in_file.update(
                df["team"]
                .dropna()
                .astype(str)
                .str.strip()
                .str.upper()
                .tolist()
            )

        if teams_in_file:
            cursor.executemany(
                "INSERT IGNORE INTO Team (team_name) VALUES (%s)",
                [(team,) for team in teams_in_file if team]
            )

        # Insert game row (IGNORE if already loaded — safe to re-run)
        cursor.execute(
            """INSERT IGNORE INTO Game (game_id, game_date, season_year, home_team, opponent_team)
               VALUES (%s, %s, %s, %s, %s)""",
            (game_id, game_date, season_year, home_team, opponent_team)
        )
        games_inserted += cursor.rowcount

        # ── prepare shot rows ─────────────────────────────────────────────
        # Insert and cache all players in this file at once
        players_in_file = (
            df["player"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

        new_players = [(p,) for p in players_in_file if p and p not in player_cache]

        if new_players:
            cursor.executemany(
                "INSERT IGNORE INTO Player (player_name) VALUES (%s)",
                new_players
            )

            placeholders = ",".join(["%s"] * len(players_in_file))
            cursor.execute(
                f"SELECT player_id, player_name FROM Player WHERE player_name IN ({placeholders})",
                tuple(players_in_file)
            )

            for player_id, player_name in cursor.fetchall():
                player_cache[player_name] = player_id

        shot_rows = []

        for _, row_dict in df.iterrows():

            player_name = str(row_dict.get("player", "")).strip()
            if not player_name:
                continue

            player_id = player_cache.get(player_name)
            if player_id is None:
                continue

            shot_type_raw = str(row_dict.get("shot_type", "")).strip()

            if "3" in shot_type_raw:
                shot_type = "3"
            elif "2" in shot_type_raw:
                shot_type = "2"
            else:
                shot_type = None
            
            quarter_raw = str(row_dict.get("quarter", "")).strip()
            if quarter_raw:
                quarter = quarter_raw[0]  
            else:
                quarter = None
                
            time_remaining_raw = str(row_dict.get("time_remaining", "")).strip()
            if ":" in time_remaining_raw:
                time_remaining = time_remaining_raw.split(":")[0]
            else:
                time_remaining = None
                
            shot_rows.append((
                game_id,
                player_id,
                str(row_dict.get("team", "")).strip().upper(),
                shot_type,
                1 if str(row_dict.get("made", "False")).lower() in ("true", "1", "yes") else 0,
                int(row_dict["distance"]) if pd.notna(row_dict.get("distance")) else None,
                float(row_dict["shotx"]) if pd.notna(row_dict.get("shotx")) else None,
                float(row_dict["shoty"]) if pd.notna(row_dict.get("shoty")) else None,
                quarter,
                time_remaining,
            ))
            
        if i == 1:
            print("DEBUG shot_rows:", len(shot_rows))
        # Batch insert
        for start in range(0, len(shot_rows), BATCH_SIZE):
            batch = shot_rows[start:start + BATCH_SIZE]
            cursor.executemany(
                """INSERT INTO Shot
                       (game_id, player_id, team_name, shot_type, made,
                        distance, shotX, shotY, quarter, time_remaining)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                batch
            )
            shots_inserted += len(batch)

        if i % COMMIT_EVERY == 0:
            conn.commit()

    conn.commit()
    cursor.close()

    print(f"\n  ✓ Games inserted : {games_inserted}")
    print(f"  ✓ Shots inserted : {shots_inserted:,}")
    print(f"  ⚠ Files skipped  : {files_skipped}")
    print(f"  ⚠ Skipped files  : {skipped_files}")


if __name__ == "__main__":
    print("=== HoopBase Data Loader ===\n")
    print("Connecting to MySQL…")
    try:
        conn = get_connection()
        print("  ✓ Connected\n")
    except Error as e:
        print(f"  ✗ Connection failed: {e}")
        raise

    print("Loading shot data from CSVs…")
    load_all(conn)
    conn.close()

    print("\n✅ Done! Your hoopbase database is ready.")
    print("   Run:  python app.py   then open http://localhost:5000")