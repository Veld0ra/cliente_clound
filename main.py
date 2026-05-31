from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import psycopg2
import os
from datetime import datetime, timedelta
import threading
import time

app = FastAPI()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# RAM (conversa atual)
# =========================
memoria_ram = []


# =========================
# CACHE GLOBAL (NÃO CONSULTA NEON TODA HORA)
# =========================
memoria_base_cache = ""
memoria_7dias_cache = ""


class Mensagem(BaseModel):
    texto: str


# =========================
# MEMÓRIA BASE (1x)
# =========================
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

        linhas = [f"- {k}: {v}" for k, v in dados]
        return "Você é a Sema.\n\nMemória Base:\n" + "\n".join(linhas)

    except Exception as e:
        print("ERRO MEMÓRIA BASE:", e)
        return "Você é a Sema."


# =========================
# MEMÓRIA 7 DIAS (CACHE)
# =========================
def carregar_memoria_7_dias():
    if not DATABASE_URL:
        return ""

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        data_limite = datetime.now().date() - timedelta(days=7)

        cur.execute("""
            SELECT data, role, conteudo
            FROM memoria_diario
            WHERE data >= %s
            ORDER BY data ASC, id ASC
        """, (data_limite,))

        dados = cur.fetchall()

        cur.close()
        conn.close()

        if not dados:
            return ""

        contexto = "\nMemória dos últimos 7 dias:\n"

        for data, role, conteudo in dados:
            contexto += f"[{data}] {role}: {conteudo}\n"

        return contexto

    except Exception as e:
        print("ERRO MEMÓRIA 7 DIAS:", e)
        return ""


# =========================
# ATUALIZA CACHE
# =========================
def atualizar_cache():
    global memoria_base_cache, memoria_7dias_cache

    print("🔄 Atualizando memória cache...")

    memoria_base_cache = carregar_memoria_base()
    memoria_7dias_cache = carregar_memoria_7_dias()


# =========================
# LOOP DE REFRESH (a cada 15 min)
# =========================
def loop_cache():
    while True:
        time.sleep(900)  # 15 minutos
        atualizar_cache()


# inicia cache no startup
atualizar_cache()

# thread para atualizar cache automaticamente
threading.Thread(target=loop_cache, daemon=True).start()


# =========================
# SALVAR DIÁRIO NO NEON
# =========================
def salvar_diario():
    if not DATABASE_URL:
        return

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        data = datetime.now().date()

        cur.executemany(
            """
            INSERT INTO memoria_diario (data, role, conteudo, timestamp)
            VALUES (%s, %s, %s, NOW())
            """,
            [(data, role, texto) for role, texto in memoria_ram]
        )

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("ERRO DIÁRIO:", e)


# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {"status": "online"}


# =========================
# DEBUG
# =========================
@app.get("/debug-neon")
def debug_neon():
    if not DATABASE_URL:
        return {"status": "erro", "erro": "DATABASE_URL não existe"}

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        cur.execute("SELECT chave, valor FROM memoria_base")
        dados = cur.fetchall()

        cur.close()
        conn.close()

        return {"status": "ok", "dados": dados}

    except Exception as e:
        return {"status": "erro", "erro": str(e)}


# =========================
# CHAT
# =========================
@app.post("/chat")
def chat(msg: Mensagem):

    texto = msg.texto.strip().lower()

    # comando sair
    if texto == "sair":
        salvar_diario()
        memoria_ram.clear()

        return {"resposta": "Sessão finalizada. Conversa salva no diário."}

    # salva RAM
    memoria_ram.append(("user", msg.texto))

    if len(memoria_ram) > 200:
        memoria_ram.pop(0)

    # conversa atual
    conversa = "\n".join(f"{r}: {t}" for r, t in memoria_ram)

    # prompt final (CACHE + RAM)
    prompt = f"""
{memoria_base_cache}

{memoria_7dias_cache}

Memória da conversa:
{conversa}
"""

    resposta = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    texto_resposta = resposta.output_text

    memoria_ram.append(("assistant", texto_resposta))

    return {"resposta": texto_resposta}
