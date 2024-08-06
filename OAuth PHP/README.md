# Eagle Eye Networks OAuth Sample

This sample PHP server demonstrates how to authenticate and obtain an access token using the OAuth2 protocol for the Eagle Eye Networks REST API. To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).

## Requirements

- [vlucas/phpdotenv](https://github.com/vlucas/phpdotenv)

## Setup


1. Clone this repository or copy the sample code into your local environment.

2. Install dependencies:
```
composer install
```

3. Create a copy of `example.env` and rename it `.env`. Update the `CLIENT_ID` and `CLIENT_SECRET` in the file with your application's credentials. For more details on obtaining these credentials, visit our [API documentation](https://developer.eagleeyenetworks.com/docs/client-credentials).

## Running the Application

To start the server, run the following command in the terminal:
```
php -S 127.0.0.1:3333
```
This will host a local server on `127.0.0.1:3333`.

## Usage

1. Navigate to `http://127.0.0.1:3333` in your web browser.
2. Click on the "Login with Eagle Eye Networks" link to authenticate.
3. You will be redirected to `auth.eagleeyenetworks.com` to where you can log in to your Eagle Eye Networks VMS account.
4. After logging in, you will be redirected back to your application with a `code`.
5. The application will automatically exchange this code for an access token and refresh token.


> [!WARNING]  
> In production, ensure that your client secret is securely stored and never expose sensitive tokens in client-facing interfaces.

## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive API documentation.