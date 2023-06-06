**Creating a Local Server-Side Proxy with Node.js and Express to Bypass CORS Restrictions**

In this guide, we'll walk you through setting up a simple server-side proxy using Node.js and Express to fetch a video with the appropriate headers and serve it to your client-side application. This will bypass CORS restrictions that may occur when using JavaScript to fetch the video with an Authorization header.

**Prerequisites**  
Node.js is installed on your local machine. If you don't have it installed, you can download it from <https://nodejs.org>.

**Step 1: Set up the project**

1. Create a new directory for your project and navigate to it in the terminal.
2. Run the following commands to set up the project:

```shell
npm init -y
npm install express node-fetch
```

**Step 2: Login**

Login to your account and get an access token as described here.

**Step 3: Base-URL**

Find your Base-URL as described here.

**Step 4: Get camera ID**

Get a list of the cameras in your account and take one of the camera IDs as described here.

**Step 5: Create the server-side proxy**

Create a file named server.js in your project directory and add the following code: (Please replace your retrieved MP4 URL in the below example) 

```javascript
import express from 'express';
import fetch from 'node-fetch';

const app = express();
const PORT = 3333;

app.use(express.static('public'));

app.get('/fetch-video', async (req, res) => {
  const videoURL = '<The URL that is returned by the /media API>';
  const token = 'your_real_access_token';

  try {
    const response = await fetch(videoURL, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.status === 200) {
      response.body.pipe(res);
    } else {
      res.status(response.status).send(response.statusText);
    }
  } catch (error) {
    res.status(500).send(error.message);
  }
});

app.listen(PORT, () => {
  console.log(`Server is running at http://127.0.0.1:${PORT}`);
});

```

> 🚧 
> 
> Make sure to replace 'your_real_access_token' with your actual access token.

**Step 6: Create the client-side application**

1. Create a new folder named public inside your project directory.
2. In the "public" folder, create an "index.html" file with the following code:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MP4 Video Player</title>
</head>
<body>
  <video id="videoPlayer" controls>
    <source src="/fetch-video" type="video/mp4">
    Your browser does not support the video tag.
  </video>
</body>
</html>

```

**Step 7: Update the package.json file**

Add "type": "module" to your package.json file, so it looks like this:

```json
{
  "name": "proxy",
  "version": "1.0.0",
  "description": "",
  "main": "server.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [],
  "author": "",
  "license": "ISC",
  "dependencies": {
    "express": "^4.17.3",
    "node-fetch": "^3.1.2"
  },
  "type": "module"
}

```

**Step 8: Run the server**

1. In the terminal, navigate to your project directory.
2. Run the following command to start the server:

```shell
node server.js
```

**Finally:** Open your browser and visit <http://127.0.0.1:3333>. You should see the video player and be able to play the video without encountering CORS restrictions.

That's it! You have successfully created a local server-side proxy with Node.js and Express to bypass CORS restrictions and fetch a video using an Authorization header.
