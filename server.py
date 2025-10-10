from fastapi import FastAPI, APIRouter, HTTPException
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import os
import logging
import smtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="CutnPaste API", version="2.3.0")

# CORS configuration
cors_origins = ['https://cutnpaste.ca', 'https://www.cutnpaste.ca', 'https://cutnpaste1-frontend.onrender.com']

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    headers=["*"],
)

# Email configuration
GMAIL_EMAIL = "zbeavinator@gmail.com"
GMAIL_APP_PASSWORD = "zolc zfuh qnpp euaw"

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

class EmailVerification(BaseModel):
    email: EmailStr
    verification_code: str

# In-memory storage
users_db = {}
verification_codes = {}

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def send_verification_email(email: str, code: str):
    """Send verification email using Gmail SMTP"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_EMAIL
        msg['To'] = email
        msg['Subject'] = "CutnPaste - Verify Your Email Address"
        
        # Email body
        body = f"""
Hello!

Welcome to CutnPaste! Please verify your email address by entering this code:

Verification Code: {code}

This code will expire in 1 hour.

If you didn't create an account with CutnPaste, please ignore this email.

Best regards,
The CutnPaste Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Gmail SMTP setup
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        
        # Send email
        text = msg.as_string()
        server.sendmail(GMAIL_EMAIL, email, text)
        server.quit()
        
        logger.info(f"✅ Verification email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email to {email}: {str(e)}")
        return False

# API Routes
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {
        "message": "🎬 CutnPaste - EMAIL VERIFICATION SYSTEM!", 
        "version": "2.3.0",
        "features": [
            "✅ User Registration",
            "✅ Email Verification", 
            "✅ Gmail SMTP Integration",
            "✅ User Authentication"
        ],
        "status": "working"
    }

@api_router.get("/health")
async def health():
    return {"status": "healthy", "message": "Email verification system ready"}

@api_router.post("/users/register")
async def register(user_data: UserRegister):
    try:
        # Check if user already exists
        if user_data.email in users_db:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Generate verification code
        verification_code = generate_verification_code()
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Store user data (unverified)
        users_db[user_data.email] = {
            "email": user_data.email,
            "password": user_data.password,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "display_name": user_data.display_name or f"{user_data.first_name} {user_data.last_name}",
            "email_verified": False,
            "created_at": datetime.now(timezone.utc)
        }
        
        # Store verification code
        verification_codes[user_data.email] = {
            "code": verification_code,
            "expiry": expiry
        }
        
        # Send verification email
        email_sent = send_verification_email(user_data.email, verification_code)
        
        if email_sent:
            return {
                "success": True,
                "message": "Registration successful! Please check your email for verification code.",
                "user_id": f"user_{len(users_db)}",
                "verification_required": True
            }
        else:
            # If email fails, still return success but mention the issue
            return {
                "success": True,
                "message": "Registration successful! Email verification temporarily unavailable.",
                "user_id": f"user_{len(users_db)}",
                "verification_required": False
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@api_router.post("/users/verify-email")
async def verify_email(verification_data: EmailVerification):
    try:
        email = verification_data.email
        code = verification_data.verification_code
        
        # Check if verification code exists and is valid
        if email not in verification_codes:
            raise HTTPException(status_code=400, detail="No verification code found for this email")
        
        stored_data = verification_codes[email]
        
        # Check if code matches
        if stored_data["code"] != code:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        # Check if code is expired
        if datetime.now(timezone.utc) > stored_data["expiry"]:
            raise HTTPException(status_code=400, detail="Verification code has expired")
        
        # Verify user
        if email in users_db:
            users_db[email]["email_verified"] = True
            
            # Remove verification code after successful verification
            del verification_codes[email]
            
            return {
                "success": True,
                "message": "Email verified successfully! You can now log in.",
                "verified": True
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification error: {e}")
        raise HTTPException(status_code=500, detail="Email verification failed")

@api_router.post("/users/login")
async def login(login_data: UserLogin):
    try:
        email = login_data.email
        password = login_data.password
        
        # Check if user exists
        if email not in users_db:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = users_db[email]
        
        # Check password
        if user["password"] != password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if email is verified
        if not user.get("email_verified", False):
            raise HTTPException(status_code=400, detail="Please verify your email before logging in")
        
        return {
            "success": True,
            "message": "Login successful",
            "token": f"token_{email}_{int(datetime.now().timestamp())}",
            "user": {
                "id": f"user_{email}",
                "email": user["email"],
                "display_name": user["display_name"],
                "is_premium": False,
                "email_verified": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@api_router.post("/users/resend-verification")
async def resend_verification(email_data: dict):
    try:
        email = email_data.get("email")
        
        if not email or email not in users_db:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = users_db[email]
        if user.get("email_verified", False):
            raise HTTPException(status_code=400, detail="Email already verified")
        
        # Generate new verification code
        verification_code = generate_verification_code()
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        verification_codes[email] = {
            "code": verification_code,
            "expiry": expiry
        }
        
        # Send verification email
        email_sent = send_verification_email(email, verification_code)
        
        if email_sent:
            return {
                "success": True,
                "message": "Verification code resent successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=500, detail="Failed to resend verification")

@api_router.get("/users/me")
async def get_me():
    return {
        "id": "demo_user",
        "email": "demo@demo.com", 
        "display_name": "Demo User",
        "is_premium": False,
        "email_verified": True
    }

# Include routers
app.include_router(api_router)

@app.get("/")
async def root_health():
    return {
        "message": "CutnPaste API with Email Verification", 
        "version": "2.3.0",
        "email_system": "active"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
