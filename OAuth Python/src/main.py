# Get API Credentials using OAuth2
# Step 1: Redirect the user to auth.eagleeyenetworks.com
# Step 2: The user will log in to their VMS Account
# Step 3: The user will be redirected back to your application with a CODE
# Step 4: Your application backend/server request the Access token.

# We'll use Flask to start an HTTP server to act as your application backend.
import json
import requests
import urllib.parse
from flask import Flask, request


# Hostname and port for the HTTP server
hostName = "127.0.0.1"
port = 3333

# A refresh token can be used to get a new access token
# without the user having to log in again.
# If you have a refresh token, you can enter it here.
refresh_token = ""

# Enter the OAuth client credentials for your application.
# For more info see:
# https://developer.eagleeyenetworks.com/docs/client-credentials
# To use the API, your appliction needs its own client credentials.
clientId = "{Your Client ID}"
clientSecret = "{Your Client Secret}"


# This method is executing step 3.
# It will request the access token and refresh token.
# The redirect_uri here must match the redirect_uri sent in step 1.
def getTokens(code):
    url = "https://auth.eagleeyenetworks.com/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "scope": "vms.all",
        "code": code,
        "redirect_uri": "http://"+hostName + ":" + str(port)
    }
    response = requests.post(url, auth=(clientId, clientSecret), data=data)
    return response.text


# Use a refresh token to get a new access token
def refreshToken(refresh_token):
    url = "https://auth.eagleeyenetworks.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "scope": "vms.all",
        "refresh_token": refresh_token
    }
    response = requests.post(url, auth=(clientId, clientSecret), data=data)
    return response.text


def oauthValid(oauthObject):
    # Check if the response is a JSON object
    try:
        json_object = json.loads(oauthObject)
    except ValueError:
        return False

    # Check if the JSON object contains an access_token
    if 'access_token' in json_object:
        return True
    else:
        return False


app = Flask(__name__)


# If a user visits localhost:3333 this method will be called.
# 1) For step 1, a link is given to rediret the user to
#    auth.eagleeyenetworks.com.
#    Here, they can log in to their VMS account.
# 2) Once the user logs in, they will be redirected back to
#    localhost:3333 with a CODE. The backend can now request
#    the access_token and refresh_token.
# 3) If a refresh_token is stored, it can be used to get a new
#    new access_token without requiring the user to to log in again.
@app.route('/')
def index():
    # This is getting the ?code= querystring value from the HTTP request.
    code = request.args.get('code')

    if (code):
        # Execute Step 2, the user is redirected back to localhost:3333
        # because of the "&redirect_uri="
        # With the CODE, this backend can request the actual access_token and
        # refresh_token. For demonstration purposes the results are printed to
        # the console.
        # On production, never show the refresh_token in the browser.
        oauthObject = getTokens(code)
        if (oauthValid(oauthObject)):
            print(oauthObject)

            return "You are logged in"
        else:
            print("Code Auth failed. Response: "+oauthObject)
    elif (refresh_token != ''):
        # If a refresh token has been entered, use the refresh token to get a
        # new access token.
        oauthObject = refreshToken(refresh_token)
        if (oauthValid(oauthObject)):
            print(oauthObject)
            return "You are logged in thanks to a refresh token."
        else:
            print("Refresh token failed. Response: "+oauthObject)

    # Executing step 1, a link is generated to redirect the user to
    # auth.eagleeyenetworks.com
    url = "https://auth.eagleeyenetworks.com/oauth2/authorize"
    params = {
        "client_id": clientId,
        "response_type": "code",
        "scope": "vms.all",
        "redirect_uri": "http://"+hostName + ":" + str(port)
    }
    url += "?" + urllib.parse.urlencode(params)
    page = '''
    <html><head><title>OAuth Testing</title></head>
    <h1>OAuth Testing</h1>
    </br>
    <a href='{url}'>Login with Eagle Eye Networks</a>
    </html>
    '''.format(url=url)
    return page


# Start the HTTP server
if __name__ == '__main__':
    app.run(host=hostName, port=port)
