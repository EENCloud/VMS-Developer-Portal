// We'll use Express.js to create a simple server
const express = require('express');
const axios = require('axios');
const app = express();

const refresh_token = "";
const clientId = '';
const clientSecret = '';
const hostName = '127.0.0.1';
const port = 3333;

// Declaring an asynchronous function named getTokens that takes a code parameter
// const getTokens = async (code) => {
//     console.log(code);
//     const url = `https://auth.eagleeyenetworks.com/oauth2/token?grant_type=authorization_code&scope=vms.all&code=${code}&redirect_uri=https://${hostName}:${port}`;

//     try {
//         const response = await axios.post(url, {}, {
//             auth: {
//                 username: clientId,
//                 password: clientSecret
//             }
//         });
//         console.log(response.data);
//         return response.data;
//     } catch (error) {
//         console.log(error);
//         throw error;
//     }
// };

// const refreshToken = async (refresh_token) => {
//     console.log(refresh_token);
//     const url = `https://auth.eagleeyenetworks.com/oauth2/token?grant_type=refresh_token&scope=vms.all&refresh_token=${refresh_token}`;

//     try {
//         const response = await axios.post(url, {}, {
//             auth: {
//                 username: clientId,
//                 password: clientSecret
//             }
//         });
//         console.log(response.data)
//         return response.data;
//     } catch (error) {
//         console.log(error);
//         throw error;
//     }
// };

// const oauthValid = (oauthObject) => {
//     console.log(oauthObject);
//     try {
//         const json_object = JSON.parse(oauthObject);
//         console.log(json_object);
//         return 'access_token' in json_object;
//     } catch (error) {
//         console.log(error);
//         return false;
//     }
// };

// Executing step 1, a link is generated to redirect the user to
// auth.eagleeyenetworks.com
// app.get('/login', (req, res) => {
//     console.log('hit 2');
//     let endpoint = "https://auth.eagleeyenetworks.com/oauth2/authorize";
//     let requestAuthUrl = `${endpoint}?client_id=${clientId}&response_type=code&scope=vms.all&redirect_uri=http://${hostName}:${port}`;

//     const page = `
//       <html>
//         <head><title>OAuth Testing(Node.JS)</title></head>
//         <body>
//           <h1>OAuth Testing(Node.JS)</h1>
//           <a href='${requestAuthUrl}'>Login with Eagle Eye Networks</a>
//         </body>
//       </html>
//     `;
//     res.send(page);
//   });

// app.get('/', async (req, res) => {
//     console.log('hit');
//     const code = req.query.code;
//     console.log(code);
//     if (code) {
//         try {
//             const tokens = await getTokens(code);
//             if (oauthValid(tokens)) {
//                 console.log("You're now logged In!");
//                 console.log(tokens);
//                 res.send("You're now logged In!");
//             } else if(refresh_token != "") {
//                 const tokens = await refreshToken(refresh_token);
//                 if (oauthValid(tokens)) {
//                     console.log("You're now logged In using your refresh token!");
//                     console.log(tokens);
//                     res.send("You're now logged In using your refresh token!");
//                 } else {
//                     res.status(400).send('refresh token failed ');
//                 }

//             } else {
//                 res.status(400).send('Invalid OAuth object');
//             }
//         } catch (error) {
//             res.status(500).send(error.toString());
//         }
//     } else {
//         res.send('No code provided');
//     }
// });


app.listen(port, () => {
    console.log(`Server is running on http://${hostName}:${port}`);
});

// I could add a .env file to store the credentials and the refresh token.
// I could use express.static to serve static html, JavaScript file.