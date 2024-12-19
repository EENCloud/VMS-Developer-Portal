# Eagle Eye Networks Video Export Sample Application

This sample Flask application demonstrates how to use the video search API for Eagle Eye Networks. To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).



## Setup

1. Install dependencies:
   ```
   $ pip install -r requirements.txt
   ```

2. Clone this repository or copy the sample code into your local environment.

3. Create a copy of `example.flaskenv` and rename it `.flaskenv`. Update the `CLIENT_ID` and `CLIENT_SECRET` in the file with your application's credentials. For more details on obtaining these credentials, visit our [API documentation](https://developer.eagleeyenetworks.com/docs/client-credentials).

## Running the Application

To start the server:
```
python -m flask run
```
This will host a local server on `127.0.0.1:5000`.

## Usage

### Logging In

1. Navigate to `http://127.0.0.1:5000` in your web browser.
2. Click on the "Login with Eagle Eye Networks" link to authenticate.
3. Once you log in, you will be redirected to the Camera List.

### Creating an Export

1. From the Camera List, click on the camera you'd like to export a video from. This will take you to the Clip Navigator for that camera.
2. From the Clip Navigator, select a clip that you'd like to export. You can filter clips by time using the form above the video clips.
3. Once you've selected a clip, you will be brought to the Preview for that video. Here, you can review the footage before confirming the export. The form on near the video will allow you to set the file name and location for the export. When you're ready, click the blue button to confirm your selection.
4. When the export has been initiated, you'll recieve an alert.

### Downloading a File

1. From any screen, select the File button from the menu at the top of the page.
2. From the File Navigator, you may view the availible folders and videos in the archive. You can select which file you'd like to download here.
3. When you've located the file you'd like to download, click the download button to the right of the table. Your download will begin shortly.

## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive [API documentation](https://developer.eagleeyenetworks.com/reference/listcameras).
