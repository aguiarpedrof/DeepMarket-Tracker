-- =============================================================================
-- DeepMarket-Tracker — Star Schema para Power BI
-- Script: 01_schema.sql
-- Execução: psql -U <user> -d <banco> -f 01_schema.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DIMENSÃO: dim_data
-- Calendário completo — filtros de dia, semana, mês, ano, dia da semana no BI
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_data (
    id_data         SERIAL PRIMARY KEY,
    data            DATE NOT NULL UNIQUE,
    ano             INT  NOT NULL,
    mes             INT  NOT NULL,   -- 1-12
    dia             INT  NOT NULL,   -- 1-31
    semana_do_ano   INT  NOT NULL,   -- 1-53
    dia_semana      VARCHAR(15) NOT NULL,  -- 'Segunda', 'Terça', ...
    dia_semana_num  INT  NOT NULL,   -- 1=Domingo, 2=Segunda, ..., 7=Sábado (padrão ISO)
    fim_de_semana   BOOLEAN NOT NULL DEFAULT FALSE,
    nome_mes        VARCHAR(15) NOT NULL  -- 'Janeiro', 'Fevereiro', ...
);

-- -----------------------------------------------------------------------------
-- DIMENSÃO: dim_hora
-- Granularidade por hora — turnos e períodos para análise de pico
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_hora (
    id_hora     SERIAL PRIMARY KEY,
    hora        INT  NOT NULL UNIQUE,  -- 0-23
    periodo     VARCHAR(10) NOT NULL,  -- 'AM' / 'PM'
    turno       VARCHAR(10) NOT NULL   -- 'Manhã' (6-12) / 'Tarde' (12-18) / 'Noite' (18-23) / 'Madrugada' (0-5)
);

-- -----------------------------------------------------------------------------
-- FATO PRINCIPAL: fato_fluxo
-- Um registro por evento detectado (ENTRADA / SAIDA / PASSAGEM)
-- Granularidade: evento individual por pessoa rastreada
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fato_fluxo (
    id                  BIGSERIAL PRIMARY KEY,
    id_data             INT NOT NULL REFERENCES dim_data(id_data),
    id_hora             INT NOT NULL REFERENCES dim_hora(id_hora),
    track_id            INT NOT NULL,              -- ID do SORT tracker
    event_type          VARCHAR(20) NOT NULL       -- 'ENTRADA' | 'SAIDA' | 'PASSAGEM'
                        CHECK (event_type IN ('ENTRADA', 'SAIDA', 'PASSAGEM')),
    event_time          TIMESTAMP NOT NULL DEFAULT NOW(),
    confianca_deteccao  FLOAT,                     -- confiança do modelo YOLO (0.0–1.0)
    direction           VARCHAR(5)                 -- 'IN' | 'OUT' (compatível com tracker_events)
);

CREATE INDEX IF NOT EXISTS idx_fato_fluxo_data  ON fato_fluxo(id_data);
CREATE INDEX IF NOT EXISTS idx_fato_fluxo_hora  ON fato_fluxo(id_hora);
CREATE INDEX IF NOT EXISTS idx_fato_fluxo_tipo  ON fato_fluxo(event_type);
CREATE INDEX IF NOT EXISTS idx_fato_fluxo_time  ON fato_fluxo(event_time);

-- -----------------------------------------------------------------------------
-- FATO SESSÃO: fato_sessao
-- Um registro por visita completa (ENTRADA + SAIDA pareados por track_id)
-- Permite calcular tempo de permanência por pessoa
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fato_sessao (
    id_sessao               BIGSERIAL PRIMARY KEY,
    id_data                 INT NOT NULL REFERENCES dim_data(id_data),
    track_id                INT NOT NULL,
    entrada_time            TIMESTAMP NOT NULL,
    saida_time              TIMESTAMP,             -- NULL se pessoa nunca saiu no período
    tempo_permanencia_seg   INT,                   -- (saida_time - entrada_time) em segundos
    converteu               BOOLEAN NOT NULL DEFAULT TRUE  -- TRUE = entrou de fato no mercado
);

CREATE INDEX IF NOT EXISTS idx_fato_sessao_data    ON fato_sessao(id_data);
CREATE INDEX IF NOT EXISTS idx_fato_sessao_trackid ON fato_sessao(track_id);

-- -----------------------------------------------------------------------------
-- AGREGADO HORÁRIO: resumo_horario
-- KPIs pré-calculados por hora — ideal para Power BI (carga rápida)
-- Populado pelo script banco/populate_resumo.py
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resumo_horario (
    id                          BIGSERIAL PRIMARY KEY,
    id_data                     INT NOT NULL REFERENCES dim_data(id_data),
    id_hora                     INT NOT NULL REFERENCES dim_hora(id_hora),
    total_entradas              INT NOT NULL DEFAULT 0,
    total_saidas                INT NOT NULL DEFAULT 0,
    total_passantes             INT NOT NULL DEFAULT 0,
    taxa_conversao_pct          FLOAT,             -- (entradas / (entradas + passantes)) * 100
    tempo_medio_permanencia_min FLOAT,             -- média de fato_sessao em minutos
    lotacao_pico                INT NOT NULL DEFAULT 0,  -- max(entradas acumuladas - saidas acumuladas)
    UNIQUE (id_data, id_hora)
);

CREATE INDEX IF NOT EXISTS idx_resumo_data ON resumo_horario(id_data);
CREATE INDEX IF NOT EXISTS idx_resumo_hora ON resumo_horario(id_hora);

-- =============================================================================
-- NOTA: A tabela original "tracker_events" é MANTIDA intacta.
-- Os dados serão migrados via 03_migrate_data.sql.
-- =============================================================================
