# Eagle Eye Networks Roles API

This repository provides an example application demonstrating the creation and management of roles using the Eagle Eye Networks API. To use this application, you need an Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For details on application registration, consult the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).

## Prerequisites

Before using the Roles API:

1. Ensure you have valid API credentials, including `CLIENT_ID` and `CLIENT_SECRET`. These can be obtained by registering an application with the Eagle Eye Networks Developer Program.
2. Verify that your account has the necessary permissions to manage roles.

## Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**

   - Create a copy of `example.flaskenv` and rename it `.flaskenv`:

      ```bash
      cp example.flaskenv .flaskenv
      ```

   - Update `.flaskenv` with your credentials:

      ```env
      CLIENT_ID=<your_client_id>
      CLIENT_SECRET=<your_client_secret>
      SECRET_KEY=<your_flask_secret> 
      ```

4. **Configure Flask**

Ensure the `FLASK_APP` environment variable is set to `main.py`:

   ```bash
   export FLASK_APP=main.py
   ```

## Running the Application

Start the Flask development server:

   ```bash
   python -m flask run
   ```

By default, the application will be available at `http://127.0.0.1:3333`.

## Features and Usage

1. **Login**

   - Navigate to `http://127.0.0.1:3333`.
   - Click on the "Login with Eagle Eye Networks" link to authenticate using your API credentials.

2. **Role Management**

   - After login, you can create, update, and delete roles using the API endpoints provided by the application.

## Additional Resources

- For detailed API functionality and examples, refer to the [Eagle Eye Networks API documentation](https://developer.eagleeyenetworks.com/docs).
- Learn about the available role types and their use cases in the [Roles API documentation](https://developer.eagleeyenetworks.com/reference/roles).

## Troubleshooting

- Ensure your `.flaskenv` file contains valid credentials.
- If the server fails to start, verify that all dependencies are installed and that `FLASK_APP` is correctly configured.
- For authentication errors, confirm that your `CLIENT_ID` and `CLIENT_SECRET` match the credentials registered with the API.

## Support

For further assistance, contact [Eagle Eye Networks API Support](mailto:api_support@een.com) or consult the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).
