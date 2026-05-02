"""
HoopBase — Flask Backend (Shot Log Edition)
CSC 353, Davidson College, Spring 2026

All stats (FG%, points, 3P%, etc.) are derived live from the Shot table.

Routes
──────
  GET  /                              → home, top scorers this season
  GET  /search?q=&team=&year=&sort=   → player search
  GET  /player/<name>                 → career stats + shot chart
  GET  /compare?p1=&p2=               → side-by-side comparison
  GET  /teams                         → all teams
  GET  /team/<abbrev>?year=           → team season breakdown
  GET  /leaderboards                  → all-time top-10
  GET  /api/shots/<name>?year=        → JSON shot coordinates for chart
"""

"""
HoopBase — Flask Backend (Shot Log Edition)
"""

from flask import Flask, render_template, request, jsonify, abort
import mysql.connector

app = Flask(__name__)

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "phsj7655",
    "database": "hoopbase",
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def query(sql, params=(), one=False):
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows[0] if (one and rows) else rows


# ── helpers ─────────────────────────────────────────

PLAYER_STATS_SQL = """
    SELECT
        s.player_name,
        s.team_name,
        COUNT(*) AS FGA,
        SUM(s.made) AS FGM,
        ROUND(SUM(s.made) / COUNT(*) * 100, 1) AS FG_PCT,
        SUM(CASE WHEN s.shot_type='3-pointer' THEN 1 ELSE 0 END) AS TPA,
        SUM(CASE WHEN s.shot_type='3-pointer' AND s.made=1 THEN 1 ELSE 0 END) AS TPM,
        ROUND(
            SUM(CASE WHEN s.shot_type='3-pointer' AND s.made=1 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN s.shot_type='3-pointer' THEN 1 ELSE 0 END), 0)
            * 100, 1) AS THREE_PCT,
        SUM(CASE 
            WHEN s.shot_type='2-pointer' AND s.made=1 THEN 2
            WHEN s.shot_type='3-pointer' AND s.made=1 THEN 3
            ELSE 0 END) AS total_pts,
        COUNT(DISTINCT s.game_id) AS games_played
    FROM Shot s
    {join}
    WHERE {where}
    GROUP BY s.player_name, s.team_name
"""

def player_stats_query(name_filter=None, team_filter=None, year_filter=None,
                       sort="total_pts", limit=200):

    join  = "JOIN Game g ON g.game_id = s.game_id" if year_filter else ""

    wheres = ["1=1"]
    params = []

    if name_filter:
        wheres.append("s.player_name LIKE %s")
        params.append(f"%{name_filter}%")

    if team_filter:
        wheres.append("s.team_name = %s")
        params.append(team_filter.upper())

    if year_filter:
        wheres.append("g.season_year = %s")
        params.append(int(year_filter))

    SAFE_SORTS = {"FGA","FGM","FG_PCT","TPA","TPM","THREE_PCT","total_pts","games_played"}
    if sort not in SAFE_SORTS:
        sort = "total_pts"

    sql = PLAYER_STATS_SQL.format(join=join, where=" AND ".join(wheres))
    sql += f" HAVING games_played >= 5 ORDER BY {sort} DESC LIMIT {int(limit)}"

    return query(sql, params)


# ── Home ───────────────────────────────────────────

@app.route("/")
def home():
    latest_year = query("SELECT MAX(season_year) AS y FROM Game", one=True)["y"]

    top = player_stats_query(year_filter=latest_year, limit=10)

    teams = query("SELECT DISTINCT team_name FROM Shot ORDER BY team_name")
    years = query("SELECT DISTINCT season_year FROM Game WHERE season_year IS NOT NULL ORDER BY season_year DESC")

    return render_template("home.html",
                           top=top,
                           latest_year=latest_year,
                           teams=teams,
                           years=years)


# ── Search ─────────────────────────────────────────

@app.route("/search")
def search():
    q    = request.args.get("q", "").strip()
    team = request.args.get("team", "").strip()
    year = request.args.get("year", "").strip()
    sort = request.args.get("sort", "total_pts")

    SAFE_SORTS = {"total_pts","FGA","FGM","FG_PCT","TPA","THREE_PCT","games_played"}
    if sort not in SAFE_SORTS:
        sort = "total_pts"

    if not year:
        wheres = ["games_played >= 5"]
        params = []

        if q:
            wheres.append("player_name LIKE %s")
            params.append(f"%{q}%")

        if team:
            wheres.append("team_name = %s")
            params.append(team.upper())

        where = " AND ".join(wheres)

        results = query(f"""
            SELECT player_name, team_name, total_pts, FGA, FGM, FG_PCT, TPA, TPM, THREE_PCT, games_played
            FROM player_career_stats
            WHERE {where}
            ORDER BY {sort} DESC LIMIT 200
        """, params)

    else:
        results = player_stats_query(
            name_filter=q or None,
            team_filter=team or None,
            year_filter=year,
            sort=sort,
            limit=200
        )

    teams = query("SELECT DISTINCT team_name FROM Shot ORDER BY team_name")
    years = query("SELECT DISTINCT season_year FROM Game WHERE season_year IS NOT NULL ORDER BY season_year DESC")

    return render_template("search.html",
                           results=results,
                           teams=teams,
                           years=years,
                           q=q,
                           team=team,
                           year=year,
                           sort=sort)


# ── Player Detail ──────────────────────────────────

@app.route("/player/<path:player_name>")
def player_detail(player_name):

    career = query("""
        SELECT g.season_year,
               s.team_name,
               COUNT(*) AS FGA,
               SUM(s.made) AS FGM,
               ROUND(SUM(s.made)/COUNT(*)*100,1) AS FG_PCT,
               SUM(CASE WHEN s.shot_type='3-pointer' THEN 1 ELSE 0 END) AS TPA,
               SUM(CASE WHEN s.shot_type='3-pointer' AND s.made=1 THEN 1 ELSE 0 END) AS TPM,
               ROUND(
                 SUM(CASE WHEN s.shot_type='3-pointer' AND s.made=1 THEN 1 ELSE 0 END)
                 / NULLIF(SUM(CASE WHEN s.shot_type='3-pointer' THEN 1 ELSE 0 END),0)
                 *100,1) AS THREE_PCT,
               SUM(CASE 
                    WHEN s.shot_type='2-pointer' AND s.made=1 THEN 2
                    WHEN s.shot_type='3-pointer' AND s.made=1 THEN 3
                    ELSE 0 END) AS total_pts,
               COUNT(DISTINCT s.game_id) AS games_played
        FROM Shot s
        JOIN Game g ON g.game_id = s.game_id
        WHERE s.player_name = %s
        GROUP BY g.season_year, s.team_name
        ORDER BY g.season_year
    """, (player_name,))

    if not career:
        abort(404)

    totals = query("""
        SELECT COUNT(*) AS FGA,
               SUM(made) AS FGM,
               ROUND(SUM(made)/COUNT(*)*100,1) AS FG_PCT,
               SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END) AS TPA,
               ROUND(
                 SUM(CASE WHEN shot_type='3-pointer' AND made=1 THEN 1 ELSE 0 END)
                 / NULLIF(SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END),0)
                 *100,1) AS THREE_PCT,
               SUM(CASE 
                    WHEN shot_type='2-pointer' AND made=1 THEN 2
                    WHEN shot_type='3-pointer' AND made=1 THEN 3
                    ELSE 0 END) AS total_pts,
               COUNT(DISTINCT game_id) AS games_played
        FROM Shot
        WHERE player_name = %s
    """, (player_name,), one=True)

    years = [r["season_year"] for r in career if r["season_year"]]

    return render_template("player.html",
                           name=player_name,
                           career=career,
                           totals=totals,
                           years=years)


# ── Shot API ───────────────────────────────────────

@app.route("/api/shots/<path:player_name>")
def api_shots(player_name):

    year = request.args.get("year", "").strip()

    if year:
        rows = query("""
            SELECT s.shotX, s.shotY, s.made, s.shot_type, s.distance
            FROM Shot s
            JOIN Game g ON g.game_id = s.game_id
            WHERE s.player_name = %s AND g.season_year = %s
        """, (player_name, int(year)))

    else:
        rows = query("""
            SELECT shotX, shotY, made, shot_type, distance
            FROM Shot
            WHERE player_name = %s
        """, (player_name,))

    return jsonify(rows)


# ── Compare ───────────────────────────────────────

@app.route("/compare")
def compare():

    p1_name = request.args.get("p1", "").strip()
    p2_name = request.args.get("p2", "").strip()

    p1_stats = p2_stats = None

    if p1_name and p2_name:

        def get_totals(name):
            return query("""
                SELECT COUNT(*) AS FGA,
                       SUM(made) AS FGM,
                       ROUND(SUM(made)/COUNT(*)*100,1) AS FG_PCT,
                       SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END) AS TPA,
                       ROUND(SUM(CASE WHEN shot_type='3-pointer' AND made=1 THEN 1 ELSE 0 END)
                             /NULLIF(SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END),0)*100,1) AS THREE_PCT,
                       SUM(CASE 
                            WHEN shot_type='2-pointer' AND made=1 THEN 2
                            WHEN shot_type='3-pointer' AND made=1 THEN 3
                            ELSE 0 END) AS total_pts,
                       COUNT(DISTINCT game_id) AS games_played
                FROM Shot
                WHERE player_name = %s
            """, (name,), one=True)

        p1_stats = get_totals(p1_name)
        p2_stats = get_totals(p2_name)

    all_players = query("SELECT DISTINCT player_name FROM Shot ORDER BY player_name LIMIT 10000")

    return render_template("compare.html",
                           p1_name=p1_name,
                           p2_name=p2_name,
                           p1_stats=p1_stats,
                           p2_stats=p2_stats,
                           all_players=all_players)


# ── run ───────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
