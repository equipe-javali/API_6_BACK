from fastapi import FastAPI
from .routes.routes import router

app = FastAPI()

app.include_router(router)

@app.get("/")
def home():
    return {"message": "Hello, Backend em Python!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
