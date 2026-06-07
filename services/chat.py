from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def gerar_resposta(contexto: str):
    resposta = client.responses.create(
        model="gpt-5-mini",
        input=contexto
    )

    return resposta.output_text.strip()
