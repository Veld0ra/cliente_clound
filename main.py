from fastapi import FastAPI
from inicializacao import router
from models.mensagem import Mensagem

from core.usuario import *
from core.memoria import carregar_memoria_base, carregar_memoria_ontem
from services.chat import gerar_resposta
from services.diario import salvar_diario
from config.instrucoes import INSTRUCOES_SEMA

app = FastAPI()
app.include_router(router)

memoria_ram = []
memoria_base_cache = ""
memoria_ontem_cache = ""


@app.get("/start")
def start():
    global memoria_base_cache

    memoria_ram.clear()
    memoria_base_cache = carregar_memoria_base()

    return {"status": "ok"}


@app.post("/chat")
def chat(msg: Mensagem):

    global memoria_ontem_cache

    usuario_atual_id = msg.id
    usuario_atual_nome = msg.nome
    usuario_atual_tipo = msg.tipo

    if usuario_atual_tipo != "visitante":
        memoria_ontem_cache = carregar_memoria_ontem(msg.id)

    memoria_ram.append(("user", msg.texto))

    contexto = f"""
{memoria_base_cache}

{memoria_ontem_cache}

{msg.nome}
{msg.pronome}

{memoria_ram[-10:]}
"""

    resposta = gerar_resposta(contexto)

    memoria_ram.append(("assistant", resposta))

    return {"resposta": resposta}
