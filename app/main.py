import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router  
from routes.user import router as user_router
from routes.csv import router as csv_router  
from routes.envio_relatorio import router as envio_relatorio_router, verificar_envio_semanal
from contextlib import asynccontextmanager

# Função de verificação periódica
async def agendar_verificacao_boletim():
    while True:
        try:
            print("Executando verificação automática do boletim...")
            verificar_envio_semanal()
        except Exception as e:
            print(f"Erro ao executar verificação do boletim: {e}")
        
        await asyncio.sleep(30)  # a cada 30 segs
        # ou: await asyncio.sleep(60 * 60 * 24)  # uma vez por dia


# Define ciclo de vida da aplicação (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando aplicação e agendando boletim automático...")

    # Inicia a tarefa em background (não bloqueia o servidor)
    task = asyncio.create_task(agendar_verificacao_boletim())

    yield  # mantém o app rodando normalmente

    # Encerra ao desligar o app
    task.cancel()
    print("Encerrando aplicação e parando agendamento.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Hello, Backend em Python!"}

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(csv_router) 
app.include_router(envio_relatorio_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)