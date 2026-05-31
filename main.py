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
# RAM (sessão da conversa)
# =========================
memoria_ram = []


class Mensagem(BaseModel):
    texto: str


# =========================
# MEMÓRIA BASE
# =========================
def carregar_memoria_base():
    if not DATABASE_URL:
        return "Você é a Sema."

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    cur.execute("SELECT chave, valor FROM memoria_base")
    dados = cur.fetchall()

    cur.close()
    conn.close()

    linhas = [f"- {k}: {v}" for k, v in dados]
    return "Você é a Sema.\n\nMemória Base:\n" + "\n".join(linhas)


# =========================
# MEMÓRIA DE ONTEM
# =========================
def carregar_memoria_ontem():
    if not DATABASE_URL:
        return ""

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

    if not dados:
        return ""

    linhas = [f"{r}: {t}" for r, t in dados]
    return "\nMemória de ontem:\n" + "\n".join(linhas)


# =========================
# SALVAR NO DIÁRIO
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
        [(data, role, texto) for role, texto in memoria_ram]
    )

    conn.commit()
    cur.close()
    conn.close()


# =========================
# START DA SESSÃO
# =========================
@app.get("/start")
def start():
    memoria_ram.clear()

    base = carregar_memoria_base()
    ontem = carregar_memoria_ontem()

    return {
        "memoria_base": base,
        "memoria_ontem": ontem
    }


# =========================
# CHAT
# =========================
@app.post("/chat")
def chat(msg: Mensagem):

    texto = msg.texto.strip().lower()

    # sair = finaliza sessão
    if texto == "sair":
        salvar_diario()
        memoria_ram.clear()
        return {"resposta": "Sessão finalizada. Conversa salva no diário."}

    # salva RAM
    memoria_ram.append(("user", msg.texto))

    if len(memoria_ram) > 200:
        memoria_ram.pop(0)

    conversa = "\n".join(f"{r}: {t}" for r, t in memoria_ram[-20:])

    prompt = f"""
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


# =========================
# DEBUG
# =========================
@app.get("/debug-neon")
def debug():
    if not DATABASE_URL:
        return {"status": "erro", "erro": "DATABASE_URL não existe"}

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    cur.execute("SELECT chave, valor FROM memoria_base")
    dados = cur.fetchall()

    cur.close()
    conn.close()

    return {"status": "ok", "dados": dados}
