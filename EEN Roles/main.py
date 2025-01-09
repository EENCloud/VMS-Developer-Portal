from app import create_app
import flask
from flask import jsonify, send_from_directory
import os
import os
import logging

app = create_app()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.errorhandler(Exception)
def handle_error(e):
    logger.error("An error occurred", exc_info=e)  # Log the stack trace for debugging
    response = {"error": "An internal error occurred. Please try again later."}
    return jsonify(response), 500

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                            'favicon.ico',
                            mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    # Use environment variables for configuration
    debug = os.getenv('FLASK_DEBUG', 'true').lower() in ['true', '1', 't']
    print(debug)
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    print(host)
    port = int(os.getenv('FLASK_RUN_PORT', 3333))
    print(port)
    redirect_uri = os.getenv('REDIRECT_URI')
    print ("redirect",os.getenv('REDIRECT_URI')),
    app.run(debug=debug, host=host, port=port)