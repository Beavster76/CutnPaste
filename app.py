from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "CutnPaste is working!"}

@app.get("/health")
def health():
    return {"status": "healthy"}
