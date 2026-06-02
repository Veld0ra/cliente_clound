from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import psycopg2
import os
from datetime import datetime, timedelta
from instrucoes import INSTRUCOES_SEMA

app = FastAPI()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# RAM DA SESSÃO
# =========================
memoria_ram = []

# =========================
# CACHE GLOBAL
# =========================
memoria_base_cache = ""
memoria_ontem_cache = ""


class Mensagem(BaseModel):
    texto: str


# =========================
# MEMÓRIA BASE
# =========================
def carregar_memoria_base():

    if not DATABASE_URL:
        return "Você é a Sema."

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        cur.execute("""
            SELECT chave, valor
            FROM memoria_base
        """)

        dados = cur.fetchall()

        cur.close()
        conn.close()

        return (
            "Você é a Sema.\n\n"
            + "\n".join(f"- {k}: {v}" for k, v in dados)
        )

    except Exception as e:
        print("ERRO MEMÓRIA BASE:", e)
        return "Você é a Sema."


# =========================
# MEMÓRIA DE ONTEM
# =========================
def carregar_memoria_ontem():

    if not DATABASE_URL:
        return ""

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        ontem = datetime.now().date() - timedelta(days=1)

        cur.execute("""
            SELECT conteudo
            FROM memoria_diario_v2
            WHERE data = %s
        """, (ontem,))

        resultado = cur.fetchone()

        cur.close()
        conn.close()

        if resultado:
            return resultado[0]

        return ""

    except Exception as e:
        print("ERRO MEMÓRIA ONTEM:", e)
        return ""


# =========================
# START DA SESSÃO
# =========================
@app.get("/start")
def start():

    global memoria_base_cache
    global memoria_ontem_cache

    memoria_ram.clear()

    memoria_base_cache = carregar_memoria_base()
    memoria_ontem_cache = carregar_memoria_ontem()

    print("✔ Memória Base carregada")
    print("✔ Memória de ontem carregada")

    return {
        "status": "ok",
        "memoria_base": memoria_base_cache,
        "memoria_ontem": memoria_ontem_cache
    }


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

    texto = msg.texto.strip()

    if texto.lower() == "sair":

        salvar_diario()
        memoria_ram.clear()

        return {
            "resposta": "Sessão finalizada. Conversa salva no diário."
        }

    # Salva mensagem do usuário
    memoria_ram.append(("user", texto))

    # Limita RAM para evitar crescimento infinito
    if len(memoria_ram) > 100:
        memoria_ram.pop(0)

    # Últimas mensagens da conversa atual
    conversa_atual = "\n".join(
        f"{role}: {conteudo}"
        for role, conteudo in memoria_ram[-10:]
    )

    # Contexto enviado para a IA
    contexto = f"""
{INSTRUCOES_SEMA}

{memoria_base_cache}

Memória de ontem:
{memoria_ontem_cache}

Memória atual:
{conversa_atual}
"""

    resposta = client.responses.create(
        model="gpt-5-mini",
        input=contexto
    )

    texto_resposta = resposta.output_text.strip()

    # Debug para futura busca de memória
    if texto_resposta == "[CONSULTAR_MEMORIA]":
        print("🔎 IA solicitou consulta de memória")

    # Salva resposta na RAM
    memoria_ram.append(("assistant", texto_resposta))

    if len(memoria_ram) > 100:
        memoria_ram.pop(0)

    return {
        "resposta": texto_resposta
    }

# =========================
# SALVAR DIÁRIO
# =========================
def salvar_diario():

    if not DATABASE_URL:
        return

    if not memoria_ram:
        return

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        data = datetime.now().date()

        sessao = "=== SESSÃO ===\n\n"
        sessao += "\n".join(
            f"{role}: {texto}"
            for role, texto in memoria_ram
        )

        cur.execute("""
            INSERT INTO memoria_diario_v2 (data, conteudo)
            VALUES (%s, %s)

            ON CONFLICT (data)
            DO UPDATE SET
            conteudo = memoria_diario_v2.conteudo
                       || E'\n\n'
                       || EXCLUDED.conteudo
        """, (data, sessao))

        conn.commit()

        cur.close()
        conn.close()

        print("✔ Diário salvo")

    except Exception as e:
        print("❌ ERRO DIÁRIO:", e)
