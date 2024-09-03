# Eagle Eye Networks Live Video Streaming Sample Application

This sample Angular application demonstrates how to live stream camera feeds from Eagle Eye Networks. To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).



## Setup
Befor you begin, make sure you have Node.js installed on your machine. For more information on installing Node.js, see [nodejs.org](https://nodejs.org/). If you are unsure what version of Node.js runs on your system, run node -v in a terminal window. You'll be using the package manager, npm. Be sure that you include this with your Node.js installation as well.

1. Clone this repository or copy the sample code into your local environment. Then, navigate to the new folder.

```
git clone git@github.com:EENCloud/VMS-Developer-Portal.git
cd "VMS-Developer-Portal/Live Video Angular"
```
   
2. Install dependencies:
```
npm install
```

3. In the directory, `src/app/environments`, create a copy of `example.environment.ts` and rename it `environment.ts`. Update the `CLIENT_ID` and `CLIENT_SECRET` in the file with your application's credentials. For more details on obtaining these credentials, visit our [API documentation](https://developer.eagleeyenetworks.com/docs/client-credentials).


## Running the Application

To start the server:
```
ng serve
```
This will host a local server on `127.0.0.1:3333`.

## Usage

1. Navigate to `http://127.0.0.1:3333` in your web browser.
2. Click on the "Login with Eagle Eye Networks" link to authenticate.
3. Once you log in, you will be redirected to the camera select page.
4. When you select a camera, you'll be taken to the high resolution live stream view of that camera.


## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive [API documentation](https://developer.eagleeyenetworks.com/reference/listcameras).
