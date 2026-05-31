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

class Mensagem(BaseModel):
    texto: str


def carregar_memoria():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("SELECT chave, valor FROM memoria_base")
    memoria_base = cur.fetchall()

    cur.execute(
        "SELECT categoria, conteudo FROM memoria_permanente"
    )
    memoria_permanente = cur.fetchall()

    cur.close()
    conn.close()

    contexto = "Você é Sema.\n\n"

    contexto += "Memória Base:\n"

    for chave, valor in memoria_base:
        contexto += f"{chave}: {valor}\n"

    contexto += "\nMemória Permanente:\n"

    for categoria, conteudo in memoria_permanente:
        contexto += f"- {categoria}: {conteudo}\n"

    return contexto


@app.get("/")
def home():
    return {"status": "online"}


@app.post("/chat")
def chat(msg: Mensagem):

    contexto = carregar_memoria()

    prompt = f"""
{contexto}

Mensagem da usuária:
{msg.texto}
"""

    resposta = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return {
        "resposta": resposta.output_text
    }
