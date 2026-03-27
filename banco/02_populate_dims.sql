-- =============================================================================
-- DeepMarket-Tracker — Popula Dimensões de Calendário e Hora
-- Script: 02_populate_dims.sql
-- Execução: psql -U <user> -d <banco> -f 02_populate_dims.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Popula dim_hora (0 a 23)
-- -----------------------------------------------------------------------------
INSERT INTO dim_hora (hora, periodo, turno)
SELECT
    h,
    CASE WHEN h < 12 THEN 'AM' ELSE 'PM' END AS periodo,
    CASE
        WHEN h BETWEEN 0  AND 5  THEN 'Madrugada'
        WHEN h BETWEEN 6  AND 11 THEN 'Manhã'
        WHEN h BETWEEN 12 AND 17 THEN 'Tarde'
        ELSE 'Noite'
    END AS turno
FROM generate_series(0, 23) AS h
ON CONFLICT (hora) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Popula dim_data: de 2 anos atrás até 2 anos à frente
-- -----------------------------------------------------------------------------
INSERT INTO dim_data (data, ano, mes, dia, semana_do_ano, dia_semana, dia_semana_num, fim_de_semana, nome_mes)
SELECT
    d::DATE                                                AS data,
    EXTRACT(YEAR  FROM d)::INT                             AS ano,
    EXTRACT(MONTH FROM d)::INT                             AS mes,
    EXTRACT(DAY   FROM d)::INT                             AS dia,
    EXTRACT(WEEK  FROM d)::INT                             AS semana_do_ano,
    TO_CHAR(d, 'TMDay')                                    AS dia_semana,        -- localizado
    EXTRACT(DOW FROM d)::INT + 1                           AS dia_semana_num,    -- 1=Dom, 7=Sáb
    EXTRACT(DOW FROM d) IN (0, 6)                          AS fim_de_semana,
    TO_CHAR(d, 'TMMonth')                                  AS nome_mes           -- localizado
FROM generate_series(
    (CURRENT_DATE - INTERVAL '2 years')::DATE,
    (CURRENT_DATE + INTERVAL '2 years')::DATE,
    INTERVAL '1 day'
) AS d
ON CONFLICT (data) DO NOTHING;

SELECT 'dim_hora populada com ' || COUNT(*) || ' registros.' AS status FROM dim_hora;
SELECT 'dim_data populada com ' || COUNT(*) || ' registros.' AS status FROM dim_data;
