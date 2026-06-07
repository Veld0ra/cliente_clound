from datetime import datetime
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")


def carregar_memoria_base():
    if not DATABASE_URL:
        return "Você é a Sema."

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        cur.execute("SELECT chave, valor FROM memoria_base")
        dados = cur.fetchall()

        cur.close()
        conn.close()

        return "Você é a Sema.\n\n" + "\n".join(
            f"- {k}: {v}" for k, v in dados
        )

    except Exception as e:
        print("ERRO MEMÓRIA BASE:", e)
        return "Você é a Sema."


def carregar_memoria_ontem(usuario_id):
    if not DATABASE_URL or not usuario_id:
        return ""

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        hoje = datetime.now().date()

        cur.execute("""
            SELECT conteudo
            FROM memoria_diario_v2
            WHERE usuario_id = %s AND data = %s
        """, (usuario_id, hoje))

        hoje_data = cur.fetchone()
        memoria_hoje = hoje_data[0] if hoje_data else ""

        cur.execute("""
            SELECT conteudo, data
            FROM memoria_diario_v2
            WHERE usuario_id = %s AND data < %s
            ORDER BY data DESC
            LIMIT 1
        """, (usuario_id, hoje))

        anterior = cur.fetchone()

        memoria_ant = ""

        if anterior:
            conteudo, data = anterior
            memoria_ant = f"""
ÚLTIMO DIA ({data})

{conteudo}
"""

        cur.close()
        conn.close()

        return f"""
HOJE:
{memoria_hoje}

ANTERIOR:
{memoria_ant}
"""

    except Exception as e:
        print("ERRO MEMÓRIA:", e)
        return ""
