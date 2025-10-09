from fastapi import FastAPI
import os

app = FastAPI(title="CutnPaste")

@app.get("/")
async def root():
    return {"message": "🎬 CutnPaste Video Editor - FULLY UPDATED!", "version": "2.0", "features": ["Video Editing", "Subscriptions", "Payments"]}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
