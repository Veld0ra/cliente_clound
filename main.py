from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import psycopg2
import os
import json
from datetime import datetime

app = FastAPI()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# RAM (sessão local)
# =========================
memoria_ram = []


class Mensagem(BaseModel):
    texto: str


# =========================
# CARREGA MEMÓRIA BASE (1x)
# =========================
def carregar_memoria_base():
    try:
        if not DATABASE_URL:
            print("❌ DATABASE_URL não configurada")
            return "Você é a Sema."

        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        cur.execute("SELECT chave, valor FROM memoria_base")
        dados = cur.fetchall()

        cur.close()
        conn.close()

        print("MEMÓRIA BASE RAW:", dados)

        contexto = "Você é a Sema.\n\nMemória Base:\n"
        for k, v in dados:
            contexto += f"- {k}: {v}\n"

        return contexto

    except Exception as e:
        print("❌ ERRO AO CARREGAR MEMÓRIA BASE:", e)
        return "Você é a Sema."


memoria_base_cache = carregar_memoria_base()


# =========================
# SALVAR DIÁRIO (FINAL DA SESSÃO)
# =========================
def salvar_diario():
    try:
        data = datetime.now().date().isoformat()

        os.makedirs("data", exist_ok=True)
        caminho = f"data/{data}.json"

        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                diario = json.load(f)
        else:
            diario = {data: []}

        for m in memoria_ram:
            diario[data].append(m)

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(diario, f, ensure_ascii=False, indent=2)

        print("✔ DIÁRIO SALVO COM SUCESSO")

    except Exception as e:
        print("❌ ERRO AO SALVAR DIÁRIO:", e)


# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {"status": "online"}


# =========================
# DEBUG NEON
# =========================
@app.get("/debug-neon")
def debug_neon():
    try:
        if not DATABASE_URL:
            return {"status": "erro", "erro": "DATABASE_URL não existe"}

        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        cur.execute("SELECT chave, valor FROM memoria_base")
        dados = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "status": "ok",
            "dados": dados
        }

    except Exception as e:
        return {
            "status": "erro",
            "erro": str(e)
        }


# =========================
# CHAT
# =========================
@app.post("/chat")
def chat(msg: Mensagem):

    texto = msg.texto.strip().lower()

    # =========================
    # COMANDO SAIR
    # =========================
    if texto == "sair":
        salvar_diario()
        memoria_ram.clear()

        return {
            "resposta": "Sessão finalizada. Conversa salva no diário."
        }

    # =========================
    # SALVA USER NA RAM
    # =========================
    memoria_ram.append(("user", msg.texto))

    if len(memoria_ram) > 200:
        memoria_ram.pop(0)

    # =========================
    # CONTEXTO PARA IA
    # =========================
    contexto = "Você DEVE usar a memória base como verdade.\n\n"
    contexto += memoria_base_cache + "\n\nMemória da conversa:\n"

    for role, texto in memoria_ram:
        contexto += f"{role}: {texto}\n"

    # =========================
    # CHAMADA IA
    # =========================
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
