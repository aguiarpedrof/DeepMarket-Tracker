import psycopg2
import os
from dotenv import load_dotenv

# Carrega o .env localizado na raiz do projeto
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def run_sql_file(filename, conn):
    with open(filename, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        print(f"✅ Arquivo {os.path.basename(filename)} executado com sucesso.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao executar {os.path.basename(filename)}: {e}")
    finally:
        cur.close()

if __name__ == "__main__":
    try:
        print("Conectando ao banco...")
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "postgres"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres")
        )
        print("✅ Conectado ao banco de dados.")

        base_dir = os.path.dirname(__file__)
        
        # 1. Cria ou recria as tabelas
        run_sql_file(os.path.join(base_dir, "01_schema.sql"), conn)
        
        # 2. Popula as dimensões de calendário e horas
        # (se não quiser popular dados do ano todo, ignore o passo 2. 
        # Mas para o Power BI cruzar datas, as tabelas de dimensões recomendam estarem populadas previamente)
        run_sql_file(os.path.join(base_dir, "02_populate_dims.sql"), conn)
        
        # 3. Não executa o migrador porque você não quer os dados antigos
        
        conn.close()
        print("\n🚀 Configuração concluída! Você já pode abrir o Power BI.")

    except Exception as e:
        print(f"Erro de conexão com o banco de dados: {e}")
