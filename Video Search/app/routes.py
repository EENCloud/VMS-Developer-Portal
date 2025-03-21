from app import app
from app.forms import SearchForm
import os
import json
import urllib.parse
from datetime import datetime, timedelta
from functools import wraps
from een import (
    EENClient,
    TokenStorage
)
from flask import (
    request, render_template, session,
    redirect, url_for
)
from dotenv import load_dotenv

load_dotenv()


class FlaskSessionStore(TokenStorage):
    def get(self, key):
        return session.get(key)

    def set(self, key, value):
        session[key] = value
        session.modified = True

    def __contains__(self, key):
        return key in session


# Load the API Client
token_store = FlaskSessionStore()
redirect_uri = "http://{host}:{port}".format(
    host=os.getenv('FLASK_RUN_HOST'),
    port=os.getenv('FLASK_RUN_PORT')
)

client = EENClient(
    os.getenv('CLIENT_ID'),
    os.getenv('CLIENT_SECRET'),
    redirect_uri,
    token_store,
    timeout=20
)


# Get the unquoted argument
def get_unquoted_arg(arg_name):
    value = request.args.get(arg_name)
    return urllib.parse.unquote(value) if value else None


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


# Parse the deep search response
# This function will modify the URLs in the deep search response
# to use the base URL from the session
def parseDeepSearch(response):
    base_url = session.get('base_url')
    results = json.loads(response)['results']
    for result in results:
        s = result['data'][0]['httpsUrl'].split('/')
        s[2] = base_url
        result['data'][0]['httpsUrl'] = '/'.join(s)
    return results


# Search Logic
def perform_search(term):
    # Parse the search term
    body = {"query": term}
    try:
        response = client.parse_video_analytics(body=body)
        print(response)
    except Exception as e:
        print(f"Failed to parse search: {e}")
        return []

    # Perform the deep search
    searchObj = json.loads(response)
    end, start = get_timestamps()
    include = "data.een.fullFrameImageUrl.v1"
    try:
        deepSearchResponse = client.list_video_analytics_events(
            include=include,
            timestamp__gte=start,
            timestamp__lte=end,
            body=searchObj
        )
    except Exception as e:
        print(f"Failed to list video analytics events: {e}")
        return []

    results = parseDeepSearch(deepSearchResponse)
    return results


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

    term = request.args.get('term')
    form = SearchForm(term=term)

    if form.validate_on_submit():
        term = form.term.data
        return redirect(url_for('index', term=term))

    elif term:
        media = {
            'access_token': session.get('access_token'),
            'base_url': session.get('base_url')
        }
        try:
            results = perform_search(term)
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
    print("Redirecting to: " + requestAuthUrl)

    return render_template('login.html', auth_url=requestAuthUrl)


# Logout Page
# This page will clear the session and redirect the user to the login page.
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
