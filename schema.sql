-- HoopBase: NBA Shot Analytics Dashboard
-- CSC 353 — Database Systems, Davidson College Spring 2026
-- Built from per-game shot log CSVs (2000–present)

CREATE DATABASE IF NOT EXISTS hoopbase;
USE hoopbase;

-- ─────────────────────────────────────────
-- 1. games  (one row per match_id)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS games (
    match_id    VARCHAR(20) PRIMARY KEY,  -- e.g. '202203130ATL'
    game_date   DATE,                     -- parsed from match_id
    home_team   VARCHAR(5),               -- last 3 chars of match_id
    season_year INT,                      -- derived from date
    INDEX idx_game_date (game_date),
    INDEX idx_game_team (home_team),
    INDEX idx_game_year (season_year)
);

-- ─────────────────────────────────────────
-- 2. shots  (one row per shot attempt)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shots (
    shot_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    match_id       VARCHAR(20) NOT NULL,
    player         VARCHAR(100) NOT NULL,
    team           VARCHAR(5)  NOT NULL,
    shot_type      VARCHAR(15),          -- '2-pointer' or '3-pointer'
    made           TINYINT(1)  NOT NULL, -- 1 = made, 0 = missed
    distance       INT,                  -- feet
    shotX          FLOAT,               -- court x coordinate
    shotY          FLOAT,               -- court y coordinate
    quarter        VARCHAR(20),
    time_remaining VARCHAR(15),
    FOREIGN KEY (match_id) REFERENCES games(match_id)
        ON DELETE CASCADE,
    INDEX idx_shot_player (player),
    INDEX idx_shot_team   (team),
    INDEX idx_shot_match  (match_id)
);
