from app import app
from app.forms import ExportForm
from app.exceptions import AuthenticationError
import os
from io import BytesIO
import json
import requests
import urllib.parse
from datetime import datetime, timedelta
from flask import (
    request, render_template, session,
    redirect, url_for, send_file
)
from dotenv import load_dotenv

load_dotenv()

# Hostname and port for the HTTP server
hostName = os.getenv('FLASK_RUN_HOST')
port = os.getenv('FLASK_RUN_PORT')


# OAuth Code Authentication
def getTokens(code):
    url = "https://auth.eagleeyenetworks.com/oauth2/token?grant_type=authorization_code&scope=vms.all&code="+code+"&redirect_uri=http://"+hostName + ":" + str(port)
    response = requests.post(
        url,
        auth=(
            os.getenv('CLIENT_ID'),
            os.getenv('CLIENT_SECRET')
        )
    )
    return response
    try:
        json_object = json.loads(response.text)
        return json_object
    except ValueError:
        return None


# OAuth Refresh Token Authentication
def refresh_access(refresh_token):
    url = "https://auth.eagleeyenetworks.com/oauth2/token"
    params = {
        "grant_type": "refresh_token",
        "scope": "vms.all",
        "refresh_token": refresh_token
    }
    url += '?' + urllib.parse.urlencode(params)
    response = requests.post(
        url,
        auth=(
            os.getenv('CLIENT_ID'),
            os.getenv('CLIENT_SECRET')
        )
    )
    return response


# Get the current time and the time exactly 7 days ago
def get_timestamps():
    # Create a search window of 7 days
    current_time = datetime.utcnow()
    seven_days_ago = current_time - timedelta(days=7)

    # Convert both times to ISO 8601 format with millisecond precision
    # Example: 2021-07-01T00:00:00.000+00:00
    # Eagle Eye Networks API requires timestamps to be in this format
    current_time_iso = current_time.isoformat(timespec='milliseconds') + '+00:00'
    seven_days_ago_iso = seven_days_ago.isoformat(timespec='milliseconds') + '+00:00'

    return current_time_iso, seven_days_ago_iso


# Handle Response
# This function will handle the response from an API call
def handle_response(
        response,
        original_request_func,
        retry_count=0,
        max_retries=1,
        *args, **kwargs):
    if response.status_code == 200 or response.status_code == 201:
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
                session['baseUrl'] = auth_response['httpsBaseUrl']['hostname']

                # Retry the original request
                retry_count += 1
                return original_request_func(retry_count=retry_count, *args, **kwargs)
            else:
                print(f"Refresh Failed: {refresh_response.status_code} {refresh_response.text}")
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
    base_url = session.get('baseUrl')

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


# Get a list of cameras
# For more info see:
# https://developer.eagleeyenetworks.com/reference/listcameras
def getCameras():
    endpoint = "/cameras"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    return api_call(endpoint, headers=headers)


# Get information about a camera
# For more info see:
# https://developer.eagleeyenetworks.com/reference/getcamera
def getCameraInfo(cameraId):
    endpoint = f"/cameras/{cameraId}"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    return api_call(endpoint, headers=headers)


# Get a list of availible video clips
# For more info see:
# https://developer.eagleeyenetworks.com/reference/listmedia
def getMedia(
        cameraId,
        start=None,
        end=None,
        type='preview',
        mediaType='video'
        ):
    endpoint = "/media"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    # Set the query parameters for the media request
    if not start:
        current, week_ago = get_timestamps()
        start = week_ago

    params = {
        "deviceId": cameraId,
        "type": type,
        "mediaType": mediaType,
        "startTimestamp__gte": start,
        "include": "multipartUrl,mp4Url"
    }

    if end:
        params['endTimestamp__lte'] = end

    return api_call(endpoint, params=params, headers=headers)


# Export video clip
def exportClip(
        camera_id,
        name,
        start, end,
        type="video",
        directory='/',
        notes=None,
        tags=None
        ):
    endpoint = "/exports"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    info = {
        "name": name,
        "directory": directory,
    }
    if notes:
        info['notes'] = notes
    if tags:
        info['tags'] = tags
    period = {
        "startTimestamp": start,
        "endTimestamp": end
    }
    data = {
        "deviceId": camera_id,
        "type": type,
        "info": info,
        "period": period
    }

    api_call(endpoint, method='POST', data=json.dumps(data), headers=headers)


# Get a list of export jobs
def getExports():
    endpoint = "/exports"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    return api_call(endpoint, headers=headers)


# Get a list of files
def getFiles(file_id=None):
    if file_id:
        endpoint = f"/files/{file_id}"
    else:
        endpoint = "/files"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    params = {
        "include": "notes,size"
    }
    return api_call(endpoint, headers=headers, params=params)


# Get a list of video exports
def getDownloads():
    endpoint = "/downloads"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    return api_call(endpoint, headers=headers)


# Initiate a download
def downloadFile(file_id):
    endpoint = f"/files/{file_id}:download"
    return api_call(endpoint)


# View Downloads
# This page will display a list of video clips that the user can download.
@app.route('/downloads/<file_id>')
def download(file_id):
    accessToken = session.get('access_token')
    if not accessToken:
        return redirect(url_for('login'))

    print('Starting Download')
    try:
        file_info = getFiles(file_id)
        file_info = json.loads(file_info)

        file_content = downloadFile(file_id)

        # Create a BytesIO object to send as a file
        buffer = BytesIO()
        buffer.write(file_content)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            attachment_filename=file_info['name'],
            mimetype=file_info['mimeType']
        )
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Download failed: {e}")


# View Files
# This page will display a list of files that the user can download.
@app.route('/files')
def view_files():
    accessToken = session.get('access_token')
    if not accessToken:
        return redirect(url_for('login'))

    print('Pulling Files')
    try:
        response = getFiles()
        results = json.loads(response)['results']
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"API Call failed: {e}")

    try:
        return render_template(
            'files.html',
            files=results
        )
    except Exception as e:
        print(f"Failed to render files view: {e}")


# Preview Export View
# This page will display a video player for a selected video clip.
@app.route('/preview/<camera_id>', methods=['GET', 'POST'])
def preview(camera_id):
    form = ExportForm()
    accessToken = session.get('access_token')
    base_url = session.get('baseUrl')
    if not accessToken:
        return redirect(url_for('login'))

    start = request.args.get('start')
    end = request.args.get('end')

    if form.validate_on_submit():
        print('Exporting Clip')
        try:

            export_response = exportClip(
                camera_id,
                form.name.data,
                start,
                end,
                directory=form.directory.data,
                notes=form.notes.data,
                tags=form.tags.data
            )
            print(export_response)
            redirect(url_for('view_files'))
        except AuthenticationError:
            return redirect(url_for('login'))
        except Exception as e:
            print(f"API Call failed: {e}")

    media = {
        'access_token': accessToken,
        'base_url': base_url
    }

    if start and end:
        print('Pulling Clip and Camera Info')
        try:
            response = getCameraInfo(camera_id)
            camera = json.loads(response)
        except Exception as e:
            print(f"Failed to get camera info: {e}")

        try:
            response = getMedia(camera_id, start, end, "main")
            results = json.loads(response)['results']
            clip = results[0]

            return render_template(
                'preview.html',
                form=form,
                media=media,
                camera=camera,
                clip=clip)
        except Exception as e:
            print(f"Failed to get clip: {e}")
    else:
        return redirect(url_for('view_clips', camera_id=camera_id))


# Clips View
# This page will display a list of video clips for a selected camera.
@app.route('/clips/<camera_id>')
def view_clips(camera_id):
    accessToken = session.get('access_token')
    base_url = session.get('baseUrl')
    if not accessToken:
        return redirect(url_for('login'))
    media = {
        'access_token': accessToken,
        'base_url': base_url
    }

    print('Pulling Clips and Camera Info')
    try:
        response = getCameraInfo(camera_id)
        camera = json.loads(response)
    except Exception as e:
        print(f"Failed to get camera info: {e}")

    try:
        response = getMedia(camera_id)
        results = json.loads(response)['results']
    except Exception as e:
        print(f"API Call failed: {e}")

    try:
        return render_template(
            'clips.html',
            media=media,
            camera=camera,
            clips=results)
    except Exception as e:
        print(f"Failed to render clips view: {e}")


# Index Page
# This page will display a list of cameras for the user to select from.
# If the user is not logged in, they will be redirected to the login page.
@app.route('/', methods=['GET', 'POST'])
def index():
    code = request.args.get('code')
    if code:
        return redirect(url_for('login') + '?code=' + code)

    accessToken = session.get('access_token')
    if not accessToken:
        return redirect(url_for('login'))

    print('Pulling Camera List')
    try:
        response = getCameras()
        cameras = json.loads(response)['results']
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Failed to get cameras: {e}")

    return render_template('index.html', cameras=cameras)


# Login Page
# This page will redirect the user to the Eagle Eye Networks OAuth login page.
# Review the OAuth Python example for more information.
@app.route('/login')
def login():
    code = request.args.get('code')

    if (code):
        print("Attempting Code Auth")
        auth_response = getTokens(code)
        if auth_response.status_code != 200:
            print("Code Auth failed. Response: "+auth_response.text)
            return redirect(url_for('login'))
        if auth_response.status_code == 200:
            # print(auth_response.text)
            auth_response = json.loads(auth_response.text)

            # Store the access_token, refresh_token, and baseUrl in the session
            session['access_token'] = auth_response['access_token']
            session['refresh_token'] = auth_response['refresh_token']
            session['baseUrl'] = auth_response['httpsBaseUrl']['hostname']

            return redirect(url_for('index'))

        else:
            print("Code Auth failed. Response: "+auth_response)

    endpoint = "https://auth.eagleeyenetworks.com/oauth2/authorize"
    clientId = os.getenv('CLIENT_ID')
    requestAuthUrl = endpoint+"?client_id="+clientId+"&response_type=code&scope=vms.all&redirect_uri=http://"+hostName + ":" + str(port)

    return render_template('login.html', auth_url=requestAuthUrl)
