import os
import re
import json
import requests
import urllib.parse
from flask import session
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


# Format timestamps to ISO 8601 format
def format_timestamp(timestamp_str, user_timezone='UTC'):
    if not timestamp_str:
        return None
    try:
        local_dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M')
        local_tz = ZoneInfo(user_timezone)
        local_dt = local_dt.replace(tzinfo=local_tz)
        utc_dt = local_dt.astimezone(ZoneInfo('UTC'))
        # Format with millisecond precision
        return utc_dt.isoformat(timespec='milliseconds')
    except ValueError:
        return None


# Get the current time and the time exactly 7 days ago
# Timestamps must be included with deep search requests
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


# Convert a camelCase string to a title case string
# This is useful for converting event names into a more readable format
def camel_to_title(camel_str, acronyms=['pos', 'lpr']):
    """
    Convert a camelCase string to a title case string.
    :param camel_str: The camelCase string to convert.
    :param acronyms: A list of acronyms to capitalize in the title.
    :return: The title case string.
    """

    title_str = re.sub(r'([a-z])([A-Z])', r'\1 \2', camel_str).title()
    for acronym in acronyms:
        title_str = re.sub(
            fr'\b({acronym})\b',
            acronym.upper(),
            title_str,
            flags=re.IGNORECASE
        )

    return title_str


class AuthenticationError(Exception):
    "Raised when an API call failed to authenticate with the server."
    pass


class EENClient:
    auth_url = "https://auth.eagleeyenetworks.com/oauth2/authorize"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    # OAuth Authentication
    def auth_een(self, token, type="code"):
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
    def __handle_response(
            self,
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
                refresh_response = self.auth_een(refresh_token, type="refresh")
                if refresh_response.status_code == 200:
                    # print(auth_response.text)
                    auth_response = json.loads(refresh_response.text)

                    # Store the tokens in the session
                    session['access_token'] = auth_response['access_token']
                    session['refresh_token'] = auth_response['refresh_token']
                    session[
                        'base_url'] = auth_response['httpsBaseUrl']['hostname']

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
            raise Exception(
                f"{response.status_code} Response: {response.text}")

    # API Call
    # This function will make an API call to the Eagle Eye Networks API
    def __api_call(
            self,
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

            response = requests.post(
                url, headers=headers, data=json.dumps(data))

        return self.__handle_response(
            response,
            self.__api_call,
            endpoint,
            method=method,
            params=params,
            data=data,
            headers=headers,
            retry_count=retry_count,
            stream=stream
        )

    # Get the current user
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/getcurrentuser
    def current_user(self, include: list = None):
        endpoint = "/users/self"
        if include:
            include = ",".join(include)
            return self.__api_call(endpoint, params={
                "include": include
            })
        return self.__api_call(endpoint)

    # Get event field values for a given device
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/listeventsfieldvalues
    def get_event_field_values(self, actor_id, actor_type="camera"):
        endpoint = "/events:listFieldValues"

        params = {
            "actor": f"{actor_type}:{actor_id}"
        }
        return self.__api_call(endpoint, params=params)

    # Get a list of events
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/listevents
    def get_events(
            self,
            actor_id,
            event_types: list,
            actor_type="camera",
            page_token=None,
            include: list = None,
            start=None, end=None):
        endpoint = "/events"

        if start is None:
            e, s = get_timestamps()
            start = s
            if end is None:
                end = e

        type_str = ",".join(event_types)
        if include:
            include = ",".join(include)

        params = {k: v for k, v in {
            "actor": f"{actor_type}:{actor_id}",
            "startTimestamp__gte": start,
            "type__in": type_str,
            "include": include,
            "pageToken": page_token,
            "endTimestamp__lte": end,
            "pageSize": 24
        }.items() if v is not None}

        return self.__api_call(endpoint, params=params)

    # Create an event
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/createevent
    def post_event(
        self,
        data: dict
    ):
        endpoint = "/events"
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }
        print(f"Data type: {data['type']}")

        return self.__api_call(
            endpoint, headers=headers, data=data, method='POST')

    # Retrieve a recorded image
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/getrecordedimage
    def get_recorded_image(
            self, device_id, timestamp,
            type="preview",
            construct_url=False):
        endpoint = "/media/recordedImage.jpeg"
        params = {
            "deviceId": device_id,
            "type": type,
            "timestamp__gte": timestamp
        }
        if construct_url:
            url = f"https://{session.get('base_url')}/api/v3.0{endpoint}"
            url += f"?{urllib.parse.urlencode(params)}"
            return url
        return self.__api_call(endpoint, params=params, stream=True)

    # Get a list of availible video clips
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/listmedia
    def get_media(
            self,
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
            "include": "rtspUrl,mp4Url",
            "pageSize": "24"
        }

        if end:
            params['endTimestamp__lte'] = end
        if page_token:
            params['pageToken'] = page_token

        return self.__api_call(endpoint, params=params, headers=headers)

    # Get a list of cameras
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/listcameras
    def get_cameras(self, camera_id=None):
        endpoint = "/cameras"

        if camera_id:
            endpoint += f"/{camera_id}"

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }
        return self.__api_call(
            endpoint,
            headers=headers
        )

    # Get a list of feeds
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/listfeeds
    def get_feeds(
            self, device_id=None, type="preview", include="multipartUrl"):
        endpoint = "/feeds"

        params = {
            "include": include,
            "type": type
        }
        if device_id:
            params['deviceId'] = device_id
        return self.__api_call(endpoint, params=params)

    # Play an audio file
    # For more info see:
    # https://developer.eagleeyenetworks.com/docs/audio-push-via-http
    def play_audio(self, camera_id):
        endpoint = "/feeds"

        params = {
            'deviceId': camera_id,
            'type': "talkdown",
            'include': 'audioPushHttpsUrl'
        }

        resp = json.loads(self.__api_call(endpoint, params=params))

        results = resp.get('results', [])
        if len(results) != 1:
            return False
        url = results[0].get('audioPushHttpsUrl', None)
        if url is None:
            return False

        access_token = session.get('access_token')

        headers = {
            "Transfer-Encoding": 'chuncked',
            "Authorization": f'Bearer {access_token}'
        }

        print(f"Current dir: {os.getcwd()}")

        filepath = "app/static/assets/sample_8k_8bit_1ch_ulaw.raw"

        with open(filepath, 'rb') as audio_file:
            files = {'audio_chunk': audio_file}

            # Perform the POST request
            response = requests.post(url+"ulaw", headers=headers, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")
        return True
