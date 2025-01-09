from app import app
from app.forms import ExportForm
import os
import json
import urllib.parse
from functools import wraps

from app.een_client import (
    EENClient, AuthenticationError,
    format_timestamp
)
from flask import (
    request, render_template, session,
    redirect, url_for, Response,
    stream_with_context
)
from dotenv import load_dotenv

load_dotenv()


# Initialize the EENClient
client = EENClient(
    os.getenv('CLIENT_ID'),
    os.getenv('CLIENT_SECRET')
)


# Get the unquoted argument
def get_unquoted_arg(arg_name):
    value = request.args.get(arg_name)
    return urllib.parse.unquote(value) if value else None


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
        file_info = client.get_files(file_id)
        file_info = json.loads(file_info)

        response = Response(
            stream_with_context(client.download_file(file_id)),
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

        response = client.get_files(
            directory=f"/{urllib.parse.unquote(directory)}")
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
            export_response = client.export_clip(
                camera_id,
                form.name.data,
                start,
                end,
                **context
            )
            print(export_response)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return a JSON response for AJAX requests
                return json.dumps({'success': True}), 200, {
                    'ContentType': 'application/json'
                }
            else:
                redirect(url_for(
                    'preview', camera_id=camera_id, start=start, end=end))
        except AuthenticationError:
            return redirect(url_for('login'))
        except Exception as e:
            print(f"API Call failed: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return json.dumps({
                    'success': False,
                    'message': 'Error exporting clip.'
                }), 500, {'ContentType': 'application/json'}
            else:
                return "API Call failed", 500

    media = {
        'access_token': session.get('access_token'),
        'base_url': session.get('base_url')
    }

    if start and end:
        print('Pulling Clip and Camera Info')
        try:
            response = client.get_cameras(camera_id)
            camera = json.loads(response)
        except Exception as e:
            print(f"Failed to get camera info: {e}")

        try:
            response = client.get_media(camera_id, start, end, "main")
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
        'base_url': session.get('base_url')
    }

    print('Pulling Clips and Camera Info')
    try:
        response = client.get_cameras(camera_id)
        camera = json.loads(response)
    except Exception as e:
        print(f"Failed to get camera info: {e}")

    # Collect the query parameters from the request
    start = get_unquoted_arg('start')
    end = get_unquoted_arg('end')
    user_timezone = get_unquoted_arg('timezone') or 'UTC'
    page_token = request.args.get('page_token')

    context = {k: v for k, v in {
        'start': format_timestamp(start, user_timezone),
        'end': format_timestamp(end, user_timezone),
        'type': 'main',
        'page_token': page_token
    }.items() if v is not None}

    try:
        response = client.get_media(camera_id, **context)
        r_json = json.loads(response)
        results = r_json['results']
        next_page = r_json['nextPageToken']
        prev_page = r_json['prevPageToken']
        for i, clip in enumerate(results):
            url = "https://{}/api/v3.0/media/recordedImage.jpeg".format(
                session.get('base_url')
            )
            params = {
                "timestamp__gte": clip['startTimestamp'],
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
        cam_response = json.loads(client.get_cameras())
        feed_response = json.loads(client.get_feeds())
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
    print(f"Cameras: {json.dumps(cameras)}")

    try:
        return render_template(
            'index.html',
            results=cameras[0:12],
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

    return render_template('login.html', auth_url=requestAuthUrl)


# Logout Page
# This page will clear the session and redirect the user to the login page.
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
