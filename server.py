from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Simple imports for now
load_dotenv()

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'cutnpaste_production')]

app = FastAPI(title="CutnPaste Video Editor", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic routes
@app.get("/")
async def root():
    return {"message": "CutnPaste Video Editor API", "version": "2.0.0"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

# Subscription plans endpoint
@app.get("/api/subscriptions/plans")
async def get_plans():
    return {
        "plans": [
            {
                "plan": "free",
                "name": "Free",
                "price_monthly": 0,
                "price_yearly": 0,
                "features": ["Basic editing", "720p export", "3 projects", "Watermark"],
                "limits": {"max_projects": 3, "max_export_quality": "720p"}
            },
            {
                "plan": "pro", 
                "name": "Pro",
                "price_monthly": 7.99,
                "price_yearly": 54.99,
                "features": ["4K export", "No watermark", "AI features", "Unlimited projects"],
                "limits": {"max_projects": -1, "max_export_quality": "4K"}
            },
            {
                "plan": "business",
                "name": "Business", 
                "price_monthly": 17.99,
                "price_yearly": 191.99,
                "features": ["Everything in Pro", "Team collaboration", "Brand kit", "Unlimited storage"],
                "limits": {"max_projects": -1, "max_export_quality": "4K"}
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
