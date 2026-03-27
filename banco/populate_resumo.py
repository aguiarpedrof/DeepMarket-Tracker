r"""
DeepMarket-Tracker — Agregador Horário
Arquivo: banco/populate_resumo.py

Agrupa os dados de fato_fluxo e fato_sessao na tabela resumo_horario.
Executar manualmente ou agendar (Windows Task Scheduler / cron).

Exemplo de agendamento no Windows (Task Scheduler):
  Ação: python C:\Users\pedro\Desktop\projetoIAmercadinho\banco\populate_resumo.py
  Gatilho: A cada 1 hora

"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
import datetime

# Adiciona o diretório pai ao path para achar o .env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def conectar():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )

QUERY_RESUMO = """
INSERT INTO resumo_horario (
    id_data, id_hora,
    total_entradas, total_saidas, total_passantes,
    taxa_conversao_pct, tempo_medio_permanencia_min, lotacao_pico
)
SELECT
    f.id_data,
    f.id_hora,

    -- Contagens por tipo de evento
    SUM(CASE WHEN f.event_type = 'ENTRADA'  THEN 1 ELSE 0 END) AS total_entradas,
    SUM(CASE WHEN f.event_type = 'SAIDA'    THEN 1 ELSE 0 END) AS total_saidas,
    SUM(CASE WHEN f.event_type = 'PASSAGEM' THEN 1 ELSE 0 END) AS total_passantes,

    -- Taxa de conversão: entradas / (entradas + passantes) * 100
    CASE
        WHEN SUM(CASE WHEN f.event_type IN ('ENTRADA', 'PASSAGEM') THEN 1 ELSE 0 END) = 0 THEN NULL
        ELSE ROUND(
            100.0 * SUM(CASE WHEN f.event_type = 'ENTRADA' THEN 1 ELSE 0 END)
            / SUM(CASE WHEN f.event_type IN ('ENTRADA', 'PASSAGEM') THEN 1 ELSE 0 END),
            2
        )
    END AS taxa_conversao_pct,

    -- Tempo médio de permanência (em minutos) das sessões que começaram nessa hora
    (
        SELECT ROUND(AVG(tempo_permanencia_seg) / 60.0, 2)
        FROM fato_sessao fs2
        WHERE fs2.id_data = f.id_data
          AND EXTRACT(HOUR FROM fs2.entrada_time)::INT = (SELECT hora FROM dim_hora dh WHERE dh.id_hora = f.id_hora)
          AND fs2.tempo_permanencia_seg IS NOT NULL
    ) AS tempo_medio_permanencia_min,

    -- Lotação pico: max(entradas acumuladas - saidas acumuladas) na hora
    (
        SELECT COALESCE(MAX(
            (SELECT COUNT(*) FROM fato_fluxo ff2 
             WHERE ff2.id_data = f.id_data AND ff2.event_type = 'ENTRADA'
               AND ff2.event_time <= ff3.event_time)
            - 
            (SELECT COUNT(*) FROM fato_fluxo ff4 
             WHERE ff4.id_data = f.id_data AND ff4.event_type = 'SAIDA'
               AND ff4.event_time <= ff3.event_time)
        ), 0)
        FROM fato_fluxo ff3
        WHERE ff3.id_data = f.id_data AND ff3.id_hora = f.id_hora
    ) AS lotacao_pico

FROM fato_fluxo f
WHERE f.id_data IN (
    SELECT id_data FROM dim_data WHERE data = %s
)
GROUP BY f.id_data, f.id_hora

ON CONFLICT (id_data, id_hora) DO UPDATE SET
    total_entradas              = EXCLUDED.total_entradas,
    total_saidas                = EXCLUDED.total_saidas,
    total_passantes             = EXCLUDED.total_passantes,
    taxa_conversao_pct          = EXCLUDED.taxa_conversao_pct,
    tempo_medio_permanencia_min = EXCLUDED.tempo_medio_permanencia_min,
    lotacao_pico                = EXCLUDED.lotacao_pico;
"""

def agregar_dia(data: datetime.date):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(QUERY_RESUMO, (data,))
        conn.commit()
        print(f"✅ resumo_horario atualizado para {data} ({cur.rowcount} linhas afetadas)")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao agregar: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Por padrão agrega o dia de hoje; passe uma data no formato YYYY-MM-DD como argumento
    if len(sys.argv) > 1:
        data_alvo = datetime.date.fromisoformat(sys.argv[1])
    else:
        data_alvo = datetime.date.today()

    print(f"▶ Agregando dados de {data_alvo}...")
    agregar_dia(data_alvo)
