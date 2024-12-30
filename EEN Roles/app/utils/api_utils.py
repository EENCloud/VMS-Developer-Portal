import json
import requests
import urllib.parse
from flask import session
from app.auth import auth_een

def api_call(endpoint, method='GET', params=None, data=None, headers=None, retry_count=0, max_retries=1, stream=False):
    access_token = session.get('access_token')
    base_url = session.get('base_url')
    if not base_url:
        raise Exception("Base URL is missing from session.")
    if not access_token:
        raise Exception("Access token is missing from session.")

    url = f"https://{base_url}/api/v3.0{endpoint}"
    if params:
        url += '?' + urllib.parse.urlencode(params)

    headers = headers or {}
    headers['Authorization'] = f'Bearer {access_token}'
    headers['Content-Type'] = 'application/json'  # Ensure JSON content-type for POST/PUT requests if needed

    try:
        response = requests.request(method, url, headers=headers, data=data, stream=stream)
        if response.status_code >= 400:
            raise Exception(f"API call error for {method} {url}: {response.status_code} - {response.text}")
        return handle_response(
            response, api_call, endpoint, method=method, params=params, data=data,
            headers=headers, retry_count=retry_count, stream=stream
        )
    except requests.exceptions.RequestException as e:
        if retry_count < max_retries:
            return api_call(endpoint, method, params, data, headers, retry_count + 1, stream)
        raise Exception(f"API request failed after retries: {str(e)}")

def handle_response(response, original_request_func, endpoint, retry_count=0, max_retries=1, *args, **kwargs):
    if response.ok:
        return response.text
    elif response.status_code == 401 and retry_count < max_retries:
        refresh_token = session.get('refresh_token')
        if refresh_token:
            # Attempt to refresh the access token
            refresh_response = auth_een(refresh_token, type="refresh")
            if refresh_response.status_code == 200:
                auth_response = json.loads(refresh_response.text)
                # Update session with new tokens
                session['access_token'] = auth_response['access_token']
                session['refresh_token'] = auth_response['refresh_token']
                session['base_url'] = auth_response['httpsBaseUrl']['hostname']
                retry_count += 1
                # Retry the original request with the new access token
                return original_request_func(endpoint, retry_count=retry_count, *args, **kwargs)
            else:
                raise Exception("Authentication Error: Unable to refresh token")
        else:
            raise Exception("Authentication Error: No refresh token found")
    else:
        raise Exception(f"{response.status_code} Response: {response.text}")