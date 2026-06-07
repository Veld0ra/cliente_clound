import psycopg2
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")


def salvar_diario(usuario, memoria_ram):

    if not DATABASE_URL or not memoria_ram:
        return

    if usuario["tipo"] == "visitante":
        return

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    data = datetime.now().date()

    sessao = "\n".join(
        f"{r}: {t}" for r, t in memoria_ram
    )

    cur.execute("""
        INSERT INTO memoria_diario_v2
        (usuario_id, usuario, data, conteudo)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (usuario_id, data)
        DO UPDATE SET conteudo =
        memoria_diario_v2.conteudo || E'\n\n' || EXCLUDED.conteudo
    """, (
        usuario["id"],
        usuario["nome"],
        data,
        sessao
    ))

    conn.commit()
    cur.close()
    conn.close()

    print("✔ Diário salvo")
