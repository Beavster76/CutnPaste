from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import logging
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

# Setup logging and environment
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    logger.error("❌ MONGO_URL environment variable not set!")
    raise ValueError("MONGO_URL environment variable is required")

logger.info(f"🔗 Connecting to MongoDB...")
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'cutnpaste_db')]

# Create the main app
app = FastAPI(
    title="CutnPaste Video Editor API", 
    version="2.2.0",
    description="CutnPaste API with Authentication"
)

# CORS configuration
cors_origins = os.environ.get('CORS_ORIGINS', 'https://cutnpaste.ca,https://www.cutnpaste.ca,http://localhost:3000,https://cutnpaste1-frontend.onrender.com').split(',')

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)
JWT_SECRET = os.environ.get('JWT_SECRET', 'cutnpaste-secret-key-2024')

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    display_name: Optional[str]
    is_premium: bool = False
    email_verified: bool = False

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

# API Routes
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {
        "message": "🎬 CutnPaste Video Editor API - AUTHENTICATION SYSTEM!", 
        "version": "2.2.0",
        "features": [
            "✅ User Registration & Login",
            "✅ JWT Authentication",
            "✅ Password Hashing",
            "✅ Database Integration"
        ],
        "status": "production-ready"
    }

@api_router.get("/health")
async def health_check():
    try:
        await db.command("ping")
        return {
            "status": "healthy", 
            "service": "cutnpaste-api",
            "database": "connected",
            "version": "2.2.0",
            "authentication": "enabled"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "cutnpaste-api", 
            "database": "disconnected",
            "error": str(e)
        }

# Authentication Routes
@api_router.post("/users/register")
async def register_user(user_data: UserRegister):
    """Register new user"""
    try:
        # Check if user exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Validate password
        if len(user_data.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
        # Create user
        user_id = f"user_{int(datetime.now().timestamp())}"
        
        user_doc = {
            "_id": user_id,
            "email": user_data.email,
            "password": hash_password(user_data.password),
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "display_name": user_data.display_name or f"{user_data.first_name} {user_data.last_name}",
            "is_premium": False,
            "email_verified": True,  # Simplified - auto-verify
            "created_at": datetime.now(timezone.utc),
            "subscription_plan": "free"
        }
        
        await db.users.insert_one(user_doc)
        
        # Generate token
        token = create_jwt_token(user_id)
        
        return {
            "success": True,
            "message": "Registration successful",
            "user_id": user_id,
            "token": token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@api_router.post("/users/login")
async def login_user(login_data: UserLogin):
    """Login user"""
    try:
        user = await db.users.find_one({"email": login_data.email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not verify_password(login_data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate token
        token = create_jwt_token(user["_id"])
        
        return {
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["_id"],
                "email": user["email"],
                "display_name": user["display_name"],
                "is_premium": user.get("is_premium", False)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@api_router.get("/users/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=['HS256'])
        user_id = payload['user_id']
        
        user = await db.users.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user["_id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "display_name": user["display_name"],
            "is_premium": user.get("is_premium", False),
            "email_verified": user.get("email_verified", False)
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user info")

# Subscription Routes
@api_router.get("/subscriptions/plans")
async def get_subscription_plans():
    """Get subscription plans"""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price": 0,
                "currency": "USD",
                "features": ["720p Export", "3 Projects", "1GB Storage", "Watermark"]
            },
            {
                "id": "pro_monthly",
                "name": "Pro Monthly", 
                "price": 7.99,
                "currency": "USD",
                "interval": "month",
                "features": ["4K Export", "Unlimited Projects", "100GB Storage", "No Watermark", "AI Features"]
            },
            {
                "id": "pro_yearly",
                "name": "Pro Yearly",
                "price": 54.99, 
                "currency": "USD",
                "interval": "year",
                "features": ["4K Export", "Unlimited Projects", "100GB Storage", "No Watermark", "AI Features"]
            }
        ]
    }

# Payment Routes
@api_router.get("/payments/packages")
async def get_payment_packages():
    """Get payment packages"""
    return {
        "packages": [
            {
                "id": "pro_monthly",
                "name": "Pro Monthly",
                "price": 799,  # in cents
                "currency": "usd",
                "interval": "month",
                "trial_days": 7
            },
            {
                "id": "pro_yearly",
                "name": "Pro Yearly", 
                "price": 5499,  # in cents
                "currency": "usd",
                "interval": "year",
                "trial_days": 7
            }
        ]
    }

# Include routers
app.include_router(api_router)

# Add root route
@app.get("/")
async def root_health():
    return {
        "message": "🎬 CutnPaste Video Editor API", 
        "version": "2.2.0",
        "status": "running",
        "authentication": "enabled",
        "docs": "/docs"
    }

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 CutnPaste Authentication API starting up...")
    logger.info("🎬 Features: User Registration, Login, JWT Authentication")
    
    try:
        await db.command("ping")
        logger.info("✅ Database connection successful")
        
        # Create basic indexes
        try:
            await db.users.create_index("email", unique=True)
            logger.info("✅ Database indexes created")
        except Exception:
            pass  # Index might already exist
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
