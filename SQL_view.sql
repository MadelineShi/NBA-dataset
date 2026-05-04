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
    ROUND(SUM(s.made)/COUNT(*)*100,1) AS FG_PCT,

    SUM(CASE WHEN s.shot_type = '3' THEN 1 ELSE 0 END) AS TPA,
    SUM(CASE WHEN s.shot_type = '3' AND s.made = 1 THEN 1 ELSE 0 END) AS TPM,

    ROUND(
        SUM(CASE WHEN s.shot_type = '3' AND s.made = 1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN s.shot_type = '3' THEN 1 ELSE 0 END),0) * 100, 1
    ) AS THREE_PCT,

    SUM(
        CASE
            WHEN s.shot_type = '2' AND s.made = 1 THEN 2
            WHEN s.shot_type = '3' AND s.made = 1 THEN 3
            ELSE 0
        END
    ) AS total_pts,

    COUNT(DISTINCT s.game_id) AS games_played

FROM Shot s
JOIN Player p ON s.player_id = p.player_id

GROUP BY p.player_name, s.team_name;


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
    team_name,

    COUNT(*) AS FGA,
    SUM(CASE WHEN made = 1 THEN 1 ELSE 0 END) AS FGM,

    ROUND(
        SUM(CASE WHEN made = 1 THEN 1 ELSE 0 END) / COUNT(*),
        3
    ) AS FG_PCT,

    SUM(
        CASE
            WHEN shot_type = '3' AND made = 1 THEN 3
            WHEN made = 1 THEN 2
            ELSE 0
        END
    ) AS total_pts

FROM Shot

GROUP BY team_name;