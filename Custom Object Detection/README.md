# Eagle Eye Networks Custom Object Detection Example

This sample Flask application connects to an Eagle Eye Networks account and runs an object detection model against one of the live RTSP feeds.  To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).

The script uses the [Ultralytics YOLO](https://docs.ultralytics.com/) object detection model to detect objects in the live video feed. The bounding boxes for the objects are then displayed on the video feed in real time.


## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Clone this repository or copy the sample code into your local environment.

3. Create a copy of `example.flaskenv` and rename it `.flaskenv`. Update the `CLIENT_ID` and `CLIENT_SECRET` in the file with your application's credentials. For more details on obtaining these credentials, visit our [API documentation](https://developer.eagleeyenetworks.com/docs/client-credentials).

4. Update the FLASK_APP environment variable:
   ```
   $ export FLASK_APP=detect.py
   ```


## Running the Application

To start the server:
```
python -m flask run
```
This will host a local server on `127.0.0.1:3333`.

## Usage

1. Navigate to `http://127.0.0.1:3333` in your web browser.
2. Click on the "Login with Eagle Eye Networks" link to authenticate.
3. Once you log in, you will be redirected to the camera select page.
4. Select a camera view to start the object detection.


## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive API documentation.