from app import app
from app.errors import AuthenticationError
import os
import json
import requests
import urllib.parse
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    request, render_template, session,
    redirect, url_for
)
from dotenv import load_dotenv

load_dotenv()


# OAuth Authentication
def auth_een(token, type="code"):
    url = "https://auth.eagleeyenetworks.com/oauth2/token"
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded"
    }
    if type == "code":
        data = {
            "grant_type": "authorization_code",
            "scope": "vms.all",
            "code": token,
            "redirect_uri": "http://{host}:{port}".format(
                host=os.getenv('FLASK_RUN_HOST'),
                port=os.getenv('FLASK_RUN_PORT')
            )
        }
    elif type == "refresh":
        data = {
            "grant_type": "refresh_token",
            "scope": "vms.all",
            "refresh_token": token
        }
    else:
        raise Exception("Invalid auth type")
    response = requests.post(
        url,
        auth=(
            os.getenv('CLIENT_ID'),
            os.getenv('CLIENT_SECRET')
        ),
        data=data,
        headers=headers
    )
    return response


# Handle Response
# This function will handle the response from an API call
# while also handling authentication errors.
def handle_response(
        response,
        original_request_func,
        endpoint,
        retry_count=0,
        max_retries=1,
        *args, **kwargs):
    if response.ok:
        if kwargs.get('stream'):
            return response
        return response.text
    elif response.status_code == 401 and retry_count < max_retries:
        # Refresh the access token
        print("Auth failed. Refreshing Access Token.")
        refresh_token = session.get('refresh_token')
        if refresh_token:
            refresh_response = auth_een(refresh_token, type="refresh")
            if refresh_response.status_code == 200:
                # print(auth_response.text)
                auth_response = json.loads(refresh_response.text)

                # Store the tokens in the session
                session['access_token'] = auth_response['access_token']
                session['refresh_token'] = auth_response['refresh_token']
                session['base_url'] = auth_response['httpsBaseUrl']['hostname']

                # Retry the original request
                retry_count += 1
                return original_request_func(
                    endpoint,
                    retry_count=retry_count,
                    *args, **kwargs
                )
            else:
                print("Refresh Failed: {code} {text}".format(
                    code=refresh_response.status_code,
                    text=refresh_response.text
                ))
                raise AuthenticationError
        else:
            print("No refresh token found")
            raise AuthenticationError
    else:
        raise Exception(f"{response.status_code} Response: {response.text}")


# API Call
# This function will make an API call to the Eagle Eye Networks API
def api_call(
        endpoint,
        method='GET',
        params=None,
        data=None,
        headers=None,
        retry_count=0,
        stream=False):
    # print(f"Making API call to {endpoint}")
    # print(f"Params: {params}")
    access_token = session.get('access_token')
    base_url = session.get('base_url')

    url = f"https://{base_url}/api/v3.0{endpoint}"
    if params:
        url += '?' + urllib.parse.urlencode(params)

    print(f"request: {url}")

    if not headers:
        headers = {}
    headers['Authorization'] = f'Bearer {access_token}'

    if method == 'GET':
        try:
            response = requests.get(url, headers=headers, stream=stream)
        except Exception as e:
            print(f"Failed to make request: {e}")
            raise e
    elif method == 'POST':
        print(f"Payload: {data}")
        response = requests.post(url, headers=headers, data=data)

    return handle_response(
        response,
        api_call,
        endpoint,
        method=method,
        params=params,
        data=data,
        headers=headers,
        retry_count=retry_count,
        stream=stream
    )


# Get the current time and the time exactly 7 days ago
# Timestamps must be included with deep search requests
def get_timestamps():
    # Create a search window of 7 days
    current_time = datetime.utcnow()
    seven_days_ago = current_time - timedelta(days=7)

    # Convert both times to ISO 8601 format with millisecond precision
    # Example: 2021-07-01T00:00:00.000+00:00
    # Eagle Eye Networks API requires timestamps to be in this format
    current_time_iso = "{iso}+00:00".format(
        iso=current_time.isoformat(timespec='milliseconds'))
    seven_days_ago_iso = "{iso}+00:00".format(
        iso=seven_days_ago.isoformat(timespec='milliseconds'))

    return current_time_iso, seven_days_ago_iso


# Get a list of cameras
# For more info see:
# https://developer.eagleeyenetworks.com/reference/listcameras
def get_cameras(camera_id=None):
    endpoint = "/cameras"

    if camera_id:
        endpoint += f"/{camera_id}"

    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    return api_call(
        endpoint,
        headers=headers
    )


# Get a list of feeds
# For more info see:
# https://developer.eagleeyenetworks.com/reference/listfeeds
def get_feeds(device_id=None, type="preview", include="multipartUrl"):
    endpoint = "/feeds"

    params = {
        "include": include,
        "type": type
    }
    if device_id:
        params['deviceId'] = device_id
    return api_call(endpoint, params=params)


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


# Clips View
# This page will display a list of video clips for a selected camera.
@app.route('/view/<camera_id>')
@auth_required
def view(camera_id):
    media = {
        'access_token': session.get('access_token'),
        'base_url': session.get('base_url')
    }

    print('Pulling Feeds and Camera Info')
    try:
        response = get_cameras(camera_id)
        camera = json.loads(response)
    except Exception as e:
        print(f"Failed to get camera info: {e}")

    try:
        response = get_feeds(
            camera_id, type="main", include="multipartUrl,hlsUrl")
        r_json = json.loads(response)
        results = r_json['results']
        feeds = results[0]
        print(f"Feeds: {results}")
    except Exception as e:
        print(f"API Call failed: {e}")

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
        cam_response = json.loads(get_cameras())
        feed_response = json.loads(get_feeds())
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
        auth_response = auth_een(code)
        if auth_response.status_code == 200:
            # print(auth_response.text)
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

    requestAuthUrl = "https://auth.eagleeyenetworks.com/oauth2/authorize"
    params = {
        "client_id": os.getenv('CLIENT_ID'),
        "response_type": "code",
        "scope": "vms.all",
        "redirect_uri": "http://{host}:{port}".format(
            host=os.getenv('FLASK_RUN_HOST'),
            port=os.getenv('FLASK_RUN_PORT')
        )
    }
    requestAuthUrl += '?' + urllib.parse.urlencode(params)

    return render_template('login.html', auth_url=requestAuthUrl)


# Logout Page
# This page will clear the session and redirect the user to the login page.
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
