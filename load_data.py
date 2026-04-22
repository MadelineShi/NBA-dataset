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
    "database": "hoopbase",
}

# Folder containing all your game CSV files
DATA_DIR = "data"

# How many rows to INSERT per batch (tune if you hit memory issues)
BATCH_SIZE = 2000
# ─────────────────────────────────────────────────────────────────────────────


def get_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


def parse_match_id(match_id):
    """
    match_id format: YYYYMMDD0XXX  e.g. '202203130ATL'
    Returns (date, home_team, season_year)
    Season year = calendar year, but Jan/Feb belong to previous season
    e.g. games in Jan 2022 are season 2021-22 → season_year = 2021
    """
    try:
        date_str  = match_id[:8]          # '20220313'
        home_team = match_id[9:]          # 'ATL'  (skip the single digit game-number)
        from datetime import datetime
        game_date = datetime.strptime(date_str, "%Y%m%d").date()
        # NBA season starts Oct; Jan/Feb of year Y belong to season Y-1
        season_year = game_date.year if game_date.month >= 10 else game_date.year - 1
        return game_date, home_team, season_year
    except Exception:
        return None, match_id[-3:], None


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

    for i, filepath in enumerate(csv_files, 1):
        filename = os.path.basename(filepath)
        if i % 100 == 0 or i == 1:
            print(f"  [{i}/{len(csv_files)}] Processing {filename}…")

        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            print(f"    ⚠ Could not read {filename}: {e}")
            files_skipped += 1
            continue

        # ── drop the duplicate index columns Kaggle adds ──────────────────
        drop_cols = [c for c in df.columns if c.startswith("Unnamed")]
        df = df.drop(columns=drop_cols)

        if "match_id" not in df.columns or df.empty:
            files_skipped += 1
            continue

        # ── one match_id per file ─────────────────────────────────────────
        match_id  = str(df["match_id"].iloc[0])
        game_date, home_team, season_year = parse_match_id(match_id)

        # Insert game row (IGNORE if already loaded — safe to re-run)
        cursor.execute(
            """INSERT IGNORE INTO games (match_id, game_date, home_team, season_year)
               VALUES (%s, %s, %s, %s)""",
            (match_id, game_date, home_team, season_year)
        )
        games_inserted += cursor.rowcount

        # ── prepare shot rows ─────────────────────────────────────────────
        # Normalise column names (lowercase, strip spaces)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        col_map = {
            "shotx":          "shotX",
            "shoty":          "shotY",
            "shot_type":      "shot_type",
            "made":           "made",
            "distance":       "distance",
            "quarter":        "quarter",
            "time_remaining": "time_remaining",
            "player":         "player",
            "team":           "team",
        }

        shot_rows = []
        for _, row in df.iterrows():
            shot_rows.append((
                match_id,
                str(row.get("player", "")).strip(),
                str(row.get("team",   "")).strip().upper(),
                str(row.get("shot_type", "")).strip(),
                1 if str(row.get("made", "False")).lower() in ("true", "1", "yes") else 0,
                int(row["distance"])   if pd.notna(row.get("distance"))   else None,
                float(row["shotx"])    if pd.notna(row.get("shotx"))      else None,
                float(row["shoty"])    if pd.notna(row.get("shoty"))      else None,
                str(row.get("quarter", "")).strip()        or None,
                str(row.get("time_remaining", "")).strip() or None,
            ))

        # Batch insert
        for start in range(0, len(shot_rows), BATCH_SIZE):
            batch = shot_rows[start:start + BATCH_SIZE]
            cursor.executemany(
                """INSERT INTO shots
                       (match_id, player, team, shot_type, made,
                        distance, shotX, shotY, quarter, time_remaining)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                batch
            )
            shots_inserted += len(batch)

        conn.commit()

    cursor.close()
    print(f"\n  ✓ Games inserted : {games_inserted}")
    print(f"  ✓ Shots inserted : {shots_inserted:,}")
    print(f"  ⚠ Files skipped  : {files_skipped}")


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
