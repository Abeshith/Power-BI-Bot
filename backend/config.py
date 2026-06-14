import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

GROQ_MODEL = "llama-3.3-70b-versatile"

CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "https://app.powerbi.com",
    "https://localhost:3000",
]

DEBUG = ENVIRONMENT == "development"
