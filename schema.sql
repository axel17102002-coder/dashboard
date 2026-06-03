-- SCHEMA.SQL: Estructura unificada para BasketStats Analytics

-- 1. Tabla de cabeceras de partidos (Filtra por competition: 'EuroLeague' o 'EuroCup')
CREATE TABLE IF NOT EXISTS game_headers (
    game_id VARCHAR(100) PRIMARY KEY,
    season_code VARCHAR(50),
    phase VARCHAR(100),
    round INT,
    team_id_a VARCHAR(100),
    team_id_b VARCHAR(100),
    score_a INT,
    score_b INT,
    stadium VARCHAR(255),
    capacity INT,
    competition VARCHAR(50), -- Identifica la liga
    score_quarter_1_a INT,
    score_quarter_2_a INT,
    score_quarter_3_a INT,
    score_quarter_1_b INT,
    score_quarter_2_b INT,
    score_quarter_3_b INT
);

-- 2. Tabla de estadísticas de jugadores por temporada
CREATE TABLE IF NOT EXISTS season_players (
    season_player_id VARCHAR(255) PRIMARY KEY,
    player_id VARCHAR(100),
    player VARCHAR(255),
    team_id VARCHAR(100),
    season_code VARCHAR(50),
    games_played INT,
    perfil_ofensivo VARCHAR(100),
    turnovers INT,
    ast_to_ratio DECIMAL(5,2),
    points_per_game DECIMAL(5,2),
    assists_per_game DECIMAL(5,2),
    efg_pct DECIMAL(5,2),
    ts_pct DECIMAL(5,2),
    offensive_rebounds_per_game DECIMAL(5,2),
    usg_pct DECIMAL(5,2),
    competition VARCHAR(50)
);

-- 3. Tabla de estadísticas por partido (Box Scores)
CREATE TABLE IF NOT EXISTS game_box_scores (
    game_player_id VARCHAR(255) PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES game_headers(game_id),
    player VARCHAR(255),
    team_id VARCHAR(100),
    season_code VARCHAR(50),
    phase VARCHAR(100),
    round INT,
    points INT,
    assists INT,
    two_points_attempted INT,
    three_points_attempted INT,
    two_points_made INT,
    three_points_made INT,
    free_throws_attempted INT,
    pir_calculado INT,
    offensive_rebounds INT,
    defensive_rebounds INT,
    steals INT,
    blocks_favour INT,
    plus_minus INT,
    competition VARCHAR(50)
);

-- 4. Tabla de estadísticas de equipos por temporada
CREATE TABLE IF NOT EXISTS season_teams (
    season_team_id VARCHAR(255) PRIMARY KEY,
    team_id VARCHAR(100),
    season_code VARCHAR(50),
    valuation_per_game DECIMAL(5,2),
    competition VARCHAR(50)
);

-- 5. Tabla de puntos y tiros detallados para el mapa de calor
CREATE TABLE IF NOT EXISTS game_points (
    game_point_id VARCHAR(255) PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES game_headers(game_id) ON DELETE CASCADE,
    player VARCHAR(255),
    season_code VARCHAR(50),
    action_id VARCHAR(50),
    zone VARCHAR(100),
    coord_x FLOAT,
    coord_y FLOAT,
    competition VARCHAR(50)
);