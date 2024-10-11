# Eagle Eye Networks Event Insertion and Management

This example demonstrates the process for creating and managing Eagle Eye Networks events. To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).

## Before You Begin

Before you can use the event insertion function, you will need to request a Creator ID. This ID indicates with which account the events will be associated with and will also determine which events you are able to send to the API. To request a Creator ID, please contact the [API platform team](mailto:api_support@een.com).

This example demonstrates the creation of [Person Detection events](https://developer.eagleeyenetworks.com/docs/example-events#person-detection-event). To see a list of all available event types, refer to the [API documentation](https://developer.eagleeyenetworks.com/docs/example-events).

## Setup

1. Clone this repository or copy the sample code into your local environment.
   
2. Install dependencies:
   ```
   $ pip install -r requirements.txt
   ```

3. Create a copy of `example.flaskenv` and rename it `.flaskenv`. Update the `CLIENT_ID` and `CLIENT_SECRET` in the file with your application's credentials. For more details on obtaining these credentials, visit our [API documentation](https://developer.eagleeyenetworks.com/docs/client-credentials).

4. Update the FLASK_APP environment variable:
   ```
   $ export FLASK_APP=main.py
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
4. When you select a camera, you'll be taken to the high resolution live stream view of that camera.


## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive [API documentation](https://developer.eagleeyenetworks.com/reference/listcameras).
