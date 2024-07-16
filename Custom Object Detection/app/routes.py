from app import app
from app.errors import AuthenticationError
import os
import cv2
import json
import requests
import urllib.parse
from datetime import datetime, timedelta
from ultralytics import YOLO
import numpy as np
from functools import wraps
from flask import (
    request, render_template, session,
    redirect, url_for, Response
)
from dotenv import load_dotenv

load_dotenv()


# OAuth Authentication
def code_auth(code):
    url = "https://auth.eagleeyenetworks.com/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "scope": "vms.all",
        "code": code,
        "redirect_uri": "http://{host}:{port}".format(
            host=os.getenv('FLASK_RUN_HOST'),
            port=os.getenv('FLASK_RUN_PORT')
        )
    }
    response = requests.post(
        url,
        auth=(
            os.getenv('CLIENT_ID'),
            os.getenv('CLIENT_SECRET')
        ),
        data=data
    )
    return response


# OAuth Refresh Token Authentication
def refresh_access(refresh_token):
    url = "https://auth.eagleeyenetworks.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "scope": "vms.all",
        "refresh_token": refresh_token
    }
    response = requests.post(
        url,
        auth=(
            os.getenv('CLIENT_ID'),
            os.getenv('CLIENT_SECRET')
        ),
        data=data
    )
    return response


# Handle Response
# This function will handle the response from an API call
# while also handling authentication errors.
def handle_response(
        response,
        original_request_func,
        retry_count=0,
        max_retries=1,
        *args, **kwargs):
    if response.ok:
        return response.text
    elif response.status_code == 401 and retry_count < max_retries:
        # Refresh the access token
        print("Auth failed. Refreshing Access Token.")
        refresh_token = session.get('refresh_token')
        if refresh_token:
            refresh_response = refresh_access(refresh_token)
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
                    retry_count=retry_count, *args, **kwargs)
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
        retry_count=0):
    # print(f"Making API call to {endpoint}")
    # print(f"Params: {params}")
    access_token = session.get('access_token')
    base_url = session.get('base_url')

    url = f"https://{base_url}/api/v3.0{endpoint}"
    if params:
        url += '?' + urllib.parse.urlencode(params)

    print(f"URL: {url}")

    if not headers:
        headers = {}
    headers['Authorization'] = f'Bearer {access_token}'

    if method == 'GET':
        try:
            response = requests.get(url, headers=headers)
        except Exception as e:
            print(f"Failed to make request: {e}")
    elif method == 'POST':
        print(f"Payload: {data}")
        response = requests.post(url, headers=headers, data=data)

    return handle_response(
        response,
        api_call,
        retry_count=retry_count,
        url=url,
        method=method,
        data=data,
        headers=headers
    )


# Get the list of cameras
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


# Get the list of camera feeds
def get_feeds(device_id=None, type="preview", include="multipartUrl"):
    endpoint = "/feeds"

    params = {
        "include": include,
        "type": type
    }
    if device_id:
        params['deviceId'] = device_id
    return api_call(endpoint, params=params)


# Convert Yolo Box to cv2 Rectangle
def yolo_to_cv2(xywh, orig_shape):
    xywh = [
        float(xywh[0])*orig_shape[0],
        float(xywh[1])*orig_shape[1],
        float(xywh[2])*orig_shape[0],
        float(xywh[3])*orig_shape[1]
    ]
    coord = []
    coord.append(int(xywh[0] - xywh[2]/2))
    coord.append(int(xywh[1] - xywh[3]/2))
    coord.append(int(xywh[0] + xywh[2]/2))
    coord.append(int(xywh[1] + xywh[3]/2))
    return coord


# Run Object Detection
def run_detection(feed_url, access_token):
    print("Running Object Detection")
    auth_url = f"{feed_url}&access_token={access_token}"
    print(f"Feed URL: {auth_url}")
    try:
        model = YOLO('yolov8s.pt')
        results = model(source=auth_url, show=False, conf=0.40, stream=True)

        for i in results:
            frame = i.orig_img
            if len(i.boxes.cls) > 0:
                for n, detection in enumerate(i.boxes.cls):
                    coord = [
                        int(i.boxes.xyxy[n][0]),
                        int(i.boxes.xyxy[n][1]),
                        int(i.boxes.xyxy[n][2]),
                        int(i.boxes.xyxy[n][3])
                    ]
                    label = i.names[int(detection)]
                    cv2.rectangle(
                        frame,
                        ((coord[0]), coord[1]),
                        (coord[2], coord[3]),
                        (218, 145, 0),
                        2)
                    cv2.putText(
                        frame,
                        f"{label} {i.boxes.conf[n]:.2f}",
                        (coord[0], coord[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (172, 103, 0),
                        2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    except Exception as e:
        print(f"Error running object detection: {e}")
        return None


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


# Video Feed
# This page will display the video feed from the selected camera with
# object detection overlay.
@app.route('/video_feed/<camera_id>')
@auth_required
def video_feed(camera_id):
    try:
        feed_info = json.loads(get_feeds(
            device_id=camera_id, include="rtspUrl"))
        return Response(
            run_detection(
                feed_info['results'][0]['rtspUrl'],
                session.get('access_token')
            ),
            mimetype='multipart/x-mixed-replace; boundary=frame')
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Error getting feed: {e}")
        return "Error", 500


# Detect Page
# This page will display the object detection overlay on the video feed.
@app.route('/detect/<camera_id>')
@auth_required
def detect(camera_id):
    try:
        cam_info = json.loads(get_cameras(camera_id=camera_id))
        feed_info = json.loads(
            get_feeds(device_id=camera_id, include="rtspUrl"))

        return render_template(
            'detect.html',
            camera=cam_info)
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Error getting feed: {e}")
        return render_template('detect.html')


# Index Page
# This page will display a list of cameras for the user to select from.
# If the user is not logged in, they will be redirected to the login page.
@app.route('/')
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

    try:
        cam_response = json.loads(get_cameras())
        feed_response = json.loads(get_feeds())
        cam_results = cam_response['results']
        feed_results = feed_response['results']

        camera_dict = {camera['id']: camera for camera in cam_results}
        for feed in feed_results:
            camera_id = feed['deviceId']
            if camera_id in camera_dict:
                if 'multipartUrl' not in camera_dict[camera_id]:
                    camera_dict[camera_id]['multipartUrl'] = feed['multipartUrl']

        cameras = list(camera_dict.values())

        return render_template(
            'index.html',
            cameras=cameras[0:12],
            media=media)
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Error getting cameras: {e}")
        return render_template('index.html')


# Login Page
# This page will redirect the user to the Eagle Eye Networks OAuth login page.
# Review the OAuth Python example for more information.
@app.route('/login')
def login():
    code = request.args.get('code')

    if (code):
        print("Attempting Code Auth")
        auth_response = code_auth(code)
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
