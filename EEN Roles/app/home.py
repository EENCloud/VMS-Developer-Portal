from flask import render_template
from app.auth import auth_required

# Home page route
@auth_required
def index():
    return render_template('index.html')