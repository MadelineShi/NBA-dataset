"""
HoopBase — Flask Backend (Shot Log Edition)
CSC 353, Davidson College, Spring 2026

All stats (FG%, points, 3P%, etc.) are derived live from the shots table.

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

from flask import Flask, render_template, request, jsonify, abort
import mysql.connector

app = Flask(__name__)

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "phsj7655",   # ← update this
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


# ── helpers ───────────────────────────────────────────────────────────────────
PLAYER_STATS_SQL = """
    SELECT
        s.player,
        s.team,
        COUNT(*)                                         AS FGA,
        SUM(s.made)                                      AS FGM,
        ROUND(SUM(s.made) / COUNT(*) * 100, 1)          AS FG_PCT,
        SUM(CASE WHEN s.shot_type='3-pointer' THEN 1 ELSE 0 END) AS TPA,
        SUM(CASE WHEN s.shot_type='3-pointer' AND s.made=1 THEN 1 ELSE 0 END) AS TPM,
        ROUND(
            SUM(CASE WHEN s.shot_type='3-pointer' AND s.made=1 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN s.shot_type='3-pointer' THEN 1 ELSE 0 END), 0)
            * 100, 1)                                    AS THREE_PCT,
        SUM(CASE WHEN s.shot_type='2-pointer' AND s.made=1 THEN 2
                 WHEN s.shot_type='3-pointer' AND s.made=1 THEN 3
                 ELSE 0 END)                             AS total_pts,
        COUNT(DISTINCT s.match_id)                       AS games_played
    FROM shots s
    {join}
    WHERE {where}
    GROUP BY s.player, s.team
"""

def player_stats_query(name_filter=None, team_filter=None, year_filter=None,
                       sort="total_pts", limit=200):
    join  = "JOIN games g ON g.match_id = s.match_id" if year_filter else ""
    wheres = ["1=1"]
    params = []
    if name_filter:
        wheres.append("s.player LIKE %s"); params.append(f"%{name_filter}%")
    if team_filter:
        wheres.append("s.team = %s"); params.append(team_filter.upper())
    if year_filter:
        wheres.append("g.season_year = %s"); params.append(int(year_filter))
    SAFE_SORTS = {"FGA","FGM","FG_PCT","TPA","TPM","THREE_PCT","total_pts","games_played"}
    if sort not in SAFE_SORTS:
        sort = "total_pts"
    sql = PLAYER_STATS_SQL.format(join=join, where=" AND ".join(wheres))
    sql += f" HAVING games_played >= 5 ORDER BY {sort} DESC LIMIT {int(limit)}"
    return query(sql, params)


# ── Home ──────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    latest_year = query("SELECT MAX(season_year) AS y FROM games", one=True)["y"]
    top = player_stats_query(year_filter=latest_year, limit=10)
    teams = query("SELECT DISTINCT team FROM shots ORDER BY team")
    years = query("SELECT DISTINCT season_year FROM games WHERE season_year IS NOT NULL ORDER BY season_year DESC")
    return render_template("home.html", top=top, latest_year=latest_year,
                           teams=teams, years=years)


# ── Search ────────────────────────────────────────────────────────────────────
@app.route("/search")
def search():
    q    = request.args.get("q",    "").strip()
    team = request.args.get("team", "").strip()
    year = request.args.get("year", "").strip()
    sort = request.args.get("sort", "total_pts")

    SAFE_SORTS = {"total_pts","FGA","FGM","FG_PCT","TPA","THREE_PCT","games_played"}
    if sort not in SAFE_SORTS:
        sort = "total_pts"

    # Use summary table when no year filter (fast), live query when year needed
    if not year:
        wheres = ["games_played >= 5"]
        params = []
        if q:
            wheres.append("player LIKE %s"); params.append(f"%{q}%")
        if team:
            wheres.append("team = %s"); params.append(team.upper())
        where = " AND ".join(wheres)
        results = query(f"""
            SELECT player, team, total_pts, FGA, FGM, FG_PCT, TPA, TPM, THREE_PCT, games_played
            FROM player_career_stats
            WHERE {where}
            ORDER BY {sort} DESC LIMIT 200
        """, params)
    else:
        results = player_stats_query(name_filter=q or None,
                                     team_filter=team or None,
                                     year_filter=year,
                                     sort=sort, limit=200)

    teams = query("SELECT DISTINCT team FROM shots ORDER BY team")
    years = query("SELECT DISTINCT season_year FROM games WHERE season_year IS NOT NULL ORDER BY season_year DESC")
    return render_template("search.html", results=results, teams=teams, years=years,
                           q=q, team=team, year=year, sort=sort)


# ── Player Detail ─────────────────────────────────────────────────────────────
@app.route("/player/<path:player_name>")
def player_detail(player_name):
    # Career season-by-season breakdown
    career = query("""
        SELECT g.season_year,
               s.team,
               COUNT(*)                                         AS FGA,
               SUM(s.made)                                     AS FGM,
               ROUND(SUM(s.made)/COUNT(*)*100, 1)              AS FG_PCT,
               SUM(CASE WHEN s.shot_type='3-pointer' THEN 1 ELSE 0 END) AS TPA,
               SUM(CASE WHEN s.shot_type='3-pointer' AND s.made=1 THEN 1 ELSE 0 END) AS TPM,
               ROUND(
                 SUM(CASE WHEN s.shot_type='3-pointer' AND s.made=1 THEN 1 ELSE 0 END)
                 / NULLIF(SUM(CASE WHEN s.shot_type='3-pointer' THEN 1 ELSE 0 END),0)
                 *100, 1)                                       AS THREE_PCT,
               SUM(CASE WHEN s.shot_type='2-pointer' AND s.made=1 THEN 2
                        WHEN s.shot_type='3-pointer' AND s.made=1 THEN 3
                        ELSE 0 END)                            AS total_pts,
               COUNT(DISTINCT s.match_id)                      AS games_played
        FROM shots s
        JOIN games g ON g.match_id = s.match_id
        WHERE s.player = %s
        GROUP BY g.season_year, s.team
        ORDER BY g.season_year
    """, (player_name,))

    if not career:
        abort(404)

    # Career totals
    totals = query("""
        SELECT COUNT(*)                                         AS FGA,
               SUM(made)                                       AS FGM,
               ROUND(SUM(made)/COUNT(*)*100, 1)                AS FG_PCT,
               SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END) AS TPA,
               ROUND(
                 SUM(CASE WHEN shot_type='3-pointer' AND made=1 THEN 1 ELSE 0 END)
                 / NULLIF(SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END),0)
                 *100, 1)                                      AS THREE_PCT,
               SUM(CASE WHEN shot_type='2-pointer' AND made=1 THEN 2
                        WHEN shot_type='3-pointer' AND made=1 THEN 3
                        ELSE 0 END)                            AS total_pts,
               COUNT(DISTINCT match_id)                        AS games_played
        FROM shots WHERE player = %s
    """, (player_name,), one=True)

    years = [r["season_year"] for r in career if r["season_year"]]
    return render_template("player.html", name=player_name,
                           career=career, totals=totals, years=years)


# ── Shot Chart API ────────────────────────────────────────────────────────────
@app.route("/api/shots/<path:player_name>")
def api_shots(player_name):
    year = request.args.get("year", "").strip()
    if year:
        rows = query("""
            SELECT s.shotX, s.shotY, s.made, s.shot_type, s.distance
            FROM shots s JOIN games g ON g.match_id = s.match_id
            WHERE s.player = %s AND g.season_year = %s
        """, (player_name, int(year)))
    else:
        rows = query("""
            SELECT shotX, shotY, made, shot_type, distance
            FROM shots WHERE player = %s
        """, (player_name,))
    return jsonify(rows)


# ── Compare ───────────────────────────────────────────────────────────────────
@app.route("/compare")
def compare():
    p1_name = request.args.get("p1", "").strip()
    p2_name = request.args.get("p2", "").strip()

    p1_stats = p2_stats = p1_career = p2_career = None

    if p1_name and p2_name:
        def get_totals(name):
            return query("""
                SELECT COUNT(*) AS FGA, SUM(made) AS FGM,
                       ROUND(SUM(made)/COUNT(*)*100,1) AS FG_PCT,
                       SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END) AS TPA,
                       ROUND(SUM(CASE WHEN shot_type='3-pointer' AND made=1 THEN 1 ELSE 0 END)
                             /NULLIF(SUM(CASE WHEN shot_type='3-pointer' THEN 1 ELSE 0 END),0)*100,1) AS THREE_PCT,
                       SUM(CASE WHEN shot_type='2-pointer' AND made=1 THEN 2
                                WHEN shot_type='3-pointer' AND made=1 THEN 3 ELSE 0 END) AS total_pts,
                       COUNT(DISTINCT match_id) AS games_played
                FROM shots WHERE player = %s
            """, (name,), one=True)

        p1_stats, p2_stats = get_totals(p1_name), get_totals(p2_name)

    # Autocomplete list (distinct player names)
    all_players = query("SELECT DISTINCT player FROM shots ORDER BY player LIMIT 10000")
    return render_template("compare.html", p1_name=p1_name, p2_name=p2_name,
                           p1_stats=p1_stats, p2_stats=p2_stats,
                           all_players=all_players)


# ── Teams ─────────────────────────────────────────────────────────────────────
@app.route("/teams")
def teams():
    teams = query("""
        SELECT team, total_pts, fg_pct, total_shots, games
        FROM team_career_stats
        ORDER BY total_pts DESC
    """)
    return render_template("teams.html", teams=teams)


# ── Team Detail ───────────────────────────────────────────────────────────────
@app.route("/team/<abbrev>")
def team_detail(abbrev):
    year = request.args.get("year", "").strip()
    abbrev = abbrev.upper()

    seasons = query("""
        SELECT g.season_year,
               COUNT(DISTINCT s.match_id)               AS games,
               ROUND(SUM(s.made)/COUNT(*)*100,1)        AS fg_pct,
               SUM(CASE WHEN s.shot_type='2-pointer' AND s.made=1 THEN 2
                        WHEN s.shot_type='3-pointer' AND s.made=1 THEN 3
                        ELSE 0 END)                     AS total_pts
        FROM shots s JOIN games g ON g.match_id=s.match_id
        WHERE s.team=%s AND g.season_year IS NOT NULL
        GROUP BY g.season_year ORDER BY g.season_year DESC
    """, (abbrev,))

    if not seasons:
        abort(404)

    year_filter = int(year) if year else seasons[0]["season_year"]

    top_players = query("""
        SELECT s.player,
               COUNT(*)                                         AS FGA,
               SUM(s.made)                                      AS FGM,
               ROUND(SUM(s.made)/COUNT(*)*100,1)               AS FG_PCT,
               SUM(CASE WHEN s.shot_type='2-pointer' AND s.made=1 THEN 2
                        WHEN s.shot_type='3-pointer' AND s.made=1 THEN 3
                        ELSE 0 END)                            AS total_pts,
               COUNT(DISTINCT s.match_id)                      AS games_played
        FROM shots s JOIN games g ON g.match_id=s.match_id
        WHERE s.team=%s AND g.season_year=%s
        GROUP BY s.player
        HAVING games_played >= 3
        ORDER BY total_pts DESC LIMIT 15
    """, (abbrev, year_filter))

    years = [r["season_year"] for r in seasons]
    return render_template("team.html", abbrev=abbrev, seasons=seasons,
                           top_players=top_players, year_filter=year_filter,
                           years=years)


# ── Leaderboards ──────────────────────────────────────────────────────────────
@app.route("/leaderboards")
def leaderboards():
    boards = {
        "Total Points": query("""
            SELECT player, team, total_pts AS val, games_played AS games
            FROM player_career_stats
            WHERE games_played >= 50
            ORDER BY val DESC LIMIT 10
        """),
        "Best FG% (min 500 attempts)": query("""
            SELECT player, team, FG_PCT AS val, FGA AS games
            FROM player_career_stats
            WHERE FGA >= 500
            ORDER BY val DESC LIMIT 10
        """),
        "Best 3P% (min 200 attempts)": query("""
            SELECT player, team, THREE_PCT AS val, TPA AS games
            FROM player_career_stats
            WHERE TPA >= 200
            ORDER BY val DESC LIMIT 10
        """),
        "Most Shots Attempted": query("""
            SELECT player, team, FGA AS val, games_played AS games
            FROM player_career_stats
            WHERE games_played >= 50
            ORDER BY val DESC LIMIT 10
        """),
    }
    return render_template("leaderboards.html", boards=boards)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
