from pydantic import BaseModel

class Mensagem(BaseModel):
    texto: str
    id: int | None = None
    nome: str = ""
    pronome: str = ""
    memoria: str = ""
    tipo: str = "usuario"
