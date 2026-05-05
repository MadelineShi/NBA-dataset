-- HoopBase — SQL Views 
-- CSC 353, Davidson College, Spring 2026

-- ─────────────────────────────────────────
-- Player Career Stats View
-- One row per (player_id, team_name)
--
-- Computes:
--   - FGM / FGA / FG%
--   - 3PT stats (TPM / TPA / 3P%)
--   - Total points
--   - Games played (proxy: number of shots)
-- ─────────────────────────────────────────
USE hoopbase2;

CREATE OR REPLACE VIEW player_career_stats AS
SELECT
    p.player_name,
    s.team_name,

    COUNT(*) AS FGA,
    SUM(s.made) AS FGM,
    ROUND(SUM(s.made) / NULLIF(COUNT(*), 0) * 100, 1) AS FG_PCT,

    SUM(CASE WHEN s.shot_type = '3' THEN 1 ELSE 0 END) AS TPA,
    SUM(CASE WHEN s.shot_type = '3' AND s.made = 1 THEN 1 ELSE 0 END) AS TPM,

    ROUND(
        SUM(CASE WHEN s.shot_type = '3' AND s.made = 1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN s.shot_type = '3' THEN 1 ELSE 0 END), 0)
        * 100, 1
    ) AS THREE_PCT,

    SUM(
        CASE
            WHEN s.shot_type = '3' AND s.made = 1 THEN 3
            WHEN s.shot_type = '2' AND s.made = 1 THEN 2
            ELSE 0
        END
    ) AS total_pts,

    COUNT(DISTINCT s.game_id) AS games_played

FROM Shot s FORCE INDEX (idx_shot_player)
JOIN Player p ON s.player_id = p.player_id
GROUP BY s.player_id, p.player_name, s.team_name;




-- ─────────────────────────────────────────
-- Team Stats View
-- One row per team_name
--
-- Computes:
--   - FGM / FGA / FG%
--   - Total points
-- ─────────────────────────────────────────

CREATE OR REPLACE VIEW team_career_stats AS
SELECT
    s.team_name,

    COUNT(*) AS FGA,
    SUM(CASE WHEN s.made = 1 THEN 1 ELSE 0 END) AS FGM,

    ROUND(
        SUM(CASE WHEN s.made = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0)
        * 100, 1
    ) AS FG_PCT,

    SUM(
        CASE
            WHEN s.shot_type = '3' AND s.made = 1 THEN 3
            WHEN s.shot_type = '2' AND s.made = 1 THEN 2
            ELSE 0
        END
    ) AS total_pts,

    COUNT(DISTINCT s.game_id) AS games

FROM Shot s FORCE INDEX (idx_shot_team)
GROUP BY s.team_name;




