from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import psycopg2
import os

app = FastAPI()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# RAM DA SESSÃO
# =========================
memoria_ram = []


class Mensagem(BaseModel):
    texto: str


# =========================
# CARREGA MEMÓRIA BASE (1x)
# =========================
def carregar_memoria_base():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        cur.execute("SELECT chave, valor FROM memoria_base")
        dados = cur.fetchall()

        cur.close()
        conn.close()

        memoria = "Você é a Sema.\n\nMemória Base:\n"
        for k, v in dados:
            memoria += f"- {k}: {v}\n"

        return memoria

    except Exception as e:
        print("ERRO AO CARREGAR MEMÓRIA BASE:", e)
        return "Você é a Sema."


memoria_base_cache = carregar_memoria_base()


# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {"status": "online"}


# =========================
# CHAT
# =========================
@app.post("/chat")
def chat(msg: Mensagem):

    # salva na RAM
    memoria_ram.append(("user", msg.texto))

    # limita só por segurança (opcional)
    if len(memoria_ram) > 200:
        memoria_ram.pop(0)

    # monta contexto
    contexto = f"""
{memoria_base_cache}

Memória da conversa:
"""

    for role, texto in memoria_ram:
        contexto += f"{role}: {texto}\n"

    # chama IA
    resposta = client.responses.create(
        model="gpt-5-mini",
        input=contexto
    )

    texto_resposta = resposta.output_text

    # salva resposta na RAM
    memoria_ram.append(("assistant", texto_resposta))

    return {
        "resposta": texto_resposta
    }
