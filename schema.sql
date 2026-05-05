CREATE DATABASE IF NOT EXISTS hoopbase2;
USE hoopbase2;

-- 1. Team (no dependencies)
CREATE TABLE IF NOT EXISTS Team (
    team_name CHAR(3) PRIMARY KEY
);

-- 2. Player (no dependencies)
CREATE TABLE IF NOT EXISTS Player (
    player_id   INT AUTO_INCREMENT PRIMARY KEY,
    player_name VARCHAR(100) UNIQUE
);

-- 3. Game (references Team)
CREATE TABLE IF NOT EXISTS Game (
    game_id       CHAR(16) PRIMARY KEY,
    game_date     DATE,
    season_year   INT,
    home_team     VARCHAR(3),
    opponent_team VARCHAR(3),
    FOREIGN KEY (home_team)     REFERENCES Team(team_name),
    FOREIGN KEY (opponent_team) REFERENCES Team(team_name),
    INDEX idx_game_date (game_date),
    INDEX idx_game_team (home_team),
    INDEX idx_game_year (season_year)
);

-- 4. Shot (references Game, Team, Player)
CREATE TABLE IF NOT EXISTS Shot (
    shot_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    shot_type      CHAR(1),
    made           BOOLEAN NOT NULL,
    distance       FLOAT,
    game_id        CHAR(16) NOT NULL,
    player_id      INT NOT NULL,
    shotX          FLOAT,
    shotY          FLOAT,
    quarter        CHAR(4),
    time_remaining INT,
    team_name      CHAR(3),
    FOREIGN KEY (game_id)   REFERENCES Game(game_id)   ON DELETE CASCADE,
    FOREIGN KEY (team_name) REFERENCES Team(team_name),
    FOREIGN KEY (player_id) REFERENCES Player(player_id),
    INDEX idx_shot_player (player_id),
    INDEX idx_shot_team   (team_name),
    INDEX idx_shot_game   (game_id),
    INDEX idx_shot_player_covering (player_id, team_name, shot_type, made, game_id),
    INDEX idx_shot_team_covering   (team_name, shot_type, made, game_id)
);

-- 5. Player_belongs_to (references Player, Team)
CREATE TABLE IF NOT EXISTS Player_belongs_to (
    player_id   INT,
    team_name   CHAR(3),
    season_year INT,
    PRIMARY KEY (player_id, team_name, season_year),
    FOREIGN KEY (player_id) REFERENCES Player(player_id),
    FOREIGN KEY (team_name) REFERENCES Team(team_name)
);