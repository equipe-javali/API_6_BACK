from fastapi import FastAPI
from .routes.envio_relatorio import enviar_relatorio

app = FastAPI()

app.include_router(enviar_relatorio)

def home():
    return {"message": "Hello, Backend em Python!"}

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(csv_router) 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)