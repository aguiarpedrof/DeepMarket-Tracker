import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="DeepMarket Analytics", layout="wide")

st.title("Dashboard de Inteligência - DeepMarket")
st.markdown("Monitoramento de fluxo, conversão e tempo de permanência de clientes.")

@st.cache_resource
def conectar_banco():
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres")
    )

try:
    conn = conectar_banco()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}")
    st.stop()

def executar_query(query, params=None):
    return pd.read_sql(query, conn, params=params)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# PARTE 1: MÉTRICAS DE HOJE (CARDS)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📊 Métricas de Hoje")

df_totais = executar_query("""
    SELECT f.event_type, COUNT(*) as total
    FROM fato_fluxo f
    JOIN dim_data d ON f.id_data = d.id_data
    WHERE d.data = CURRENT_DATE
      AND f.event_type IN ('ENTRADA', 'SAIDA', 'PASSAGEM')
    GROUP BY f.event_type;
""")

entradas  = int(df_totais[df_totais['event_type'] == 'ENTRADA']['total'].sum())  if not df_totais.empty else 0
saidas    = int(df_totais[df_totais['event_type'] == 'SAIDA']['total'].sum())    if not df_totais.empty else 0
passantes = int(df_totais[df_totais['event_type'] == 'PASSAGEM']['total'].sum()) if not df_totais.empty else 0
lotacao   = max(0, entradas - saidas)

df_tempo = executar_query("""
    SELECT ROUND(AVG(tempo_permanencia_seg) / 60.0, 1) AS tempo_medio
    FROM fato_sessao s
    JOIN dim_data d ON s.id_data = d.id_data
    WHERE d.data = CURRENT_DATE
      AND s.tempo_permanencia_seg IS NOT NULL;
""")
tempo_medio = float(df_tempo['tempo_medio'].iloc[0]) if pd.notnull(df_tempo['tempo_medio'].iloc[0]) else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("🚶 Entradas Hoje",      entradas)
col2.metric("👥 Lotação Atual",      lotacao)
col3.metric("👀 Passantes (Vitrine)", passantes)
col4.metric("⏱️ Tempo Médio",        f"{tempo_medio:.1f} min")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# PARTE 2: FLUXO POR HORA (HOJE)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📈 Fluxo por Hora — Hoje")

df_hora = executar_query("""
    SELECT
        h.hora,
        COALESCE(r.total_entradas, 0)  AS entradas,
        COALESCE(r.total_passantes, 0) AS passantes
    FROM dim_hora h
    LEFT JOIN resumo_horario r
        ON r.id_hora = h.id_hora
       AND r.id_data = (SELECT id_data FROM dim_data WHERE data = CURRENT_DATE)
    ORDER BY h.hora;
""")

if df_hora['entradas'].sum() > 0 or df_hora['passantes'].sum() > 0:
    fig = px.line(df_hora, x="hora", y=["entradas", "passantes"],
                  labels={"value": "Pessoas", "hora": "Hora do Dia", "variable": "Tipo"},
                  title="Entradas vs Passantes por Hora",
                  markers=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado registrado hoje. Ative a câmera no main.py!")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# PARTE 3: TENDÊNCIA DIÁRIA (ÚLTIMOS 30 DIAS)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📅 Tendência Diária — Últimos 30 Dias")

df_diario = executar_query("""
    SELECT
        d.data,
        d.dia_semana,
        COALESCE(SUM(r.total_entradas),  0) AS entradas,
        COALESCE(SUM(r.total_passantes), 0) AS passantes,
        COALESCE(AVG(r.taxa_conversao_pct), 0) AS conversao
    FROM dim_data d
    LEFT JOIN resumo_horario r ON r.id_data = d.id_data
    WHERE d.data BETWEEN CURRENT_DATE - INTERVAL '30 days' AND CURRENT_DATE
    GROUP BY d.data, d.dia_semana
    ORDER BY d.data;
""")

if not df_diario.empty and df_diario['entradas'].sum() > 0:
    fig2 = px.bar(df_diario, x="data", y="entradas",
                  color="dia_semana",
                  title="Entradas por Dia (30 dias)",
                  labels={"data": "Data", "entradas": "Entradas", "dia_semana": "Dia"})
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Sem dados históricos ainda para o período.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# PARTE 4: TENDÊNCIA MENSAL
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📆 Tendência Mensal")

df_mensal = executar_query("""
    SELECT
        d.ano,
        d.mes,
        d.nome_mes,
        COALESCE(SUM(r.total_entradas),  0) AS entradas,
        COALESCE(SUM(r.total_passantes), 0) AS passantes,
        COALESCE(AVG(r.taxa_conversao_pct), 0) AS conversao_media
    FROM dim_data d
    LEFT JOIN resumo_horario r ON r.id_data = d.id_data
    WHERE d.data <= CURRENT_DATE
    GROUP BY d.ano, d.mes, d.nome_mes
    ORDER BY d.ano, d.mes;
""")

if not df_mensal.empty and df_mensal['entradas'].sum() > 0:
    df_mensal['periodo'] = df_mensal['nome_mes'] + '/' + df_mensal['ano'].astype(str)
    fig3 = px.line(df_mensal, x="periodo", y=["entradas", "passantes"],
                   title="Entradas e Passantes por Mês",
                   markers=True,
                   labels={"value": "Total", "periodo": "Mês", "variable": "Tipo"})
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Dados mensais aparecerão após algumas semanas de operação.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# PARTE 5: ANÁLISE DE PICO POR TURNO
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🌅 Análise por Turno (Manhã / Tarde / Noite)")

df_turno = executar_query("""
    SELECT
        h.turno,
        COALESCE(SUM(r.total_entradas), 0)  AS entradas,
        COALESCE(SUM(r.total_passantes), 0) AS passantes,
        COALESCE(AVG(r.taxa_conversao_pct), 0) AS conversao_media,
        COALESCE(AVG(r.tempo_medio_permanencia_min), 0) AS permanencia_media
    FROM dim_hora h
    LEFT JOIN resumo_horario r ON r.id_hora = h.id_hora
    JOIN dim_data d ON r.id_data = d.id_data AND d.data = CURRENT_DATE
    GROUP BY h.turno
    ORDER BY MIN(h.hora);
""")

if not df_turno.empty and df_turno['entradas'].sum() > 0:
    fig4 = px.bar(df_turno, x="turno", y="entradas", color="turno",
                  title="Entradas por Turno — Hoje",
                  labels={"turno": "Turno", "entradas": "Entradas"})
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# PARTE 6: ANÁLISE DO ESPECIALISTA DE BI
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🧠 Insights Automáticos")

taxa_conversao = (entradas / (entradas + passantes) * 100) if (entradas + passantes) > 0 else 0

st.markdown(f"**1. Taxa de Conversão de Vitrine:** `{taxa_conversao:.1f}%` das pessoas que passaram na frente entraram no mercadinho hoje.")
if taxa_conversao < 10 and passantes > 0:
    st.warning("⚠️ **Conversão Baixa:** Poucas pessoas estão entrando. Sugestão: Melhore a vitrine, use placa de promoção na calçada ou destaque produtos de alto giro.")
elif taxa_conversao >= 10:
    st.success("✅ **Conversão Saudável:** A atratividade da entrada está funcionando!")

st.markdown(f"**2. Tempo Médio na Loja:** `{tempo_medio:.1f} minutos`")
if 0 < tempo_medio <= 5:
    st.info("📌 Perfil de **compra rápida**. Coloque produtos de impulso (doces, snacks) perto do caixa.")
elif 5 < tempo_medio <= 15:
    st.info("📌 Tempo normal para pequenos varejos. Clientes browsing tranquilos.")
elif tempo_medio > 15:
    st.warning("📌 Tempo alto — possível gargalo no caixa ou dificuldade de localizar produtos.")

st.markdown("**3. Estratégia de Produto:**")
st.markdown("> Coloque produtos *destino* (pão, carne) no **fundo da loja** para forçar o cliente a percorrer as prateleiras. Cross-sell é gerado naturalmente.")
