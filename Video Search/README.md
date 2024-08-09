# Eagle Eye Networks Video Search Sample Application

This sample Flask application demonstrates how to use the video search API for Eagle Eye Networks. To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).



## Setup

1. Clone this repository or copy the sample code into your local environment.
   
2. Install dependencies:
   ```
   $ pip install -r requirements.txt
   ```

3. Create a copy of `example.flaskenv` and rename it `.flaskenv`. Update the `CLIENT_ID` and `CLIENT_SECRET` in the file with your application's credentials. For more details on obtaining these credentials, visit our [API documentation](https://developer.eagleeyenetworks.com/docs/client-credentials).

4. Update the FLASK_APP environment variable:
   ```
   $ export FLASK_APP=search.py
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
3. Once you log in, you will be redirected to the search page.
4. When you search, the application will first [parse your query](https://developer.eagleeyenetworks.com/reference/parsevideoanalytics) and then make a request to the [deep search API](https://developer.eagleeyenetworks.com/reference/listvideoanalyticsevents). The results will be displayed on the page.


## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive [API documentation](https://developer.eagleeyenetworks.com/reference/listcameras).
