from app import app
from app.forms import SearchForm
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
def code_auth(code):
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


# Handle Response
# This function will handle the response from an API call
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


# Parse a search sting into a deep search request
# For more info see:
# https://developer.eagleeyenetworks.com/reference/parsevideoanalytics
def parseSearch(searchString):
    endpoint = "/videoAnalyticEvents:parse"

    payload = {
        "query": searchString
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    return api_call(
        endpoint,
        method='POST',
        data=json.dumps(payload),
        headers=headers)


# Perform a deep search request
# For more info see:
# https://developer.eagleeyenetworks.com/reference/listvideoanalyticsevents
def deepSearch(searchObject):
    endpoint = "/videoAnalyticEvents:deepSearch"

    # Set the query parameters for the deep search request
    includeParam = "data.een.fullFrameImageUrl.v1"
    current, week_ago = get_timestamps()
    params = {
        "include": includeParam,
        "timestamp__gte": week_ago,
        "timestamp__lte": current
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    return api_call(
        endpoint,
        method='POST',
        params=params,
        data=json.dumps(searchObject),
        headers=headers)


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


# Index Page
# This page will display a search form and the results of the search.
# If the user is not logged in, they will be redirected to the login page.
@app.route('/', methods=['GET', 'POST'])
def index():
    code = request.args.get('code')
    if code:
        return redirect(url_for('login') + '?code=' + code)
    if not is_authenticated():
        return redirect(url_for('login'))

    form = SearchForm()

    if form.validate_on_submit():
        print('Search requested for {}'.format(form.query.data))
        media = {
            'access_token': session.get('access_token'),
            'base_url': session.get('base_url')
        }
        try:
            response = parseSearch(form.query.data)
            deepSearchResponse = deepSearch(json.loads(response))
            # print(deepSearchResponse)
            results = json.loads(deepSearchResponse)['results']
            return render_template(
                'index.html',
                form=form,
                results=results,
                media=media
            )
        except Exception as e:
            print(f"Failed to complete search: {e}")
            return render_template('index.html', form=form)
    return render_template('index.html', form=form)


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

            # Store the access_token, refresh_token, and base_url in the session
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
