from app import app
import os
import json
import urllib.parse

from functools import wraps
from een import (
    EENClient,
    TokenStorage,
    AuthenticationError
)
from flask import (
    request, render_template, session,
    redirect, url_for, jsonify
)
from dotenv import load_dotenv

load_dotenv()


class FlaskSessionStore(TokenStorage):
    def get(self, key):
        return session.get(key)

    def set(self, key, value):
        session[key] = value
        session.modified = True

    def __contains__(self, key):
        return key in session


# Load the API Client
token_store = FlaskSessionStore()
redirect_uri = "http://{host}:{port}".format(
    host=os.getenv('FLASK_RUN_HOST'),
    port=os.getenv('FLASK_RUN_PORT')
)

client = EENClient(
    os.getenv('CLIENT_ID'),
    os.getenv('CLIENT_SECRET'),
    redirect_uri,
    token_store
)


# Get the unquoted argument
def get_unquoted_arg(arg_name):
    value = request.args.get(arg_name)
    return urllib.parse.unquote(value) if value else None


# Grabs the WebRTC, HLS, and Multipart URLs for the view function
# and places them in a dictionary
def label_feeds(results, device_id):
    feeds = {}
    for result in results:
        if result['deviceId'] == device_id:
            feeds[result['type']] = result
    return feeds


# Check if the user is authenticated
def is_authenticated():
    return session.get('access_token') is not None


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# PTZ Routes
# This route will control the PTZ of the selected camera
@app.route('/ptz/<camera_id>', methods=['POST'])
@auth_required
def ptz(camera_id):
    content_type = request.headers.get('Content-Type')
    if content_type != 'application/json':
        return "Invalid Content-Type", 400
    try:
        json_r = request.json
        response = client.move_to(json_r, camera_id)
        print(f"PTZ Request for Camera {camera_id}: {json_r}")
        print(f"Response: {response}")
        return jsonify({
            "status": "success"
        }), 200
    except Exception as e:
        print(f"PTZ request failed: {e}")
        return jsonify({
            "status": "fail"
        }), 500


# Refresh Token
# This route will refresh the access token
@app.route('/refresh_token', methods=['POST'])
@auth_required
def refresh_token():
    print('Viewing Tokens')
    print(f"Access Token: {session.get('access_token')}")
    print(f"Refresh Token: {session.get('refresh_token')}")
    print(f"Base URL: {session.get('base_url')}")
    print("Viweing Tokenm Store")
    print(f"Token Store: {token_store.get('access_token')}")
    print(f"Token Store: {token_store.get('refresh_token')}")
    print(f"Token Store: {token_store.get('base_url')}")
    try:
        client.refresh_access_token()
    except Exception as e:
        print(f"Failed to refresh token: {e}")
        return jsonify({
            "status": "fail"
        }), 500

    print("New Token Store")
    print(f"Access Store: {token_store.get('access_token')}")
    print(f"Refresh Store: {token_store.get('refresh_token')}")
    print(f"Base Store: {token_store.get('base_url')}")
    return jsonify({
        "status": "success"
    }), 200


# Play Audio
# This route plays audio to the selected camera
@app.route('/talkdown/<camera_id>', methods=['POST'])
@auth_required
def play_audio(camera_id):
    # Get audioPushHttpsUrl from the POST request
    data = request.get_json()
    audio_push_url = data.get('audioPushHttpsUrl')
    if not audio_push_url:
        return jsonify({
            "status": "fail",
            "message": "audioPushHttpsUrl is required"
        }), 400
    print('Recieved Audio Push URL: '+audio_push_url)
    try:
        response = client.play_audio(camera_id, audio_push_url)
    except Exception as e:
        print(f"Audio Push request failed: {e}")
        return jsonify({
            "status": "fail"
        }), 500
    if response:
        return jsonify({
            "status": "success"
        }), 200
    else:
        return jsonify({
            "status": "fail"
        }), 500


# Live View
# This page will display high res live view of a selected camera.
@app.route('/view/<camera_id>')
@auth_required
def view(camera_id):
    media = {
        'access_token': session.get('access_token'),
        'base_url': session.get('base_url')
    }

    print('Pulling Feeds and Camera Info')
    try:
        response = client.get_camera(camera_id, include="capabilities")
        camera = json.loads(response)
    except Exception as e:
        print(f"Failed to get camera info: {e}")

    try:
        response = client.list_feeds(
            camera_id,
            include="multipartUrl,hlsUrl,webRtcUrl")
        r_json = json.loads(response)
        results = r_json['results']
        print(f"Response: {json.dumps(results)}")
    except Exception as e:
        print(f"API Call failed: {e}")

    feeds = label_feeds(results, camera_id)
    feeds['capabilities'] = camera['capabilities']
    print(f"Feeds:\n{json.dumps(feeds)}")

    try:
        return render_template(
            'view.html',
            camera=camera,
            media=media,
            results=feeds)
    except Exception as e:
        print(f"Failed to render live view: {e}")


# Index Page
# This page will display a list of cameras for the user to select from.
# If the user is not logged in, they will be redirected to the login page.
@app.route('/', methods=['GET', 'POST'])
def index():
    code = request.args.get('code')
    if code:
        return redirect(url_for('login') + '?code=' + code)
    if not is_authenticated():
        return redirect(url_for('login'))

    media = {
        'access_token': session.get('access_token'),
        'base_url': session.get('base_url')
    }

    print('Pulling Camera List')
    try:
        cam_response = json.loads(
            client.list_cameras(include="capabilities"))
        feed_response = json.loads(
            client.list_feeds(type="preview", include="multipartUrl"))
        cam_results = cam_response['results']
        feed_results = feed_response['results']
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Failed to get cameras: {e}")
        return render_template('index.html')

    camera_dict = {camera['id']: camera for camera in cam_results}
    for feed in feed_results:
        camera_id = feed['deviceId']
        if camera_id in camera_dict:
            cam = camera_dict[camera_id]
            if 'multipartUrl' not in cam:
                cam['multipartUrl'] = feed['multipartUrl']

    cameras = list(camera_dict.values())

    try:
        return render_template(
            'index.html',
            cameras=cameras[0:12],
            media=media)
    except Exception as e:
        print(f"Failed render template: {e}")
        return render_template('index.html')


# Login Page
# This page will redirect the user to the Eagle Eye Networks OAuth login page.
# Review the OAuth Python example for more information.
@app.route('/login')
def login():
    code = request.args.get('code')

    if (code):
        print("Attempting Code Auth")
        auth_response = client.auth_een(code)
        if auth_response.status_code == 200:
            auth_response = json.loads(auth_response.text)

            # Store the access_token, refresh_token,
            # and base_url in the session
            session['access_token'] = auth_response['access_token']
            session['refresh_token'] = auth_response['refresh_token']
            session['base_url'] = auth_response['httpsBaseUrl']['hostname']
            session.permanent = True

            return redirect(url_for('index'))
        else:
            print("Code Auth failed. {status_code} Response: {text}".format(
                status_code=auth_response.status_code,
                text=auth_response.text
            ))

    requestAuthUrl = client.get_auth_url()
    print("Redirecting to: " + requestAuthUrl)

    return render_template('login.html', auth_url=requestAuthUrl)


# Logout Page
# This page will clear the session and redirect the user to the login page.
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
