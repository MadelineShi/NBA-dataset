-- HoopBase: NBA Shot Analytics Dashboard
-- CSC 353 — Database Systems, Davidson College Spring 2026
-- Built from per-game shot log CSVs (2000–present)

CREATE DATABASE IF NOT EXISTS hoopbase;
USE hoopbase;

-- ─────────────────────────────────────────
-- 1. Game  (one row per game_id)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Game (
    game_id        CHAR(16) PRIMARY KEY,     -- e.g. '202203130ATL'
    game_date      DATE,                     -- parsed from match_id
    season_year    INT,                      -- derived from date
    home_team      VARCHAR(3),               -- last 3 chars of match_id
    opponent_team  VARCHAR(3),				 -- read from "opp"
    FOREIGN KEY (home_team) REFERENCES Team(team_name),
	FOREIGN KEY (opponent_team) REFERENCES Team(team_name),
	INDEX idx_game_date (game_date),     	 --这三个是啥啊
    INDEX idx_game_team (home_team),	  	 --这三个是啥啊
    INDEX idx_game_year (season_year)	 	 --这三个是啥啊
);

-- ─────────────────────────────────────────
-- 2. Shot  (one row per shot attempt)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Shot (
    shot_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    shot_type      CHAR(1),          	    -- '2-pointer' or '3-pointer'
    made           BOOLEAN  NOT NULL,    	-- 1 = made, 0 = missed
    distance       FLOAT,                  	-- feet
    game_id        CHAR(16) NOT NULL,
    player_id      INT AUTO_INCREMENT NOT NULL,
    shotX          FLOAT,                	-- court x coordinate
    shotY          FLOAT,                	-- court y coordinate
    quarter        CHAR(4),
    time_remaining INT(2), 					-- minute
    status		   CHAR(6),         	    -- trails or leads or tied
    team_name      CHAR(3),
    FOREIGN KEY (game_id) REFERENCES Game(game_id)
        ON DELETE CASCADE,
	FOREIGN KEY (team_name) REFERENCES Team(team_name),
	FOREIGN KEY (playe_id) REFERENCES Player(player_id), 
    INDEX idx_shot_player (player_id),  	-- updated to player_id
    INDEX idx_shot_team   (team_name),
    INDEX idx_shot_game   (game_id)
);

-- ─────────────────────────────────────────
-- 3. Team 
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Team (
	team_name		   CHAR(3) PRIMARY KEY
);

-- ─────────────────────────────────────────
-- 4. Player 
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Player (
	player_id 		   INT AUTO_INCREMENT PRIMARY KEY,
	player_name		   VARCHAR(100) UNIQUE,
);

-- ─────────────────────────────────────────
-- 5. Player_team relationship  (one row per player-team-season)
-- ─────────────────────────────────────────

CREATE TABLE Player_belongs_to (
  player_id 		   INT AUTO_INCREMENT,
  team_name 	       CHAR(3),
  season_year 		   INT,

  PRIMARY KEY (player_id, team_name, season_year),
  FOREIGN KEY (player_id) REFERENCES Player(player_id),
  FOREIGN KEY (team_name) REFERENCES Team(team_name)
);
