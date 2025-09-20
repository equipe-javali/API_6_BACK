from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router  
from routes.user import router as user_router
from routes.csv import router as csv_router  # Adicione esta linha


app = FastAPI()

app.include_router(enviar_relatorio.router)

def home():
    return {"message": "Hello, Backend em Python!"}

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(csv_router) 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)