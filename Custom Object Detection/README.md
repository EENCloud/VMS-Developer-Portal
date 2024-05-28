# Eagle Eye Networks Custom Object Detection Example

This sample Python script connects to an Eagle Eye Networks account and runs an object detection model against one of the live RTSP feeds. To run this script, you will need to have an application registered with the Eagle Eye Networks Developer Program. You will also need to have a valid Eagle Eye Networks account with an IP camera that is connected to a Bridge or the Eagle Eye Cloud using Camera Direct. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).

The script uses the [Ultralytics YOLO](https://docs.ultralytics.com/) object detection model to detect objects in the live video feed. The detected objects are then displayed on the video feed in real time.

## Requirements

- Python 3.x
- Requests
- Ultralytics
- dotenv

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Clone this repository or copy the sample code into your local environment.

3. Rename example.env to dot env and update the following values:
   - `CLIENT_ID` - Your Eagle Eye Networks application's client ID. 
   - `CLIENT_SECRET` - Your Eagle Eye Networks application's client secret.
   - `CAMERA_ID` - The ID of the camera you want to use for object detection.
   - `REFRESH_TOKEN` - A valid refresh token for the account you want to access. This can be obtained by running the [OAuth Python example server](https://github.com/EENCloud/VMS-Developer-Portal/tree/main/OAuth%20Python).

## Running the Application

To start the application:
```
python een_alert.py
```
The application will attamept to connect to a live video feed and run the object detection model. Detected objects will be displayed on the video feed in real-time.


## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive API documentation.