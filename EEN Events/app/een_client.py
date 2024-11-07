import re
import json
import time
import requests
import logging
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


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


class TokenStorage(ABC):
    @abstractmethod
    def get(self, key):
        pass

    @abstractmethod
    def set(self, key, value):
        pass

    @abstractmethod
    def __contains__(self, key):
        pass


class EENClient:
    auth_url = "https://auth.eagleeyenetworks.com/oauth/authorize"

    def __init__(
            self, client_id, client_secret,
            redirect_uri, token_storage, max_retries=3):
        if not isinstance(token_storage, TokenStorage):
            raise TypeError(
                "token_storage must implement the TokenStorage interface.")
        self.client_id = client_id
        self.client_secret = client_secret
        self.max_retries = max_retries
        self.redirect_uri = redirect_uri
        self.token_storage = token_storage

    # OAuth Authentication
    def auth_een(self, token, type="code"):
        """
        Authenticate with the Eagle Eye Networks API
        and store the access token, refresh token,
        and base URL in the token storage.

        :param token: The authorization code or refresh token.
        :param type: The type of token being used. Either 'code' or 'refresh'.
        :return: The response from the authentication request.
        """
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
                "redirect_uri": self.redirect_uri
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
                self.client_id,
                self.client_secret
            ),
            data=data,
            headers=headers
        )
        if response.ok:
            auth_response = json.loads(response.text)
            self.token_storage.set(
                'access_token', auth_response['access_token'])
            self.token_storage.set(
                'refresh_token', auth_response['refresh_token'])
            self.token_storage.set(
                'base_url', auth_response['httpsBaseUrl']['hostname'])
        else:
            raise AuthenticationError(
                "Authentication Failed: {code} {text}".format(
                    code=response.status_code,
                    text=response.text
                ))
        return response

    def refresh_access_token(self):
        refresh_token = self.token_storage.get('refresh_token')
        if not refresh_token:
            raise AuthenticationError("No refresh token found.")
        self.auth_een(refresh_token, type="refresh")

    def __retry_request(self, request_func, *args, **kwargs):
        max_retries = self.max_retries
        retry_count = 0
        while retry_count <= max_retries:
            try:
                response = request_func(*args, **kwargs)
                if response.ok:
                    return response
                elif response.status_code == 401:
                    logger.info("Auth failed. Refreshing Access Token.")
                    self.refresh_access_token()
                else:
                    raise Exception(
                        f"{response.status_code} Response: {response.text}")
            except (AuthenticationError, RequestException) as e:
                logger.error(
                    f"Request failed: {e}. {retry_count}/{max_retries}")
                if retry_count == max_retries:
                    raise
                retry_count += 1
                time.sleep(2 ** retry_count)

    # API Call
    # This function will make an API call to the Eagle Eye Networks API
    def __api_call(
            self,
            endpoint,
            method='GET',
            params=None,
            data=None,
            headers=None,
            stream=False
            ):
        access_token = self.token_storage.get('access_token')
        base_url = self.token_storage.get('base_url')

        url = f"https://{base_url}/api/v3.0{endpoint}"
        if params:
            url += '?' + urllib.parse.urlencode(params)

        logger.info(f"request: {url}")

        if not headers:
            headers = {
                "accept": "application/json",
                "content-type": "application/json"
            }
        headers['Authorization'] = f'Bearer {access_token}'

        def request_func():
            if method == 'GET':
                return requests.get(url, headers=headers, stream=stream)
            elif method == 'POST':
                return requests.post(
                    url, headers=headers, data=json.dumps(data))

        response = self.__retry_request(request_func)
        if stream:
            return response
        return response.text

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
        logger.info(f"Data type: {data['type']}")
        return self.__api_call(
            endpoint, headers=headers, data=data, method='POST')

    # Retrieve a recorded image
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/getrecordedimage
    def get_recorded_image(
            self, device_id, timestamp,
            type="preview", construct_url=False):
        endpoint = "/media/recordedImage.jpeg"
        params = {
            "deviceId": device_id,
            "type": type,
            "timestamp__gte": timestamp
        }
        if construct_url:
            url = "https://{base}/api/v3.0{endpoint}".format(
                base=self.token_storage.get('base_url'),
                endpoint=endpoint
            )
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

        return self.__api_call(endpoint, params=params)

    # Get a list of cameras
    # For more info see:
    # https://developer.eagleeyenetworks.com/reference/listcameras
    def get_cameras(self, camera_id=None):
        endpoint = "/cameras"

        if camera_id:
            endpoint += f"/{camera_id}"

        return self.__api_call(
            endpoint
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
