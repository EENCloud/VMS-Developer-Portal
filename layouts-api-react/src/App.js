import React, { useState, useEffect } from 'react';
import './App.css';

function App() {

  /*
    Please take a look at the following starting code I have provided. You
    will need to finish the application using the API instructions and notes
    within this code. We will go one piece at a time until all missing code
    has been filled in. Please make sure to remove all notes from the code so
    that we are not taking unnecessary space.
  */

  //States and Authentication
  const clientId = '9ac2f9086c5743788e5dad1bba79b22d'
  const clientSecret = 'BzKo}JvKMoPec[3*F?/('
  const redirectUrl = 'https://localhost:3333'

  //Add any additional states you think are needed
  const [token, setToken] = useState('');
  const [layouts, setLayouts] = useState([]);
  const [layout, setLayout] = useState([]);
  const [panes, setPanes] = useState([]);
  const [pane, setPane] = useState([]);
  const [settings, setSettings] = useState([]);
  const [layoutName, setLayoutName] = useState([]);
  const [cameras, setCameras] = useState([]);

  //Data Fetches
  const fetchTokens = async (authCode) => {
    const authUrl = 'https://auth.eagleeyenetworks.com/oauth2/token';
    const headers = new Headers({
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': 'Basic ' + btoa(`${clientId}:${clientSecret}`),
      'Accept': 'application/json',
    });
  
    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      scope: 'vms.all',
      code: authCode,
      redirect_uri: redirectUrl,
    });
  
    try {
      const response = await fetch(authUrl, {
        method: 'POST',
        headers: headers,
        body: body.toString(),
      });
      const data = await response.json();
      return data.access_token;
    } catch (error) {
      console.error('Error fetching token:', error);
    }
  };  
  const fetchLayouts = async (token) => {
    const options = {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    };
  
    try {
      const response = await fetch('https://api.c001.eagleeyenetworks.com/api/v3.0/layouts?pageToken=b2Zmc2V0PTEwJmxpbWl0PTEw&pageSize=100', options);
      const data = await response.json();
      setLayouts(data);
    } catch (error) {
      console.error('Error fetching layouts:', error);
    }
  };
  const fetchCameras = () => {
    //Insert Camera fetching here
  };

  //Layout Editing
  const createLayout = () => {
    //Insert Layout creation here
  };
  const deleteLayout = () => {
    //Insert Layout deletion here
  };
  const editLayout = () => {
    //Insert Layout editing here
  };
  const editPane = () => {
    //Insert Layout editing here
  };

  //Effects
  useEffect(() => {
    async function getToken() {
      const authCode = ''; // Set this to your auth code
      if (authCode) {
        const fetchedToken = await fetchTokens(authCode);
        setToken(fetchedToken);
      }
    }
    getToken();
  }, []);
  
  useEffect(() => {
    if (token) {
      fetchLayouts(token);
    }
  }, [token]);

  return (
    <div className="App">
      <nav>
        <h1>Layouts API Test</h1>
        <select>
          <option value="create">Create</option>
          <option value="edit">Edit</option>
          <option value="delete">Delete</option>
        </select>
      </nav>
      <main>
        <section>
          <h2>Selected Layout</h2>
          <p>{layoutName}</p>
          {/* Iterate over panes and display them */}
          {panes.map((pane, index) => (
            <div key={index}>
              <p>Camera {index + 1}</p>
              {/* Display camera view here if possible */}
            </div>
          ))}
        </section>
        <aside>
          <select onChange={(e) => setLayout(e.target.value)}>
            {layouts.map((layout) => (
              <option key={layout.id} value={layout.id}>{layout.name}</option>
            ))}
          </select>
          <div>
            <h3>Layout Settings</h3>
            <p>{JSON.stringify(settings)}</p>
            <select onChange={(e) => setPane(e.target.value)}>
              {panes.map((pane, index) => (
                <option key={index} value={index}>Pane {index + 1}</option>
              ))}
            </select>
            <button onClick={() => editPane()}>Edit Pane</button>
          </div>
        </aside>
        {/* Add modal here for editing pane */}
      </main>
    </div>
  );    
}

export default App;
