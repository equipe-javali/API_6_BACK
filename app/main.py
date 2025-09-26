from fastapi import FastAPI
from routes.auth import router as auth_router  
from routes.user import router as user_router
from routes.routes import router as routes_router

app = FastAPI()



@app.get("/")
def home():
    return {"message": "Hello, Backend em Python!"}

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(routes_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
