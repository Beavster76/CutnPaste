from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="CutnPaste API", version="2.2.1")

# CORS configuration
cors_origins = ['https://cutnpaste.ca', 'https://www.cutnpaste.ca', 'https://cutnpaste1-frontend.onrender.com']

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class UserRegister(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    display_name: str = None

class UserLogin(BaseModel):
    email: str
    password: str

# Simple in-memory storage for demo
users_db = {}

# API Routes
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {
        "message": "🎬 CutnPaste - WORKING AUTHENTICATION!", 
        "version": "2.2.1",
        "status": "working"
    }

@api_router.get("/health")
async def health():
    return {"status": "healthy", "message": "All systems working"}

@api_router.post("/users/register")
async def register(user_data: UserRegister):
    try:
        # Simple registration - just store user
        users_db[user_data.email] = {
            "email": user_data.email,
            "password": user_data.password,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "display_name": user_data.display_name or f"{user_data.first_name} {user_data.last_name}"
        }
        
        return {
            "success": True,
            "message": "Registration successful!",
            "user_id": f"user_{len(users_db)}"
        }
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return {"success": False, "message": "Registration failed"}

@api_router.post("/users/login")
async def login(login_data: UserLogin):
    try:
        # Simple login check
        user = users_db.get(login_data.email)
        if user and user["password"] == login_data.password:
            return {
                "success": True,
                "message": "Login successful",
                "token": "demo_token_123",
                "user": {
                    "id": "demo_user_id",
                    "email": user["email"],
                    "display_name": user["display_name"],
                    "is_premium": False
                }
            }
        else:
            return {"success": False, "message": "Invalid credentials"}
    except Exception as e:
        logger.error(f"Login error: {e}")
        return {"success": False, "message": "Login failed"}

@api_router.get("/users/me")
async def get_me():
    return {
        "id": "demo_user",
        "email": "demo@demo.com", 
        "display_name": "Demo User",
        "is_premium": False
    }

# Include routers
app.include_router(api_router)

@app.get("/")
async def root_health():
    return {"message": "CutnPaste API Working", "version": "2.2.1"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
