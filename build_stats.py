"""
HoopBase — Build Summary Stats Table
Run this once:  python build_stats.py

Does the same INSERT as the SQL version but processes players in small
batches so MySQL never times out.
"""

import mysql.connector

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "phsj7655",   # ← update this
    "database": "hoopbase",
}

def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn

print("Connecting...")
conn = get_db()
cur  = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS player_career_stats (
    player VARCHAR(100),
    team VARCHAR(5),
    total_pts INT,
    FGA INT,
    FGM INT,
    FG_PCT FLOAT,
    TPA INT,
    TPM INT,
    THREE_PCT FLOAT,
    games_played INT,
    PRIMARY KEY (player)
)
""")

# Step 1 — clear the table
print("Clearing old stats...")
cur.execute("TRUNCATE TABLE player_career_stats")

# Step 2 — get all distinct player names
print("Getting player list...")
cur.execute("SELECT DISTINCT player FROM shots WHERE player IS NOT NULL AND player != ''")
players = [row[0] for row in cur.fetchall()]
print(f"  Found {len(players)} players\n")

# Step 3 — compute and insert stats one player at a time
STAT_SQL = """
    SELECT
        %s,
        MAX(team),
        SUM(CASE WHEN shot_type='2-pointer' AND made=1 THEN 2
                 WHEN shot_type='3-pointer' AND made=1 THEN 3 ELSE 0 END),
        COUNT(*),
        SUM(made),
        ROUND(SUM(made)/COUNT(*)*100, 1),
        SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END),
        SUM(CASE WHEN shot_type='3-pointer' AND made=1 THEN 1 ELSE 0 END),
        ROUND(SUM(CASE WHEN shot_type='3-pointer' AND made=1 THEN 1 ELSE 0 END)
              / NULLIF(SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END),0)*100, 1),
        COUNT(DISTINCT match_id)
    FROM shots
    WHERE player = %s
"""

INSERT_SQL = """
    INSERT IGNORE INTO player_career_stats
        (player, team, total_pts, FGA, FGM, FG_PCT, TPA, TPM, THREE_PCT, games_played)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

inserted = 0
for i, player in enumerate(players, 1):
    cur.execute(STAT_SQL, (player, player))
    row = cur.fetchone()
    if row:
        cur.execute(INSERT_SQL, row)
        inserted += 1

    if i % 100 == 0 or i == len(players):
        print(f"  [{i}/{len(players)}] {inserted} players inserted...")

cur.close()
conn.close()
print(f"\n✅ Done! {inserted} players in player_career_stats.")