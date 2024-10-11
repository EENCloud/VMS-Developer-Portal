from app import app
from app.forms import TimeSelectForm
from app.schemas import (
    CreateEvent, CreatorDetailsData,
    FullFrameImageData, ObjectClassificationData,
    ObjectDetectionData, ObjectRegionmappingData)
import os
import cv2
import json
import urllib.parse
from pydantic import ValidationError

from functools import wraps
from app.een_client import (
    EENClient,
    AuthenticationError,
    format_timestamp,
    camel_to_title
)
from ultralytics import YOLO
import numpy as np
from flask import (
    request, render_template, session,
    redirect, url_for, jsonify
)
from dotenv import load_dotenv

load_dotenv()

# Load the API Client
client = EENClient(
    os.getenv('CLIENT_ID'),
    os.getenv('CLIENT_SECRET')
)

# Load the YOLO model.
model = YOLO('yolov8s.pt')


# Construct Detection Event
def construct_detection_event(
        camera_id, type, timestamp, box,
        img_url, confidence):
    """
    Construct a detection event object.

    Args:
        type (str): The type of detection.
        box (list): The bounding box coordinates.
        img_url (str): The URL of the image.
        timestamp (str): The timestamp of the detection.
        confidence (float): The confidence score of the detection.
    Returns:
        dict: The detection event object.
    """
    print(f"Constructing {type} Detection Event")
    camera_info = json.loads(client.get_cameras(camera_id))
    user_info = json.loads(client.current_user())

    if type == 'person':
        dataSchemas = [
            "een.fullFrameImageUrl.v1",
            "een.objectClassification.v1",
            "een.objectClassification.v1",
            "een.creatorDetails.v1",
        ]
        data = []
        data.append(FullFrameImageData(
            type="een.fullFrameImageUrl.v1",
            timestamp=timestamp,
            httpsUrl=img_url,
            feedType="main"
        ))
        data.append(ObjectClassificationData(
            type="een.objectClassification.v1",
            **{"class": "person"},
            confidence=confidence
        ))
        data.append(ObjectDetectionData(
            type="een.objectDetection.v1",
            timestamp=timestamp,
            boundingBox=box
        ))
        data.append(CreatorDetailsData(
            type="een.creatorDetails.v1",
            id=os.getenv('CREATOR_ID'),
            vendor=os.getenv('CREATOR_VENDOR'),
            application="Yolov8s"
        ))

        e = CreateEvent(
            type="een.personDetectionEvent.v1",
            startTimestamp=timestamp,
            endTimestamp=None,
            span=False,
            accountId=user_info.get('accountId'),
            actorId=camera_id,
            actorAccountId=camera_info.get('accountId'),
            actorType="camera",
            creatorId=os.getenv('CREATOR_ID'),
            data=data,
            dataSchemas=dataSchemas
        )
        return e.dict()
    else:
        return None


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


# Create Event
# This route will create an event based on the provided JSON body.
@app.route('/event', methods=['POST'])
@auth_required
def create_event():
    content_type = request.headers.get('Content-Type')
    if content_type != 'application/json':
        return "Invalid Content-Type", 400
    print('Creating Event')
    json_r = request.json

    # Convert the data list to the appropriate Pydantic models
    data_schemas = []
    for item in json_r.get('data', []):
        schema_type = item.get('type')
        if schema_type == 'een.objectDetection.v1':
            data_schemas.append(ObjectDetectionData(**item))
        elif schema_type == 'een.fullFrameImageUrl.v1':
            data_schemas.append(FullFrameImageData(**item))
        elif schema_type == 'een.objectClassification.v1':
            data_schemas.append(ObjectClassificationData(**item))
        elif schema_type == 'een.creatorDetails.v1':
            data_schemas.append(CreatorDetailsData(**item))
        elif schema_type == 'een.objectRegionMapping.v1':
            data_schemas.append(ObjectRegionmappingData(**item))
        else:
            return jsonify(
                {"error": f"Unsupported data schema type: {schema_type}"}), 400

    try:
        event_data = CreateEvent(**json_r)
    except ValidationError as e:
        print(f"Invalid data: {e}")
        return jsonify({"error": "Invalid data", "details": e.errors()}), 422

    try:
        create_response = client.post_event(event_data.dict())
        print(f"Event Created: {create_response}")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return json.dumps({'success': True}), 200, {
                'ContentType': 'application/json'
            }
        else:
            return redirect(url_for('events', camera_id=event_data.actorId))
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return json.dumps({
                'success': False,
                'error': str(e)
                }), 500, {
                'ContentType': 'application/json'
            }
        else:
            return redirect(url_for('events', camera_id=event_data.actorId))


# Analyze Frame
# This route will analyze a single frame from a camera feed.
@app.route('/analyze', methods=['POST'])
@auth_required
def analyze_frame():
    content_type = request.headers.get('Content-Type')
    if content_type != 'application/json':
        return "Invalid Content-Type", 400
    try:
        json_r = request.json
        camera_id = json_r.get('camera_id')
        timestamp = json_r.get('timestamp')
        response = client.get_recorded_image(camera_id, timestamp, "main")
        img_url = client.get_recorded_image(
            camera_id, timestamp, "main", construct_url=True)
    except AuthenticationError:
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Error getting image: {e}")
        return "Error", 500

    try:
        img = cv2.imdecode(np.frombuffer(response.content, np.uint8), -1)
        results = model(
            [img]
        )
        events = []
        for r in results:
            if len(r.boxes.cls) > 0:
                for n, detection in enumerate(r.boxes.cls):
                    label = r.names[int(detection)]
                    print(f"Detection {label}")
                    if label == 'person':
                        # Create person detection event
                        events.append(construct_detection_event(
                            camera_id,
                            "person",
                            timestamp,
                            r.boxes.xyxyn[n].tolist(),
                            img_url,
                            r.boxes.conf[n].item()
                        ))
                    if detection > 1 and detection <= 9:
                        # Create vehicle detection event
                        events.append(construct_detection_event(
                            camera_id,
                            label,
                            timestamp,
                            r.boxes.xyxyn[n].tolist(),
                            img_url,
                            r.boxes.conf[n].item()
                        ))
        for e in events:
            if e is None:
                events.remove(e)
        print(f"Events: {json.dumps(events)}")
        return jsonify({
            "status": "success",
            "events": events
        }), 200
    except Exception as e:
        print(f"Error running object detection: {e}")
        return "Error", 500


# Clips View
# This page will display a list of video clips for a selected camera.
@app.route('/clips/<camera_id>')
@auth_required
def view_clips(camera_id):
    media = {
        'access_token': session.get('access_token'),
        'base_url': session.get('base_url')
    }
    form = TimeSelectForm()

    print('Pulling Clips and Camera Info')
    try:
        response = client.get_cameras(camera_id)
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
            'form': form,
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


# Preview Export View
# This page will display a video player for a selected video clip.
@app.route('/preview/<camera_id>', methods=['GET'])
@auth_required
def preview(camera_id):
    print('Creating Preview')
    start = request.args.get('start')
    end = request.args.get('end')

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
            print(f"Clip: {clip}")

            return render_template(
                'preview.html',
                media=media,
                camera=camera,
                clip=clip)
        except Exception as e:
            print(f"Failed to get clip: {e}")
    else:
        return redirect(url_for('view_clips', camera_id=camera_id))


# Events List Page
# This page will display a list of events for a selected camera.
@app.route('/events/<camera_id>')
@auth_required
def events(camera_id):
    media = {
        'access_token': session.get('access_token'),
        'base_url': session.get('base_url')
    }
    form = TimeSelectForm()
    exclude = [
        "een.motionDetectionEvent.v1",
        "een.sceneLabelEvent.v1"
    ]

    # Retrieve the camera info and event types
    camera = json.loads(client.get_cameras(camera_id))
    event_types = json.loads(client.get_event_field_values(camera_id))['type']
    for e in exclude:
        try:
            event_types.remove(e)
        except ValueError:
            pass
    form.type.choices = [(t, t) for t in event_types]

    # Collect the query parameters from the request
    start = get_unquoted_arg('start')
    end = get_unquoted_arg('end')
    timezone = get_unquoted_arg('timezone') or 'UTC'
    page_token = request.args.get('page_token')

    context = {k: v for k, v in {
        'start': format_timestamp(start, timezone),
        'end': format_timestamp(end, timezone),
        'page_token': page_token,
        'include': ["data.een.fullFrameImageUrl.v1"]
    }.items() if v is not None}

    print('Retrieving Events')
    try:
        response = client.get_events(
            camera_id,
            event_types,
            **context
        )
        r_json = json.loads(response)
        events = r_json['results']
        next_page = r_json['nextPageToken']
        prev_page = r_json['prevPageToken']

        for event in events:
            event['type'] = camel_to_title(
                event['type'].split('.')[1]
            )
            if len(event['data']) == 0:
                event['data'].append({
                    "httpsUrl": url_for(
                        'static', filename='assets/no_image.svg'),
                    "type": "placeholderImage"
                })
    except Exception as e:
        print(f"Failed to load events: {e}")

    try:
        context = {k: v for k, v in {
            'media': media,
            'camera': camera,
            'form': form,
            'results': events,
            'start': start,
            'end': end,
            'next_page': next_page,
            'prev_page': prev_page
        }.items() if v is not None}
        return render_template('events.html', **context)
    except Exception as e:
        print(f"Failed to render events: {e}")


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
        response = client.get_cameras(camera_id)
        camera = json.loads(response)
    except Exception as e:
        print(f"Failed to get camera info: {e}")

    try:
        response = client.get_feeds(
            camera_id, type="main", include="multipartUrl,hlsUrl")
        r_json = json.loads(response)
        results = r_json['results']
        print(f"Feeds: {results[0]}")
    except Exception as e:
        print(f"API Call failed: {e}")

    try:
        return render_template(
            'view.html',
            camera=camera,
            media=media,
            results=results[0])
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
