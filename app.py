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

from flask import Flask, render_template, request, jsonify, abort
import mysql.connector

app = Flask(__name__)

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "gha$bbhisA23rtyuiop0999",
    "database": "hoopbase2",
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
# Used only when a year filter is applied (views are career-only)

PLAYER_STATS_SQL = """
    SELECT
        p.player_name,
        s.team_name,
        COUNT(*) AS FGA,
        SUM(s.made) AS FGM,
        ROUND(SUM(s.made) / COUNT(*) * 100, 1) AS FG_PCT,
        SUM(CASE WHEN s.shot_type='3' THEN 1 ELSE 0 END) AS TPA,
        SUM(CASE WHEN s.shot_type='3' AND s.made=1 THEN 1 ELSE 0 END) AS TPM,
        ROUND(
            SUM(CASE WHEN s.shot_type='3' AND s.made=1 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN s.shot_type='3' THEN 1 ELSE 0 END), 0)
            * 100, 1) AS THREE_PCT,
        SUM(CASE
            WHEN s.shot_type='2' AND s.made=1 THEN 2
            WHEN s.shot_type='3' AND s.made=1 THEN 3
            ELSE 0 END) AS total_pts,
        COUNT(DISTINCT s.game_id) AS games_played
    FROM Shot s
    JOIN Player p ON s.player_id = p.player_id
    {join}
    WHERE {where}
    GROUP BY p.player_name, s.team_name
"""

def player_stats_query(name_filter=None, team_filter=None, year_filter=None,
                       sort="total_pts", limit=200):
    """Used only when year_filter is set — otherwise we use the view."""
    join = "JOIN Game g ON g.game_id = s.game_id" if year_filter else ""

    wheres = ["1=1"]
    params = []

    if name_filter:
        wheres.append("p.player_name LIKE %s")
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

    # Year-filtered top scorers — view is career-only so raw query needed here
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
        # ── use the view for career search ──
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
            SELECT player_name, team_name, total_pts, FGA, FGM, FG_PCT,
                   TPA, TPM, THREE_PCT, games_played
            FROM player_career_stats
            WHERE {where}
            ORDER BY {sort} DESC LIMIT 200
        """, params)

    else:
        # Year filter requires hitting Shot directly
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

    # Per-season breakdown — needs raw query (view has no season column)
    career = query("""
        SELECT g.season_year,
               s.team_name,
               COUNT(*) AS FGA,
               SUM(s.made) AS FGM,
               ROUND(SUM(s.made)/COUNT(*)*100,1) AS FG_PCT,
               SUM(CASE WHEN s.shot_type='3' THEN 1 ELSE 0 END) AS TPA,
               SUM(CASE WHEN s.shot_type='3' AND s.made=1 THEN 1 ELSE 0 END) AS TPM,
               ROUND(
                 SUM(CASE WHEN s.shot_type='3' AND s.made=1 THEN 1 ELSE 0 END)
                 / NULLIF(SUM(CASE WHEN s.shot_type='3' THEN 1 ELSE 0 END),0)
                 *100,1) AS THREE_PCT,
               SUM(CASE
                    WHEN s.shot_type='2' AND s.made=1 THEN 2
                    WHEN s.shot_type='3' AND s.made=1 THEN 3
                    ELSE 0 END) AS total_pts,
               COUNT(DISTINCT s.game_id) AS games_played
        FROM Shot s
        JOIN Player p ON s.player_id = p.player_id
        JOIN Game g ON g.game_id = s.game_id
        WHERE p.player_name = %s
        GROUP BY g.season_year, s.team_name
        ORDER BY g.season_year
    """, (player_name,))

    if not career:
        abort(404)

    # Career totals — use the view
    totals = query("""
        SELECT total_pts, FGA, FGM, FG_PCT, TPA, TPM, THREE_PCT, games_played
        FROM player_career_stats
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
    # Raw Shot query needed — coordinates aren't in any view
    year = request.args.get("year", "").strip()

    if year:
        rows = query("""
            SELECT s.shotX, s.shotY, s.made, s.shot_type, s.distance
            FROM Shot s
            JOIN Player p ON s.player_id = p.player_id
            JOIN Game g ON g.game_id = s.game_id
            WHERE p.player_name = %s AND g.season_year = %s
        """, (player_name, int(year)))
    else:
        rows = query("""
            SELECT s.shotX, s.shotY, s.made, s.shot_type, s.distance
            FROM Shot s
            JOIN Player p ON s.player_id = p.player_id
            WHERE p.player_name = %s
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
            # Use the view — much faster than aggregating Shot
            return query("""
                SELECT total_pts, FGA, FGM, FG_PCT, TPA, TPM, THREE_PCT, games_played
                FROM player_career_stats
                WHERE player_name = %s
            """, (name,), one=True)

        p1_stats = get_totals(p1_name)
        p2_stats = get_totals(p2_name)

    all_players = query("SELECT DISTINCT player_name FROM Player ORDER BY player_name LIMIT 10000")

    return render_template("compare.html",
                           p1_name=p1_name,
                           p2_name=p2_name,
                           p1_stats=p1_stats,
                           p2_stats=p2_stats,
                           all_players=all_players)


# ── Teams ─────────────────────────────────────────

@app.route("/teams")
def teams():
    # Use the view
    rows = query("SELECT * FROM team_career_stats ORDER BY total_pts DESC")
    return render_template("teams.html", teams=rows)


# ── Team Detail ────────────────────────────────────

@app.route("/team/<abbrev>")
def team_detail(abbrev):
    year = request.args.get("year", "").strip()

    # Season-by-season breakdown — needs raw query (view has no season column)
    seasons = query("""
        SELECT g.season_year,
               COUNT(*) AS FGA,
               SUM(s.made) AS FGM,
               ROUND(SUM(s.made)/COUNT(*)*100,1) AS FG_PCT,
               SUM(CASE
                    WHEN s.shot_type='2' AND s.made=1 THEN 2
                    WHEN s.shot_type='3' AND s.made=1 THEN 3
                    ELSE 0 END) AS total_pts,
               COUNT(DISTINCT s.game_id) AS games
        FROM Shot s
        JOIN Game g ON s.game_id = g.game_id
        WHERE s.team_name = %s
        GROUP BY g.season_year
        ORDER BY g.season_year DESC
    """, (abbrev.upper(),))

    if not seasons:
        abort(404)

    if year:
        # Year-filtered top players — needs raw query
        top_players = query("""
            SELECT p.player_name,
                   COUNT(*) AS FGA,
                   SUM(s.made) AS FGM,
                   ROUND(SUM(s.made)/COUNT(*)*100,1) AS FG_PCT,
                   SUM(CASE
                        WHEN s.shot_type='2' AND s.made=1 THEN 2
                        WHEN s.shot_type='3' AND s.made=1 THEN 3
                        ELSE 0 END) AS total_pts,
                   COUNT(DISTINCT s.game_id) AS games_played
            FROM Shot s
            JOIN Player p ON s.player_id = p.player_id
            JOIN Game g ON s.game_id = g.game_id
            WHERE s.team_name = %s AND g.season_year = %s
            GROUP BY p.player_name
            HAVING games_played >= 5
            ORDER BY total_pts DESC
            LIMIT 15
        """, (abbrev.upper(), int(year)))
    else:
        # Career top players for this team — use the view
        top_players = query("""
            SELECT player_name, total_pts, FGA, FGM, FG_PCT, games_played
            FROM player_career_stats
            WHERE team_name = %s AND games_played >= 5
            ORDER BY total_pts DESC
            LIMIT 15
        """, (abbrev.upper(),))

    years = query("""
        SELECT DISTINCT g.season_year
        FROM Game g
        JOIN Shot s ON s.game_id = g.game_id
        WHERE s.team_name = %s AND g.season_year IS NOT NULL
        ORDER BY g.season_year DESC
    """, (abbrev.upper(),))

    return render_template("team.html",
                           abbrev=abbrev.upper(),
                           seasons=seasons,
                           top_players=top_players,
                           years=years,
                           selected_year=year)


# ── Leaderboards ───────────────────────────────────

@app.route("/leaderboards")
def leaderboards():
    # We use 'AS val' to make every query return a column with the same name[cite: 1]
    top_pts = query("SELECT player_name, total_pts AS val FROM player_career_stats ORDER BY total_pts DESC LIMIT 10")
    top_fg = query("SELECT player_name, FG_PCT AS val FROM player_career_stats WHERE FGA >= 500 ORDER BY FG_PCT DESC LIMIT 10")
    top_3p = query("SELECT player_name, THREE_PCT AS val FROM player_career_stats WHERE TPA >= 200 ORDER BY THREE_PCT DESC LIMIT 10")
    top_volume = query("SELECT player_name, FGA AS val FROM player_career_stats ORDER BY FGA DESC LIMIT 10")

    boards = {
        "Total Points": top_pts,
        "Field Goal %": top_fg,
        "Three Point %": top_3p,
        "Field Goal Attempts": top_volume
    }

    context = {
        "boards": boards,
        "active_page": "leaderboards"
    }

    return render_template("leaderboards.html", **context)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
