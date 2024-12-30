from app import create_app
from flask import jsonify, send_from_directory
import os

app = create_app()

@app.errorhandler(Exception)
def handle_error(e):
    response = {"error": "An internal error occurred. Please try again later."}
    return jsonify(response), 500

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3333)