from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

class Mensagem(BaseModel):
    texto: str

@app.get("/")
def home():
    return {"status": "online"}

@app.post("/chat")
def chat(msg: Mensagem):

    resposta = client.responses.create(
        model="gpt-5-mini",
        input=msg.texto
    )

    return {
        "resposta": resposta.output_text
    }
