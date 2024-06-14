// Get API Credentials using OAuth2
// Step 1: Redirect the user to auth.eagleeyenetworks.com
// Step 2: The user will log in to their VMS Account
// Step 3: The user will be redirected back to your application with a CODE
// Step 4: Your application backend/server request the Access token.

// We'll use Express.js to create a simple server
const express = require('express');
const axios = require('axios');
const app = express();

const refresh_token = "";
const clientId = 'yourClientId';
const clientSecret = 'yourClientSecret';
const hostName = '127.0.0.1';
const port = 3333;

const getTokens = async (code) => {
    const url = `https://auth.eagleeyenetworks.com/oauth2/token?grant_type=authorization_code&scope=vms.all&code=${code}&redirect_uri=https://${hostName}:${port}`;

    try {
        const response = await axios.post(url, {}, {
            auth: {
                username: clientId,
                password: clientSecret
            }
        });
        return response.data;
    } catch (error) {
        throw error;
    }
};

const refreshToken = async (refresh_token) => {
    const url = `https://auth.eagleeyenetworks.com/oauth2/token?grant_type=refresh_token&scope=vms.all&refresh_token=${refresh_token}`;

    try {
        const response = await axios.post(url, {}, {
            auth: {
                username: clientId,
                password: clientSecret
            }
        });
        return response.data;
    } catch (error) {
        throw error;
    }
};

const oauthValid = (oauthObject) => {
    try {
        const json_object = JSON.parse(oauthObject);
        return 'access_token' in json_object;
    } catch (error) {
        return false;
    }
};

app.get('/', async (req, res) => {
    const code = req.query.code;
    if (code) {
        try {
            const tokens = await getTokens(code);
            if (oauthValid(tokens)) {
                console.log("You're now logged In!");
                console.log(tokens);
                res.send("You're now logged In!");
            } else if(refresh_token != "") {
                const tokens = await refreshToken(refresh_token);
                if (oauthValid(tokens)) {
                    console.log("You're now logged In using your refresh token!");
                    console.log(tokens);
                    res.send("You're now logged In using your refresh token!");
                } else {
                    res.status(400).send('refresh token failed ');
                }

            } else {
                res.status(400).send('Invalid OAuth object');
            }
        } catch (error) {
            res.status(500).send(error.toString());
        }
    } else {
        res.send('No code provided');
    }
});

// Executing step 1, a link is generated to redirect the user to
// auth.eagleeyenetworks.com
  app.get('/', (req, res) => {
    let endpoint = "https://auth.eagleeyenetworks.com/oauth2/authorize";
    let requestAuthUrl = `${endpoint}?client_id=${clientId}&response_type=code&scope=vms.all&redirect_uri=https://${hostName}:${String(port)}`;

    const page = `
      <html>
        <head><title>OAuth Testing(Node.JS)</title></head>
        <body>
          <h1>OAuth Testing(Node.JS)</h1>
          <a href='${requestAuthUrl}'>Login with Eagle Eye Networks</a>
        </body>
      </html>
    `;
    res.send(page);
  });


app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});

// I could add a .env file to store the credentials and the refresh token.
// I could use express.static to serve static html, JavaScript file.