from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import psycopg2
import os
from datetime import datetime, timedelta
from instrucoes import INSTRUCOES_SEMA
from inicializacao import router

app = FastAPI()

app.include_router(router)

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
usuario_atual_id = None
usuario_atual_nome = ""
usuario_atual_tipo = "visitante"

# =========================
# MODELS
# =========================
class Mensagem(BaseModel):
    texto: str

    id: int | None = None

    nome: str = ""
    pronome: str = ""
    memoria: str = ""

    tipo: str = "usuario"

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
def carregar_memoria_ontem(usuario_id):

    if not DATABASE_URL:
        return ""

    if not usuario_id:
        return ""

    try:

        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )

        cur = conn.cursor()

        hoje = datetime.now().date()

        # Conversas de hoje
        cur.execute("""
            SELECT conteudo
            FROM memoria_diario_v2
            WHERE usuario_id = %s
            AND data = %s
        """, (
            usuario_id,
            hoje
        ))

        resultado_hoje = cur.fetchone()

        memoria_hoje = (
            resultado_hoje[0]
            if resultado_hoje
            else ""
        )

        # Último dia anterior
        cur.execute("""
            SELECT conteudo, data
            FROM memoria_diario_v2
            WHERE usuario_id = %s
            AND data < %s
            ORDER BY data DESC
            LIMIT 1
        """, (
            usuario_id,
            hoje
        ))

        resultado_anterior = cur.fetchone()

        memoria_anterior = ""

        if resultado_anterior:

            conteudo, data_memoria = resultado_anterior

            memoria_anterior = f"""
ÚLTIMO DIA DE CONVERSA ({data_memoria})

{conteudo}
"""

        cur.close()
        conn.close()

        return f"""
CONVERSAS DE HOJE

{memoria_hoje}

{memoria_anterior}
"""

    except Exception as e:

        print("ERRO MEMÓRIA:", e)

        return ""

# =========================
# START
# =========================
@app.get("/start")
def start():

    global memoria_base_cache
    global memoria_ontem_cache

    memoria_ram.clear()

    memoria_base_cache = carregar_memoria_base()
    memoria_ontem_cache = ""

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

    global usuario_atual_id
    global usuario_atual_nome
    global usuario_atual_tipo

    usuario_atual_id = msg.id
    usuario_atual_nome = msg.nome
    usuario_atual_tipo = msg.tipo

    global memoria_ontem_cache

    if usuario_atual_tipo != "visitante":

    memoria_ontem_cache = carregar_memoria_ontem(
        usuario_atual_id
    )

    texto = msg.texto.strip()

    if texto.lower() == "sair":

        salvar_diario()
        memoria_ram.clear()

        return {
            "resposta": "Sessão finalizada. Conversa salva no diário."
        }

    memoria_ram.append(("user", texto))

    if len(memoria_ram) > 100:
        memoria_ram.pop(0)

    conversa_atual = "\n".join(
        f"{role}: {conteudo}"
        for role, conteudo in memoria_ram[-10:]
    )

    perfil_usuario = f"""
Perfil do usuário:

Nome: {msg.nome}
Pronome: {msg.pronome}
Informações conhecidas:
{msg.memoria}
"""

    contexto = f"""
{INSTRUCOES_SEMA}

{memoria_base_cache}

Memória de ontem:
{memoria_ontem_cache}

{perfil_usuario}

Memória atual:
{conversa_atual}
"""

    resposta = client.responses.create(
        model="gpt-5-mini",
        input=contexto
    )

    texto_resposta = resposta.output_text.strip()

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

    global usuario_atual_id
    global usuario_atual_nome
    global usuario_atual_tipo

    if not DATABASE_URL or not memoria_ram:
        return

    # visitante não salva histórico
    if usuario_atual_tipo == "visitante":
        return

    try:

        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )

        cur = conn.cursor()

        data = datetime.now().date()

        sessao = "=== SESSÃO ===\n\n"
        sessao += "\n".join(
            f"{role}: {texto}"
            for role, texto in memoria_ram
        )

        cur.execute("""
            INSERT INTO memoria_diario_v2
            (
                usuario_id,
                usuario,
                data,
                conteudo
            )
            VALUES (%s, %s, %s, %s)

            ON CONFLICT (usuario_id, data)

            DO UPDATE SET
            conteudo = memoria_diario_v2.conteudo
                       || E'\n\n'
                       || EXCLUDED.conteudo
        """, (
            usuario_atual_id,
            usuario_atual_nome,
            data,
            sessao
        ))

        conn.commit()

        cur.close()
        conn.close()

        print(
            f"✔ Diário salvo para "
            f"{usuario_atual_nome}"
        )

    except Exception as e:
        print("❌ ERRO DIÁRIO:", e)
