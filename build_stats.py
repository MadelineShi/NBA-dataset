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
    "password": "phsj7655", 
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
    player_name VARCHAR(100),
    team_name VARCHAR(5),
    total_pts INT,
    FGA INT,
    FGM INT,
    FG_PCT FLOAT,
    TPA INT,
    TPM INT,
    THREE_PCT FLOAT,
    games_played INT,
    PRIMARY KEY (player_name, team_name)
)
""")

print("Clearing old stats...")
cur.execute("TRUNCATE TABLE player_career_stats")

print("Getting player list...")
cur.execute("SELECT DISTINCT player_name FROM Shot WHERE player_name IS NOT NULL AND player_name != ''")
players = [row[0] for row in cur.fetchall()]

STAT_SQL = """
    SELECT
        %s,
        MAX(team_name),
        SUM(CASE WHEN shot_type='2-pointer' AND made=1 THEN 2
                 WHEN shot_type='3-pointer' AND made=1 THEN 3 ELSE 0 END),
        COUNT(*),
        SUM(made),
        ROUND(SUM(made)/COUNT(*)*100, 1),
        SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END),
        SUM(CASE WHEN shot_type='3-pointer' AND made=1 THEN 1 ELSE 0 END),
        ROUND(SUM(CASE WHEN shot_type='3-pointer' AND made=1 THEN 1 ELSE 0 END)
              / NULLIF(SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END),0)*100, 1),
        COUNT(DISTINCT game_id)
    FROM Shot
    WHERE player_name = %s
"""

INSERT_SQL = """
    INSERT IGNORE INTO player_career_stats
    (player_name, team_name, total_pts, FGA, FGM, FG_PCT, TPA, TPM, THREE_PCT, games_played)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""

for player in players:
    cur.execute(STAT_SQL, (player, player))
    row = cur.fetchone()
    if row:
        cur.execute(INSERT_SQL, row)

cur.close()
conn.close()

print("✅ player stats built")