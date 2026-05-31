from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import psycopg2
import os
from datetime import datetime, timedelta

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# RAM DA SESSÃO
# =========================
memoria_ram = []

# =========================
# CACHE GLOBAL (IMPORTANTE)
# =========================
memoria_base_cache = ""
memoria_ontem_cache = ""


class Mensagem(BaseModel):
    texto: str


# =========================
# CARREGA BASE (SÓ NO START)
# =========================
def carregar_memoria_base():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    cur.execute("SELECT chave, valor FROM memoria_base")
    dados = cur.fetchall()

    cur.close()
    conn.close()

    return "Você é a Sema.\n\n" + "\n".join([f"- {k}: {v}" for k, v in dados])


# =========================
# CARREGA ONTEM (SÓ NO START)
# =========================
def carregar_memoria_ontem():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    ontem = datetime.now().date() - timedelta(days=1)

    cur.execute("""
        SELECT role, conteudo
        FROM memoria_diario
        WHERE data = %s
        ORDER BY id ASC
    """, (ontem,))

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return "\n".join([f"{r}: {t}" for r, t in dados])


# =========================
# START (AQUI CARREGA TUDO UMA VEZ)
# =========================
@app.get("/start")
def start():
    global memoria_base_cache, memoria_ontem_cache

    memoria_ram.clear()

    memoria_base_cache = carregar_memoria_base()
    memoria_ontem_cache = carregar_memoria_ontem()

    return {
        "status": "ok",
        "memoria_base": memoria_base_cache,
        "memoria_ontem": memoria_ontem_cache
    }


# =========================
# CHAT (SEM BANCO AQUI)
# =========================
@app.post("/chat")
def chat(msg: Mensagem):

    texto = msg.texto.strip().lower()

    if texto == "sair":
        salvar_diario()
        memoria_ram.clear()
        return {"resposta": "Sessão finalizada. Conversa salva no diário."}

    memoria_ram.append(("user", msg.texto))

    contexto = f"""
{memoria_base_cache}

Memória de ontem:
{memoria_ontem_cache}

Memória atual:
{chr(10).join(f"{r}: {t}" for r, t in memoria_ram[-10:])}
"""

    resposta = client.responses.create(
        model="gpt-5-mini",
        input=contexto
    )

    texto_resposta = resposta.output_text

    memoria_ram.append(("assistant", texto_resposta))

    return {"resposta": texto_resposta}


# =========================
# SALVAR DIÁRIO
# =========================
def salvar_diario():
    if not DATABASE_URL:
        return

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    data = datetime.now().date()

    cur.executemany(
        """
        INSERT INTO memoria_diario (data, role, conteudo, timestamp)
        VALUES (%s, %s, %s, NOW())
        """,
        [(data, r, t) for r, t in memoria_ram]
    )

    conn.commit()
    cur.close()
    conn.close()
