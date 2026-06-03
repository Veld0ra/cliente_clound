import psycopg2
import os
import time
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# CONEXÃO
# =========================

def conectar():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )


# =========================
# LISTAR USUÁRIOS
# =========================

def listar_usuarios():

    try:

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, nome
            FROM usuarios
            ORDER BY nome
        """)

        usuarios = cur.fetchall()

        cur.close()
        conn.close()

        return usuarios

    except Exception as e:

        print("Erro:", e)
        return []


# =========================
# CARREGAR USUÁRIO
# =========================

def carregar_usuario(nome):

    try:

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            SELECT nome, pronome, memoria
            FROM usuarios
            WHERE nome = %s
        """, (nome,))

        resultado = cur.fetchone()

        cur.close()
        conn.close()

        return resultado

    except Exception as e:

        print("Erro:", e)
        return None


# =========================
# NOVO USUÁRIO
# =========================

def criar_usuario():

    print("\n==================")
    print("NOVO USUÁRIO")
    print("==================\n")

    nome = input("Digite seu nome: ").strip()

    if not nome:
        print("Nome inválido.")
        return None

    try:

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO usuarios
            (nome, pronome, memoria)
            VALUES (%s, %s, %s)
        """, (
            nome,
            "não informado",
            "..."
        ))

        conn.commit()

        cur.close()
        conn.close()

        print("\n✓ Usuário criado com sucesso.\n")

        return {
            "nome": nome,
            "pronome": "não informado",
            "memoria": "...",
            "tipo": "usuario"
        }

    except Exception as e:

        print("\nErro ao criar usuário:")
        print(e)

        return None


# =========================
# LOGIN
# =========================

def login_usuario():

    usuarios = listar_usuarios()

    if not usuarios:

        print("\nNenhum usuário encontrado.\n")
        return None

    print("\n==================")
    print("USUÁRIO CONHECIDO")
    print("==================\n")

    for indice, (_, nome) in enumerate(usuarios, start=1):

        print(f"[{indice}] {nome}")

    print("\n[0] Voltar\n")

    escolha = input("> ").strip()

    if escolha == "0":
        return None

    try:

        indice = int(escolha) - 1

        if indice < 0:
            return None

        nome = usuarios[indice][1]

        dados = carregar_usuario(nome)

        if not dados:

            return None

        nome, pronome, memoria = dados

        print("\nCarregando perfil...")
        time.sleep(1)

        print("✓ Perfil carregado")
        print(f"Bem-vindo(a), {nome}.\n")

        return {
            "nome": nome,
            "pronome": pronome,
            "memoria": memoria,
            "tipo": "usuario"
        }

    except:

        return None


# =========================
# VISITANTE
# =========================

def modo_visitante():

    print("\n==================")
    print("MODO VISITANTE")
    print("==================\n")

    print("Nenhuma memória será carregada.")
    print("Nenhuma informação será salva.\n")

    resposta = input("Continuar? (s/n): ")

    if resposta.lower() != "s":
        return None

    return {
        "nome": "Visitante",
        "pronome": "não informado",
        "memoria": "",
        "tipo": "visitante"
    }


# =========================
# TELA INICIAL
# =========================

def iniciar_sessao():

    agora = datetime.now()

    print("\nSEMA INICIANDO...\n")

    print("Verificando sistemas...")
    time.sleep(0.5)

    print("✓ Núcleo carregado")
    time.sleep(0.5)

    print("✓ Memória carregada")
    time.sleep(0.5)

    print("✓ Conexão estabelecida")
    time.sleep(0.5)

    print()

    print("Bom dia!")
    print(f"Hoje é {agora.strftime('%d/%m/%Y')}")
    print(f"São {agora.strftime('%H:%M')}.\n")

    print("Pronta para auxiliar.\n")

    while True:

        print("==================")
        print("USUÁRIO")
        print("==================\n")

        print("[1] Usuário conhecido")
        print("[2] Cadastrar novo usuário")
        print("[3] Modo visitante\n")

        escolha = input("> ").strip()

        if escolha == "1":

            usuario = login_usuario()

            if usuario:
                return usuario

        elif escolha == "2":

            usuario = criar_usuario()

            if usuario:
                return usuario

        elif escolha == "3":

            usuario = modo_visitante()

            if usuario:
                return usuario

        print("\nOpção inválida.\n")
