from app import app
from app.forms import ExportForm
from app.exceptions import AuthenticationError
import os
import json
import requests
import urllib.parse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from functools import wraps
from flask import (
    request, render_template, session,
    redirect, url_for, Response,
    stream_with_context
)
from dotenv import load_dotenv

load_dotenv()


# OAuth Code Authentication
def getTokens(code):
    url = "https://auth.eagleeyenetworks.com/oauth2/token"
    params = {
        "grant_type": "authorization_code",
        "scope": "vms.all",
        "code": code,
        "redirect_uri": "http://{host}:{port}".format(
            host=os.getenv('FLASK_RUN_HOST'),
            port=os.getenv('FLASK_RUN_PORT')
        )
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


# Get the unquoted argument
def get_unquoted_arg(arg_name):
    value = request.args.get(arg_name)
    return urllib.parse.unquote(value) if value else None


# Format timestamps to ISO 8601 format
def format_timestamp(timestamp_str, user_timezone='UTC'):
    if not timestamp_str:
        return None
    try:
        local_dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M')
        local_tz = ZoneInfo(user_timezone)
        local_dt = local_dt.replace(tzinfo=local_tz)
        utc_dt = local_dt.astimezone(ZoneInfo('UTC'))
        # Format with microsecond precision and truncate to milliseconds
        return utc_dt.isoformat(timespec='milliseconds')
    except ValueError:
        return None


# Get the current time and the time exactly 7 days ago
def get_timestamps():
    # Create a search window of 7 days
    current_time = datetime.now(timezone.utc)
    seven_days_ago = current_time - timedelta(days=7)

    # Convert both times to ISO 8601 format with millisecond precision
    # Example: 2021-07-01T00:00:00.000+00:00
    # Eagle Eye Networks API requires timestamps to be in this format
    current_time_iso = current_time.isoformat(timespec='milliseconds')
    seven_days_ago_iso = seven_days_ago.isoformat(timespec='milliseconds')

    return current_time_iso, seven_days_ago_iso


# Handle Response
# This function will handle the response from an API call
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
    base_url = session.get('baseUrl')

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


# Get a list of availible video clips
# For more info see:
# https://developer.eagleeyenetworks.com/reference/listmedia
def get_media(
        cameraId,
        start=None,
        end=None,
        type='preview',
        mediaType='video',
        page_token=None
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
        "include": "multipartUrl,mp4Url",
        "pageSize": "24"
    }

    if end:
        params['endTimestamp__lte'] = end
    if page_token:
        params['pageToken'] = page_token

    return api_call(endpoint, params=params, headers=headers)


# Export video clip
def export_clip(
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
        "period": period,
        "autoDelete": False
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
def get_files(
        file_id=None,
        include="size,createTimestamp",
        directory=None,
        mime_type=None):

    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    if file_id:
        endpoint = f"/files/{file_id}"
        params = {
            "include": include
        }
    else:
        endpoint = "/files"
        params = {k: v for k, v in {
            "include": include,
            "directory": directory,
            "mimeType": mime_type
        }.items() if v is not None}

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
    response = api_call(endpoint, stream=True)

    if isinstance(response, str):
        response = response.encode('utf-8')

    # Yield chunks from the streamed response
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            yield chunk


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


# Download File
# This page will initiate a download.
@app.route('/download/<file_id>')
@auth_required
def download(file_id):
    try:
        # Fetch file metadata
        file_info = get_files(file_id)
        file_info = json.loads(file_info)

        response = Response(
            stream_with_context(downloadFile(file_id)),
            mimetype=file_info['mimeType']
        )
        disposition = f"attachment; filename={file_info['name']}"
        response.headers['Content-Disposition'] = disposition

        return response
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Download failed: {e}")
        return "Download failed", 500


# View Files
# This page will display a list of files that the user can download.
@app.route('/files/', defaults={'directory': ''})
@app.route('/files/<path:directory>')
@auth_required
def view_files(directory):
    print('Pulling Files')
    try:

        response = get_files(directory=f"/{urllib.parse.unquote(directory)}")
        results = json.loads(response)['results']
        print(f"Files: {json.dumps(results)}")
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"API Call failed: {e}")

    # Create breadcrumbs for the directory path
    current_path = directory
    if current_path == '/':
        current_path = ''
        breadcrumbs = []
    else:
        breadcrumbs = [crumb for crumb in current_path.split('/') if crumb]
    dir_info = {
        "current": current_path,
        "breadcrumbs": breadcrumbs
    }

    try:
        return render_template(
            'files.html',
            dir_info=dir_info,
            results=results
        )
    except Exception as e:
        print(f"Failed to render files view: {e}")


# Preview Export View
# This page will display a video player for a selected video clip.
@app.route('/preview/<camera_id>', methods=['GET', 'POST'])
@auth_required
def preview(camera_id):
    form = ExportForm()
    start = request.args.get('start')
    end = request.args.get('end')

    if form.validate_on_submit():
        print('Exporting Clip')
        try:
            context = {k: v for k, v in {
                'directory': form.directory.data,
                'notes': form.notes.data,
                'tags': form.tags.data
            }.items() if v is not None}
            export_response = export_clip(
                camera_id,
                form.name.data,
                start,
                end,
                **context
            )
            print(export_response)
            redirect(
                url_for('preview', camera_id=camera_id, start=start, end=end))
        except AuthenticationError:
            return redirect(url_for('login'))
        except Exception as e:
            print(f"API Call failed: {e}")

    media = {
        'access_token': session.get('access_token'),
        'base_url': session.get('baseUrl')
    }

    if start and end:
        print('Pulling Clip and Camera Info')
        try:
            response = get_cameras(camera_id)
            camera = json.loads(response)
        except Exception as e:
            print(f"Failed to get camera info: {e}")

        try:
            response = get_media(camera_id, start, end, "main")
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
@auth_required
def view_clips(camera_id):
    media = {
        'access_token': session.get('access_token'),
        'base_url': session.get('baseUrl')
    }

    print('Pulling Clips and Camera Info')
    try:
        response = get_cameras(camera_id)
        camera = json.loads(response)
    except Exception as e:
        print(f"Failed to get camera info: {e}")

    # Collect the query parameters from the request
    start = get_unquoted_arg('start')
    end = get_unquoted_arg('end')
    timezone = get_unquoted_arg('timezone') or 'UTC'
    page_token = request.args.get('page_token')

    context = {k: v for k, v in {
        'start': format_timestamp(start, timezone),
        'end': format_timestamp(end, timezone),
        'type': 'main',
        'page_token': page_token
    }.items() if v is not None}

    try:
        response = get_media(camera_id, **context)
        r_json = json.loads(response)
        results = r_json['results']
        next_page = r_json['nextPageToken']
        prev_page = r_json['prevPageToken']
        for i, clip in enumerate(results):
            url = "https://{}/api/v3.0/media/recordedImage.jpeg".format(
                session.get('baseUrl')
            )
            params = {
                "timestamp": clip['startTimestamp'],
                "type": "main",
                "deviceId": camera_id
            }
            url += '?' + urllib.parse.urlencode(params)
            clip['imageUrl'] = url
            clip['id'] = f"camclip{i}"
    except Exception as e:
        print(f"API Call failed: {e}")

    try:
        context = {k: v for k, v in {
            'media': media,
            'camera': camera,
            'results': results,
            'start': start,
            'end': end,
            'next_page': next_page,
            'prev_page': prev_page
        }.items() if v is not None}
        return render_template('clips.html', **context)
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

        camera_dict = {camera['id']: camera for camera in cam_results}
        for feed in feed_results:
            camera_id = feed['deviceId']
            if camera_id in camera_dict:
                cam = camera_dict[camera_id]
                if 'multipartUrl' not in cam:
                    cam['multipartUrl'] = feed['multipartUrl']

        cameras = list(camera_dict.values())

        return render_template(
            'index.html',
            cameras=cameras[0:12],
            media=media)
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Failed to get cameras: {e}")
        return render_template('index.html')


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
            session.permanent = True

            return redirect(url_for('index'))

        else:
            print("Code Auth failed. Response: "+auth_response)

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
