from fastapi import FastAPI
from app.routes import enviar_relatorio

app = FastAPI()

app.include_router(enviar_relatorio.router)

def home():
    return {"message": "Hello, Backend em Python!"}
