-- =============================================================================
-- DeepMarket-Tracker — Queries prontas para Power BI
-- Arquivo: banco/04_powerbi_queries.sql
-- Cole cada query como "Consulta Nativa" no Power BI (PostgreSQL connector)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 1: Fluxo por Hora (granularidade horária)
-- Tabela no Power BI: "Fluxo Horário"
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    d.data,
    d.dia_semana,
    d.fim_de_semana,
    d.nome_mes,
    d.ano,
    d.mes,
    h.hora,
    h.turno,
    h.periodo,
    COALESCE(r.total_entradas,              0)    AS entradas,
    COALESCE(r.total_saidas,                0)    AS saidas,
    COALESCE(r.total_passantes,             0)    AS passantes,
    COALESCE(r.taxa_conversao_pct,          0)    AS taxa_conversao_pct,
    COALESCE(r.tempo_medio_permanencia_min, 0)    AS permanencia_media_min,
    COALESCE(r.lotacao_pico,                0)    AS lotacao_pico
FROM dim_data d
CROSS JOIN dim_hora h
LEFT JOIN resumo_horario r
    ON r.id_data = d.id_data
   AND r.id_hora = h.id_hora
WHERE d.data <= CURRENT_DATE
ORDER BY d.data, h.hora;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 2: Resumo Diário
-- Tabela no Power BI: "Resumo Diário"
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    d.data,
    d.dia_semana,
    d.nome_mes,
    d.ano,
    d.mes,
    d.semana_do_ano,
    d.fim_de_semana,
    COALESCE(SUM(r.total_entradas),              0) AS entradas_total,
    COALESCE(SUM(r.total_saidas),                0) AS saidas_total,
    COALESCE(SUM(r.total_passantes),             0) AS passantes_total,
    COALESCE(AVG(r.taxa_conversao_pct),          0) AS conversao_media_pct,
    COALESCE(AVG(r.tempo_medio_permanencia_min), 0) AS permanencia_media_min,
    COALESCE(MAX(r.lotacao_pico),                0) AS lotacao_pico_dia
FROM dim_data d
LEFT JOIN resumo_horario r ON r.id_data = d.id_data
WHERE d.data <= CURRENT_DATE
GROUP BY d.data, d.dia_semana, d.nome_mes, d.ano, d.mes, d.semana_do_ano, d.fim_de_semana
ORDER BY d.data;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 3: Sessões Individuais (tempo de permanência + conversão por pessoa)
-- Tabela no Power BI: "Sessões"
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    s.id_sessao,
    d.data,
    d.dia_semana,
    d.nome_mes,
    s.track_id,
    s.entrada_time,
    s.saida_time,
    s.tempo_permanencia_seg,
    ROUND(s.tempo_permanencia_seg / 60.0, 2) AS tempo_permanencia_min,
    s.converteu,
    CASE
        WHEN s.tempo_permanencia_seg IS NULL     THEN 'Sem registro de saida'
        WHEN s.tempo_permanencia_seg < 120       THEN 'Rapida (< 2 min)'
        WHEN s.tempo_permanencia_seg < 600       THEN 'Normal (2-10 min)'
        WHEN s.tempo_permanencia_seg < 1800      THEN 'Longa (10-30 min)'
        ELSE 'Muito longa (> 30 min)'
    END AS perfil_visita
FROM fato_sessao s
JOIN dim_data d ON s.id_data = d.id_data
ORDER BY s.entrada_time DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 4: Eventos Brutos (drill-down detalhado)
-- Tabela no Power BI: "Eventos"
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    f.id,
    d.data,
    h.hora,
    h.turno,
    f.track_id,
    f.event_type,
    f.event_time,
    f.confianca_deteccao,
    f.direction
FROM fato_fluxo f
JOIN dim_data d ON f.id_data = d.id_data
JOIN dim_hora h ON f.id_hora = h.id_hora
ORDER BY f.event_time DESC;
