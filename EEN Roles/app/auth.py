from flask import session, redirect, url_for, request, render_template, current_app
import os
import json
import requests
import urllib.parse
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Authenticate with Eagle Eye Networks, Exchanges an authorization code or refresh token for an access token.
def auth_een(token, type="code"):
    url = "https://auth.eagleeyenetworks.com/oauth2/token"
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code" if type == "code" else "refresh_token",
        "scope": "vms.all",
        "code": token if type == "code" else None,
        "refresh_token": token if type == "refresh" else None,
        "redirect_uri": f"http://{os.getenv('FLASK_RUN_HOST')}:{os.getenv('FLASK_RUN_PORT')}/login"
    }
    try:
        response = requests.post(
            url,
            auth=(os.getenv('CLIENT_ID'), os.getenv('CLIENT_SECRET')),
            data=data,
            headers=headers
        )
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        current_app.logger.error(f"Error during token request: {e}")
        raise Exception(f"Error during token request: {e}")

# Check if user is authenticated
def is_authenticated():
    access_token = session.get('access_token')
    if not access_token:
        raise Exception("User not authenticated: No access token found.")
    return True

# Decorator to require authentication
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            is_authenticated()
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Authentication error: {e}")
            return redirect(url_for('login'))
    return decorated_function

# Login page, redirects to auth.eagleeeyenetworks.com for authorization.
def login():
    try:
        code = request.args.get('code')
        if code:
            # Exchange authorization code for tokens
            auth_response = auth_een(code)
            if auth_response and auth_response.status_code == 200:
                auth_response_data = json.loads(auth_response.text)
                access_token = auth_response_data.get('access_token')
                refresh_token = auth_response_data.get('refresh_token')
                base_url = auth_response_data.get('httpsBaseUrl', {}).get('hostname')

                if not access_token:
                    raise Exception("Missing access token in the authentication response.")

                # Store tokens and base URL in session
                session['access_token'] = access_token
                session['refresh_token'] = refresh_token
                session['base_url'] = base_url
                session.permanent = True

                return redirect(url_for('index'))
            else:
                error_message = auth_response.text if auth_response else "No response from authentication server."
                raise Exception(f"Authentication failed: {error_message}")

        # Redirect to the Eagle Eye Networks authorization URL
        request_auth_url = "https://auth.eagleeyenetworks.com/oauth2/authorize"
        params = {
            "client_id": os.getenv('CLIENT_ID'),
            "response_type": "code",
            "scope": "vms.all",
            "redirect_uri": f"http://{os.getenv('FLASK_RUN_HOST')}:{os.getenv('FLASK_RUN_PORT')}/login"
        }
        request_auth_url += '?' + urllib.parse.urlencode(params)
        return render_template('login.html', auth_url=request_auth_url)
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return render_template('error.html', error=str(e))

# Logout and clear session
def logout():
    try:
        session.clear()
        return redirect(url_for('login'))
    except Exception as e:
        current_app.logger.error(f"Error during logout: {e}")
        raise Exception(f"Error during logout: {e}")

# Refresh access token
def refresh_access_token():
    try:
        refresh_token = session.get('refresh_token')
        if not refresh_token:
            raise Exception("No refresh token found in session.")

        auth_response = auth_een(refresh_token, type="refresh")
        if auth_response and auth_response.status_code == 200:
            auth_response_data = json.loads(auth_response.text)
            session['access_token'] = auth_response_data.get('access_token')
            session['refresh_token'] = auth_response_data.get('refresh_token')
            session['base_url'] = auth_response_data.get('httpsBaseUrl', {}).get('hostname')
            return True
        else:
            error_message = auth_response.text if auth_response else "No response from authentication server."
            raise Exception(f"Failed to refresh access token: {error_message}")
    except Exception as e:
        current_app.logger.error(f"Access token refresh error: {e}")
        return False