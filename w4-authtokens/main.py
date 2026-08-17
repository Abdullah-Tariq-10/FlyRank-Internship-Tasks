import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client

# Load secrets from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file.")

# Initialize the Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# HTTP bearer for swagger UI
security = HTTPBearer()

app = FastAPI(
    title="Auth Login & Protect API",
    description="Secure FastAPI application integrated with Supabase Auth",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "Server running and connected to Supabase"}

# Schemas
class UserAuth(BaseModel):
    email: str
    password: str 


# Reusable auth dependency AKA the guard + swagger UI padlock
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extracts and verifies the Bearer JWT with Supabase and enables the Swagger lock icon."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Access token required"}
        )

    token = credentials.credentials

    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid or expired token"}
            )
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired token"}
        )



# endpoints 
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def sign_up(credentials: UserAuth):
    email = credentials.email.strip()
    password = credentials.password

    # Validate inputs
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Email and password are required"}
        )

    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Could not create user"}
            )

        return {
            "message": "User created successfully",
            "user": {
                "id": response.user.id,
                "email": response.user.email
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)}
        )


@app.post("/auth/login", status_code=status.HTTP_200_OK)
def log_in(credentials: UserAuth):
    email = credentials.email.strip()
    password = credentials.password

    # Validate inputs
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Email and password cannot be empty"}
        )

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid login credentials"}
            )

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": response.user.id,
                "email": response.user.email
            }
        }
    except HTTPException:
        raise
    except Exception:
        # Supabase raises an error on wrong password / bad user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid login credentials"}
        )


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def log_out(current_user = Depends(get_current_user)):
    """Ends the active user session and returns 204 No Content."""
    try:
        supabase.auth.sign_out()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)}
        )

    
#  Public & Protected Routes

@app.get("/public/info", status_code=status.HTTP_200_OK)
def public_info():
    return {"message": "Welcome stranger! This info is public."}



# protected endpoints both guarded by Depends(get_current_user)

@app.get("/protected/profile", status_code=status.HTTP_200_OK)
def protected_profile(current_user = Depends(get_current_user)):
    return {
        "id" : current_user.id,
        "email" : current_user.email,
        "created_at" : current_user.created_at
    }

@app.get("/protected/dashboard", status_code=status.HTTP_200_OK)
def protected_dashboard(current_user = Depends(get_current_user)):
    return {
        "message": f"Welcome to the secret dashboard, {current_user.email}!",
        "user_id": current_user.id
    }








