"""
HoopBase — Build Team Stats Table
Run this once:  python build_team_stats.py
"""

import mysql.connector

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "phsj7655",   # ← update this
    "database": "hoopbase",
}

print("Connecting...")
conn = mysql.connector.connect(**DB_CONFIG)
conn.autocommit = True
cur = conn.cursor()

# Step 1 — make sure the table exists
cur.execute("""
    CREATE TABLE IF NOT EXISTS team_career_stats (
        team         VARCHAR(5) PRIMARY KEY,
        total_pts    INT,
        total_shots  INT,
        fg_pct       FLOAT,
        games        INT
    )
""")

# Step 2 — clear it
print("Clearing old team stats...")
cur.execute("TRUNCATE TABLE team_career_stats")

# Step 3 — get all distinct teams
print("Getting team list...")
cur.execute("SELECT DISTINCT team FROM shots WHERE team IS NOT NULL AND team != ''")
teams = [row[0] for row in cur.fetchall()]
print(f"  Found {len(teams)} teams\n")

# Step 4 — one query per team, uses the idx_shot_team index so each is fast
for i, team in enumerate(teams, 1):
    c2 = conn.cursor()
    c2.execute("""
        SELECT %s,
            SUM(CASE WHEN shot_type='2-pointer' AND made=1 THEN 2
                     WHEN shot_type='3-pointer' AND made=1 THEN 3 ELSE 0 END),
            COUNT(*),
            ROUND(SUM(made)/COUNT(*)*100, 1),
            COUNT(DISTINCT game_id)
        FROM shots WHERE team = %s
    """, (team, team))
    row = c2.fetchone()
    c2.close()

    if row and row[0] is not None:
        c3 = conn.cursor()
        c3.execute("""
            INSERT IGNORE INTO team_career_stats
                (team, total_pts, total_shots, fg_pct, games)
            VALUES (%s, %s, %s, %s, %s)
        """, row)
        c3.close()

    print(f"  [{i}/{len(teams)}] {team} done")

cur.close()
conn.close()
print(f"\n✅ Done! {len(teams)} teams in team_career_stats.")
