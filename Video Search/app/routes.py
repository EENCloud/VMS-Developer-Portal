from app import app
from app.forms import SearchForm
import os
import json
import requests
import urllib.parse
from datetime import datetime, timedelta
from flask import (
    request, render_template, session,
    redirect, url_for
)
from dotenv import load_dotenv

load_dotenv()

# Enter the OAuth client credentials for your application.
# For more info see:
# https://developer.eagleeyenetworks.com/docs/client-credentials
# To use the API, your appliction needs its own client credentials.
clientId = os.getenv('CLIENT_ID')
clientSecret = os.getenv('CLIENT_SECRET')

# Hostname and port for the HTTP server
hostName = os.getenv('HOST_NAME')
port = os.getenv('PORT')


# OAuth Code Authentication
def getTokens(code):
    url = "https://auth.eagleeyenetworks.com/oauth2/token?grant_type=authorization_code&scope=vms.all&code="+code+"&redirect_uri=http://"+hostName + ":" + str(port)
    response = requests.post(url, auth=(clientId, clientSecret))
    try:
        json_object = json.loads(response.text)
        return json_object
    except ValueError:
        return None


# OAuth Refresh Token Authentication
def refreshAccess(refresh_token):
    url = "https://auth.eagleeyenetworks.com/oauth2/token?grant_type=refresh_token&scope=vms.all&refresh_token="+refresh_token
    response = requests.post(url, auth=(clientId, clientSecret))
    try:
        json_object = json.loads(response.text)
        return json_object
    except ValueError:
        return None


# Parse a search sting into a deep search request
# For more info see:
# https://developer.eagleeyenetworks.com/reference/parsevideoanalytics
def parseSearch(searchString, baseUrl, accessToken):
    url = f"https://{baseUrl}/api/v3.0/videoAnalyticEvents:parse"

    payload = {
        "query": searchString
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {accessToken}"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to parse search: {response.text}")


# Get the current time and the time exactly 7 days ago
# Timestamps must be included with deep search requests
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


# Perform a deep search request
# For more info see:
# https://developer.eagleeyenetworks.com/reference/listvideoanalyticsevents
def deepSearch(searchObject, baseUrl, accessToken):
    print(searchObject['objects__all'])
    url = f"https://{baseUrl}/api/v3.0/videoAnalyticEvents:deepSearch"

    # Set the query parameters for the deep search request
    includeParam = "data.een.fullFrameImageUrl.v1"
    current, week_ago = get_timestamps()

    url += "?include={include}&timestamp__gte={gte}&timestamp__lte={lte}".format(
        include=includeParam,
        gte=urllib.parse.quote(week_ago),
        lte=urllib.parse.quote(current)
    )

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {accessToken}"
    }

    response = requests.post(
        url,
        headers=headers,
        json=searchObject
    )
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to perform deep search: {response.text}")


# Index Page
# This page will display a search form and the results of the search.
# If the user is not logged in, they will be redirected to the login page.
@app.route('/', methods=['GET', 'POST'])
def index():
    form = SearchForm()
    accessToken = session.get('access_token')
    baseUrl = session.get('baseUrl')
    if not accessToken:
        return redirect(url_for('login'))

    if form.validate_on_submit():
        print('Search requested for {}'.format(form.query.data))
        response = parseSearch(form.query.data, baseUrl, accessToken)
        deepSearchResponse = deepSearch(
            json.loads(response),
            baseUrl,
            accessToken
        )
        print(deepSearchResponse)
        results = json.loads(deepSearchResponse)['results']
        return render_template('index.html', form=form, results=results)
    return render_template('index.html', form=form)


# Login Page
# This page will redirect the user to the Eagle Eye Networks OAuth login page.
# Review the OAuth Python example for more information.
@app.route('/login')
def login():
    code = request.args.get('code')

    if (code):
        oauthObject = getTokens(code)
        if 'access_token' in oauthObject:
            print(json.dumps(oauthObject))

            # Store the access_token, refresh_token, and baseUrl in the session
            session['access_token'] = oauthObject['access_token']
            session['refresh_token'] = oauthObject['refresh_token']
            session['baseUrl'] = oauthObject['httpsBaseUrl']['hostname']

            return redirect(url_for('index'))

        else:
            print("Code Auth failed. Response: "+oauthObject)

    endpoint = "https://auth.eagleeyenetworks.com/oauth2/authorize"
    requestAuthUrl = endpoint+"?client_id="+clientId+"&response_type=code&scope=vms.all&redirect_uri=http://"+hostName + ":" + str(port)

    return render_template('login.html', auth_url=requestAuthUrl)
