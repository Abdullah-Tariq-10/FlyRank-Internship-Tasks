import os
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client, Client

# Load secrets from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file.")

# Initialize the Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="Auth Login & Protect API",
    description="Secure API with Supabase Auth and FastAPI",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "Server running and connected to Supabase"}