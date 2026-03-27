-- =============================================================================
-- DeepMarket-Tracker — Migração de Dados: tracker_events → fato_fluxo
-- Script: 03_migrate_data.sql
-- Execução: psql -U <user> -d <banco> -f 03_migrate_data.sql
-- =============================================================================

-- Migra todos os eventos existentes de tracker_events para fato_fluxo,
-- fazendo o JOIN com dim_data e dim_hora pelas chaves calculadas.

INSERT INTO fato_fluxo (id_data, id_hora, track_id, event_type, event_time, direction, confianca_deteccao)
SELECT
    d.id_data,
    h.id_hora,
    te.track_id,
    te.event_type,
    te.event_time,
    te.direction,
    NULL AS confianca_deteccao   -- dados antigos não têm confiança
FROM tracker_events te
JOIN dim_data d ON d.data = DATE(te.event_time)
JOIN dim_hora h ON h.hora = EXTRACT(HOUR FROM te.event_time)::INT
ON CONFLICT DO NOTHING;

-- Monta as sessões a partir dos pares ENTRADA/SAIDA migrados
INSERT INTO fato_sessao (id_data, track_id, entrada_time, saida_time, tempo_permanencia_seg, converteu)
SELECT
    d.id_data,
    e.track_id,
    e.event_time AS entrada_time,
    s.event_time AS saida_time,
    EXTRACT(EPOCH FROM (s.event_time - e.event_time))::INT AS tempo_permanencia_seg,
    TRUE AS converteu
FROM tracker_events e
LEFT JOIN tracker_events s
    ON e.track_id = s.track_id
   AND s.event_type = 'SAIDA'
   AND s.event_time > e.event_time
JOIN dim_data d ON d.data = DATE(e.event_time)
WHERE e.event_type = 'ENTRADA';

SELECT 'Migração concluída.' AS status;
SELECT 'fato_fluxo: ' || COUNT(*) || ' registros.' AS status FROM fato_fluxo;
SELECT 'fato_sessao: ' || COUNT(*) || ' registros.' AS status FROM fato_sessao;
