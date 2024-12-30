import datetime
from flask import Flask, jsonify
from dotenv import load_dotenv
from datetime import timedelta
import os
import logging

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.client_id = os.getenv('CLIENT_ID')
    app.client_secret = os.getenv('CLIENT_SECRET')
    app.secret_key = os.environ.get('SECRET_KEY') or 'ill-never-tell'

    # Validate required environment variables
    if not app.client_id or not app.client_secret:
        raise ValueError("CLIENT_ID and CLIENT_SECRET must be set in the environment.")

    # Use secure cookies and configure session lifetime
    app.config.update(
        SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',  # Secure only in production
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

    # Register error handlers
    register_error_handlers(app)

    with app.app_context():
        from app import routes

    return app

def register_error_handlers(app):
    
    @app.errorhandler(400)
    def bad_request_error(error):
        app.logger.error(f"400 Bad Request: {error}")
        return jsonify({"error": "Bad Request", "message": str(error)}), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        app.logger.error(f"401 Unauthorized: {error}")
        return jsonify({"error": "Unauthorized", "message": str(error)}), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.error(f"403 Forbidden: {error}")
        return jsonify({"error": "Forbidden", "message": str(error)}), 403

    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.error(f"404 Not Found: {error}")
        return jsonify({"error": "Not Found", "message": str(error)}), 404
    
    @app.errorhandler(409)
    def conflict_error(error):
        app.logger.error(f"409 Conflict: {error}")
        return jsonify({"error": "Conflict", "message": str(error)}), 409

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"500 Internal Server Error: {error}")
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        app.logger.error(f"Unhandled Exception: {error}")
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500