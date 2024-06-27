import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    HOST_NAME = os.getenv('HOST_NAME')
    PORT = os.getenv('PORT')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ill-never-tell'
