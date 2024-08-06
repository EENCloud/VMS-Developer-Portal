// We'll use Express.js to create a simple server
const express = require('express');
const axios = require('axios');
const app = express();

const clientId = 'Your Client ID';
const clientSecret = 'Your Client Secret';

const hostName = '127.0.0.1';
const port = 3333;

// This function will request the access token and refresh token.
const getTokens = async (code) => {
    let endpoint = 'https://auth.eagleeyenetworks.com/oauth2/token'
    let params = new URLSearchParams({
        grant_type: "authorization_code",
        code: code,
        scope: "vms.all",
        redirect_uri: `http://${hostName}:${port}`
    });

    const url = `${endpoint}?${params.toString()}`;
    try {
        const response = await axios.post(url, {}, {       
            auth: {
                username: clientId,
                password: clientSecret
            }
        });
        return response.data;
    } catch (error) {
        console.log(error);
        throw error;
    }
};

// This function will request a new access token using the refresh token.
const refreshToken = async (refresh_token) => {
    let endpoint = 'https://auth.eagleeyenetworks.com/oauth2/token'
    let params = new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: refresh_token,
        scope: "vms.all"
    });
    const url = `${endpoint}?${params.toString()}`;

    try {
        const response = await axios.post(url, {}, {
            auth: {
                username: clientId,
                password: clientSecret
            }
        });
        return response.data;
    } catch (error) {
        console.log(error, "refresh token error");
        throw error;
    }
};

// This function will check if the response is a JSON object and if it contains an access_token
const oauthValid = (oauthObject) => {
    // Check if the response is a JSON object
    try {
        let json_object;
        if(typeof oauthObject === 'string') {
            json_object = JSON.parse(oauthObject);
        } else if(typeof oauthObject === 'object') {
            json_object = oauthObject;
        }
        return 'access_token' in json_object;
    } catch (error) {
        console.log(error, "oauth Valid error");
        return false;
    }
};

// Execution #1: After navigating to http://localhost:3333,
// a link is generated to redirect the user to 
// auth.eagleeyenetworks.com so that they can log in
// to their Eagle Eye Networks account.

// Execution #2: After logging in the user is redirected
// back to the server with a code parameter in the query string
// If a user visits localhost:3333/login this route will be called.
app.get('/', async (req, res) => {

    let endpoint = "https://auth.eagleeyenetworks.com/oauth2/authorize";
    let params = new URLSearchParams({
        client_id: clientId,
        response_type: "code",
        scope: "vms.all",
        redirect_uri: `http://${hostName}:${port}`
    });

    let requestAuthUrl = `${endpoint}?${params.toString()}`;

    const page = `
      <html>
        <head><title>OAuth Testing(Node.JS)</title></head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@3.4.1/dist/css/bootstrap.min.css" integrity="sha384-HSMxcRTRxnN+Bdg0JdbxYKrThecOKuH5zCYotlSAcp1+c8xmyTe9GYg1l9a69psu" crossorigin="anonymous">
        <body>
            <main style="display: flex; justify-content: center; height: 100vh;"> 
                <div class="card" style="width: 55%; margin: 5rem; text-align:center;">
                    <img src="https://upload.wikimedia.org/wikipedia/en/4/46/Eagle_Eye_Networks_logo.png" class="card-img-top" alt="...">
                    <div class="card-body">
                        <h2 class="card-title">OAuth Testing(Node.JS)</h2>
                        <p class="card-text mb-5">This sample Express application demonstrates how to authenticate and obtain an access token using the OAuth2 protocol for the Eagle Eye Networks REST API. To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).</p>
                        <a href='${requestAuthUrl}' class="btn btn-primary" style="margin-top: 5rem;">Login with Eagle Eye Networks</a>
                    </div>
                </div>
            </main>

          <script src="https://cdn.jsdelivr.net/npm/bootstrap@3.4.1/dist/js/bootstrap.min.js" integrity="sha384-aJ21OjlMXNL5UyIl/XNwTMqvzeRMZH2w8c5cRVpzpU8Y5bApTppSuUkhZXN0VxHd" crossorigin="anonymous"></script>
        </body>
      </html>
    `;

    const code = req.query.code;
    if (!code) {
        return res.send(page);
    }
        try {
            // Once the user logs in, they will be redirected back to 
            // localhost:3333 with a CODE. The backend can now request
            // the access_token and refresh_token.
            const tokens = await getTokens(code);
            // check if the response is a JSON object and if it contains an access_token
            if (oauthValid(tokens)) {
                console.log("You're now logged In!", tokens);
                return res.send("You're now logged In!");
            } else if(refresh_token != "") {
                // If the access_token is expired, the refresh_token
                // can be used to get a new access_token.
                const tokens = await refreshToken(refresh_token);
                if (oauthValid(tokens)) {
                    console.log("You're now logged In using your refresh token!");
                    return res.send("You're now logged In using your refresh token!");
                } else {
                    return res.status(400).send('refresh token failed ');
                }

            } else {
                return res.status(400).send('Invalid OAuth refresh token');
            }
        } catch (error) {
            return res.status(500).send(error.toString());
        }

});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`)
});