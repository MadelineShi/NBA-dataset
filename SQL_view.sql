-- HoopBase — SQL Views (Index-Optimized)
-- CSC 353, Davidson College, Spring 2026
--
-- NOTE: Before running this on a fresh machine, first run in Workbench:
--   ALTER TABLE Shot ADD INDEX idx_shot_player_covering (player_id, team_name, shot_type, made, game_id);
--   ALTER TABLE Shot ADD INDEX idx_shot_team_covering (team_name, shot_type, made, game_id);

USE hoopbase2;

-- ─────────────────────────────────────────
-- Player Career Stats View
-- One row per (player_name, team_name)
-- Uses idx_shot_player_covering on Shot + Player primary key
-- ─────────────────────────────────────────

CREATE OR REPLACE VIEW player_career_stats AS
SELECT
    p.player_name,
    s.team_name,

    COUNT(*) AS FGA,
    SUM(s.made) AS FGM,
    ROUND(SUM(s.made) / COUNT(*) * 100, 1) AS FG_PCT,

    SUM(CASE WHEN s.shot_type = '3' THEN 1 ELSE 0 END) AS TPA,
    SUM(CASE WHEN s.shot_type = '3' AND s.made = 1 THEN 1 ELSE 0 END) AS TPM,

    ROUND(
        SUM(CASE WHEN s.shot_type = '3' AND s.made = 1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN s.shot_type = '3' THEN 1 ELSE 0 END), 0) * 100,
    1) AS THREE_PCT,

    SUM(CASE
        WHEN s.shot_type = '2' AND s.made = 1 THEN 2
        WHEN s.shot_type = '3' AND s.made = 1 THEN 3
        ELSE 0
    END) AS total_pts,

    COUNT(DISTINCT s.game_id) AS games_played

FROM Shot s
JOIN Player p ON p.player_id = s.player_id
GROUP BY s.player_id, s.team_name, p.player_name;


-- ─────────────────────────────────────────
-- Team Career Stats View
-- One row per team_name
-- Uses idx_shot_team_covering on Shot
-- ─────────────────────────────────────────

CREATE OR REPLACE VIEW team_career_stats AS
SELECT
    s.team_name,

    COUNT(*) AS FGA,
    SUM(s.made) AS FGM,
    ROUND(SUM(s.made) / COUNT(*) * 100, 1) AS FG_PCT,

    SUM(CASE
        WHEN s.shot_type = '3' AND s.made = 1 THEN 3
        WHEN s.made = 1 THEN 2
        ELSE 0
    END) AS total_pts

FROM Shot s
GROUP BY s.team_name;
