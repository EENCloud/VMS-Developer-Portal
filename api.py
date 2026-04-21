"""
Minimal Eagle Eye Networks API v3 client.
Handles base-URL discovery and authenticated requests.
"""
import json
import urllib.parse
import urllib.request

import auth
import config


# Base URL is account-specific and must be resolved before making API calls.
_base_url: str | None = None


def _get_json(url: str, headers: dict, params: dict | None = None) -> dict:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _get_base_url(access_token: str) -> str:
    """
    Fetch the account-specific base URL from the client settings endpoint.
    Eagle Eye's base URL looks like https://api.c000.eagleeyenetworks.com/api/v3.0
    """
    global _base_url
    if _base_url:
        return _base_url

    data = _get_json(
        "https://api.eagleeyenetworks.com/api/v3.0/clientSettings",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    https_base = data.get("httpsBaseUrl", {})
    hostname = https_base.get("hostname", "api.eagleeyenetworks.com")
    port = https_base.get("port", 443)
    _base_url = f"https://{hostname}:{port}/api/v3.0"
    return _base_url


def get_live_stream(camera_id: str | None = None, stream_type: str = "main", local: bool = False) -> str:
    """
    Return an RTSP URL for a live camera stream.

    Args:
        camera_id:   Camera device ID. Defaults to CAMERA_ID from config.
        stream_type: "main" (full resolution) or "preview" (low quality).
        local:       If True, request the local bridge RTSP URL instead of the cloud URL.

    Returns:
        The RTSP URL with the access token appended.
    """
    device_id = camera_id or config.CAMERA_ID
    if not device_id:
        raise ValueError("No camera ID provided. Set EEN_CAMERA_ID in .env or pass camera_id.")

    include = "localRtspUrl" if local else "rtspUrl"
    result = get("/feeds", params={"deviceId": device_id, "type": stream_type, "include": include})
    feeds = result.get("results", [])
    if not feeds:
        raise RuntimeError(f"No feed returned for camera {device_id}.")

    access_token = auth.get_valid_access_token()
    rtsp_url = feeds[0].get(include)
    if not rtsp_url:
        raise RuntimeError(f"Response did not contain '{include}' for camera {device_id}.")

    return f"{rtsp_url}&access_token={access_token}"


def get(endpoint: str, params: dict | None = None) -> dict:
    """
    Perform a GET request against the EEN API v3.
    Automatically resolves the base URL and handles token refresh.
    """
    access_token = auth.get_valid_access_token()
    base_url = _get_base_url(access_token)

    url = f"{base_url}{endpoint}"
    return _get_json(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        params=params,
    )
