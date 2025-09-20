from fastapi import FastAPI

app = FastAPI()

app.include_router(enviar_relatorio.router)

def home():
    return {"message": "Hello, Backend em Python!"}
