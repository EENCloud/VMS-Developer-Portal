import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Configuration class for the application
class Config:
    CLIENT_ID = os.getenv('CLIENT_ID') 
    CLIENT_SECRET = os.getenv('CLIENT_SECRET') 
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ill-never-tell' # Secret key for Flask session
    PERMENANT_SESSION_LIFETIME = timedelta(days=7) # Session lifetime


