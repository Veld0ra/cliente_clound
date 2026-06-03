from fastapi import APIRouter
from pydantic import BaseModel
import psycopg2
import os

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# MODEL
# =========================

class Usuario(BaseModel):
    nome: str


# =========================
# LISTAR USUÁRIOS
# =========================

@router.get("/usuarios")
def listar_usuarios():

    try:

        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )

        cur = conn.cursor()

        cur.execute("""
            SELECT id, nome
            FROM usuarios
            ORDER BY nome
        """)

        usuarios = cur.fetchall()

        cur.close()
        conn.close()

        return [
            {
                "id": uid,
                "nome": nome
            }
            for uid, nome in usuarios
        ]

    except Exception as e:

        return {
            "erro": str(e)
        }


# =========================
# NOVO USUÁRIO
# =========================

@router.post("/novo-usuario")
def novo_usuario(usuario: Usuario):

    try:

        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )

        cur = conn.cursor()

        cur.execute("""
            INSERT INTO usuarios
            (nome, pronome, memoria)
            VALUES (%s, %s, %s)
        """, (
            usuario.nome,
            "não informado",
            "..."
        ))

        conn.commit()

        cur.close()
        conn.close()

        return {
            "status": "ok",
            "nome": usuario.nome
        }

    except Exception as e:

        return {
            "erro": str(e)
        }


# =========================
# LOGIN
# =========================

@router.post("/login")
def login(usuario: Usuario):

    try:

        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )

        cur = conn.cursor()

        cur.execute("""
            SELECT nome, pronome, memoria
            FROM usuarios
            WHERE nome = %s
        """, (usuario.nome,))

        resultado = cur.fetchone()

        cur.close()
        conn.close()

        if not resultado:

            return {
                "erro": "Usuário não encontrado"
            }

        nome, pronome, memoria = resultado

        return {
            "nome": nome,
            "pronome": pronome,
            "memoria": memoria,
            "tipo": "usuario"
        }

    except Exception as e:

        return {
            "erro": str(e)
        }
