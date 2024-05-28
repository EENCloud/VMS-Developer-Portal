# Create a custom AI detection alert for an Eagle Eye Networks VMS account.
# Step 1: Connect to Eaagle Eye Networks
# Step 2: Request the video feed URL
# Step 3: Run object detection on the video feed
# Step 4: Record detections as Eagle Eye Analytics events

# Import the necessary libraries
import json
import requests
import argparse
import os
from dotenv import load_dotenv
from ultralytics import YOLO


# Rename example.env to .env and fill in the values
load_dotenv()

# Enter the OAuth client credentials for your application.
# For more info see:
# https://developer.eagleeyenetworks.com/docs/client-credentials
# To use the API, your appliction needs its own client credentials.
clientId = os.getenv('CLIENT_ID')
clientSecret = os.getenv('CLIENT_SECRET')

# A refresh token can be used to generate an access token
# without the user having to log in again.
# Very useful for long-running applications.
refresh_token = os.getenv('REFRESH_TOKEN')

camera_id = os.getenv('CAMERA_ID')


# Use a refresh token to get an access token
def auth(refresh_token):
    url = "https://auth.eagleeyenetworks.com/oauth2/token?grant_type=refresh_token&scope=vms.all&refresh_token="+refresh_token
    response = requests.post(url, auth=(clientId, clientSecret))
    try:
        json_object = json.loads(response.text)
    except ValueError:
        return False

    # Check if the JSON object contains an access_token
    if 'access_token' in json_object:
        print(response.text)

        # Save the new refresh token and write it to a file
        refresh_token = json_object['refresh_token']
        f = open("refresh_token.txt", "w")
        f.write(refresh_token)
        f.close()
        return json_object
    else:
        raise Exception("Error getting access token: "+response.text)


# Get the video feed URL using the List Feeds endpoint
# Documeantion for this endpoint can be found at:
# https://developer.eagleeyenetworks.com/reference/listfeeds
def get_feed_url(baseUrl, access_token, camera_id=None):
    if camera_id:
        url = f"https://{baseUrl}/api/v3.0/feeds?deviceId={camera_id}&type=main&include=rtspUrl"
    else:
        url = f"https://{baseUrl}/api/v3.0/feeds?type=main&include=rtspUrl"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    json_object = json.loads(response.text)
    if 'results' in json_object and 'rtspUrl' in json_object['results'][0]:
        return json_object
    else:
        raise Exception("Error getting feed URL: "+response.text)


def run():
    if not clientId or not clientSecret:
        raise Exception(
            "Please set the CLIENT_ID and CLIENT_SECRET environment variables")

    # Connect to Eagle Eye Networks
    # Get a fresh access token
    oauthObject = auth(refresh_token)
    access_token = oauthObject['access_token']
    baseUrl = oauthObject['httpsBaseUrl']['hostname']

    # Get the video feed URL
    # You can specify a camera_id to get the URL for a specific camera
    if camera_id:
        feedResponse = get_feed_url(baseUrl, access_token, camera_id)
    else:
        feedResponse = get_feed_url(baseUrl, access_token)

    feedUrl = f"{feedResponse['results'][0]['rtspUrl']}&access_token={access_token}"

    # Run object detection on the video feed
    # Results are returned in a generator
    model = YOLO('yolov8s.pt')
    results = model(
        source=feedUrl, show=True, conf=0.4, classes=0, stream=True)

    for i in results:
        # Handle the detection
        if len(i.boxes.cls) > 0:
            for n, detection in enumerate(i.boxes.cls):
                coord = [
                    int(float(i.boxes.xywhn[n][0])*i.orig_shape[0]),
                    int(float(i.boxes.xywhn[n][1])*i.orig_shape[1])
                ]
                print(f"Detection: {i.names[int(detection)]} at {coord}")
                # handle_detecton()


def parse_opt():
    parser = argparse.ArgumentParser(
        description='Eagle Eye Networks Custom AI Detection Alert')
    parser.add_argument('--refresh_token', type=str, help='Refresh token')
    parser.add_argument('--access_token', type=str, help='Access token')
    parser.add_argument('--client_id', type=str, help='Client ID')
    parser.add_argument('--client_secret', type=str, help='Client Secret')
    parser.add_argument('--camera_id', type=str, help='Camera ID')
    opt = parser.parse_args()
    return opt


def main(opt):
    run()


if __name__ == "__main__":
    opt = parse_opt()
    main(opt)
