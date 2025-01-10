""" Initialize the Flask app and set up the EENClient. """
import os
from flask import Flask
from dotenv import load_dotenv
from .een_client import EENClient, TokenStorage

load_dotenv('.flaskenv')


def create_app():
    app = Flask(__name__)
    app.client_id = os.getenv('CLIENT_ID')
    app.client_secret = os.getenv('CLIENT_SECRET')
    app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')
    if not app.client_id or not app.client_secret:
        raise ValueError("CLIENT_ID and CLIENT_SECRET must be set in the environment.")

    # Initialize TokenStorage and EENClient
    class MyTokenStorage(TokenStorage):
        def __init__(self):
            self.tokens = {}

        def get(self, key):
            return self.tokens.get(key)

        def set(self, key, value):
            self.tokens[key] = value

        def __contains__(self, key):
            return key in self.tokens

    token_storage = MyTokenStorage()
    app.een_client = EENClient(
        client_id=app.client_id,
        client_secret=app.client_secret,
        redirect_uri=os.getenv('REDIRECT_URI'),
        token_storage=token_storage
    )

    # Register blueprints and other initialization code
    from .routes import api_bp
    app.register_blueprint(api_bp)

    return app
