# Eagle Eye Networks IP Speakers

This example demonstrates the process for adding and employing IP Speakers through  Eagle Eye Networks' API. To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).


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

> [!NOTE]
> This example leverages the Eagle Eye Networks 2-Way Audio SDK to create an intercom between the web user and the IP Speaker. This SDK has been packaged for browser usage and is included in the `static` directory. If you would like to use the SDK in your own application, you can refer to the [2-Way Audio SDK documentation](https://developer.eagleeyenetworks.com/docs/two-way-audio-web-sdk).

## Packaging the 2-Way Audio SDK

To package the 2-Way Audio SDK for use in your own application, you can use the following steps:

1. Install Webpack (or any other bundler of your choice):
   ```
   $ npm install --save-dev webpack webpack-cli
   ```

2. Create a `webpack.config.js` file in the root of your project with the following content:
   ```javascript
   const path = require('path');

   module.exports = {
      mode: 'production',
      entry: './index.js',
      output: {
         filename: 'bundle.js',
         path: path.resolve(__dirname, 'app/static/js'), // Output directory
      },
   };
   ```

3. Create an `index.js` file in the root of your project with the following content:
   ```javascript
   const EENWebRTC = require('@een/two-way-audio-web-sdk');
   ```

4. Run Webpack to bundle the SDK:
   ```
   $ npx webpack
   ```

5. Include the bundled `bundle.js` file in your template or HTML file:
   ```html
   <script src="static/js/bundle.js"></script>
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
4. When you select a camera, you'll be taken to the high resolution live stream view of that camera. From here, you will be able to activate an intercom to the IP Speaker associated with the camera if one is available.


## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive [API documentation](https://developer.eagleeyenetworks.com/reference/listcameras).
