import React, { useState, useEffect } from 'react';
import './App.css';

function App() {

  //States and Authentication
  const clientId = '9ac2f9086c5743788e5dad1bba79b22d'
  const clientSecret = 'BzKo}JvKMoPec[3*F?/('
  const redirectUrl = 'http://127.0.0.1:3333'

  //Add any additional states you think are needed
  const [token, setToken] = useState('');
  const [layouts, setLayouts] = useState([]);
  const [layout, setLayout] = useState(null);
  const [panes, setPanes] = useState([]);
  const [pane, setPane] = useState([]);
  const [settings, setSettings] = useState([]);
  const [layoutName, setLayoutName] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [feeds, setFeeds] = useState({});
  const [showOptions, setShowOptions] = useState(false);

  //Data Fetches
  const fetchTokens = async (authCode) => {
    const authUrl = 'https://auth.eagleeyenetworks.com/oauth2/token';
    const headers = new Headers({
      'Accept': 'application/json',
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': 'Basic ' + btoa(`${clientId}:${clientSecret}`),
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
      // Store the refresh token securely, if needed
      const refreshToken = data.refresh_token;
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
      const response = await fetch('https://api.c001.eagleeyenetworks.com/api/v3.0/layouts', options);
      const data = await response.json();
      console.log('Layouts fetched:', data);  // Log the fetched data to check its structure
      setLayouts(data.results);
    } catch (error) {
      console.error('Error fetching layouts:', error);
    }
  };  
  const fetchCameras = async (token) => {
    const options = {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    };
  
    try {
      const response = await fetch('https://api.c001.eagleeyenetworks.com/api/v3.0/cameras', options);
      const data = await response.json();
      console.log('Cameras fetched:', data);
      setCameras(data.results);
    } catch (error) {
      console.error('Error fetching cameras:', error);
    }
  };
  const fetchCameraFeeds = async (token, cameraId) => {
    const options = {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    };
  
    try {
      const response = await fetch(`https://api.c001.eagleeyenetworks.com/api/v3.0/feeds?deviceId=${cameraId}&type=preview&pageSize=100`, options);
      const data = await response.json();
      console.log('Camera feeds fetched:', data.results);
      return data;
    } catch (error) {
      console.error('Error fetching camera feeds:', error);
    }
  };   

  //Layout Editing
  const handleOptions = () => {
    if (!showOptions) {
      setShowOptions(true);
    } else {
      setShowOptions(false);
    }
  };
  const createLayout = () => {
    //Insert Layout creation here
  };
  const deleteLayout = async (layoutId) => {
    const options = {
      method: 'DELETE',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    };
  
    try {
      const response = await fetch(`https://api.c001.eagleeyenetworks.com/api/v3.0/layouts/${layoutId}`, options);
      if (response.ok) {
        // Layout deleted successfully
        setLayouts(layouts.filter(layout => layout.id !== layoutId));
        setLayout(null); // Clear the selected layout
        setSettings({});
        setPanes([]);
      } else {
        console.error('Failed to delete layout:', response.statusText);
      }
    } catch (error) {
      console.error('Error deleting layout:', error);
    }
  };  
  const editLayout = async () => {
    const options = {
      method: 'PATCH',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: layout.name,
        settings,
        panes,
      }),
    };
  
    try {
      const response = await fetch(`https://api.c001.eagleeyenetworks.com/api/v3.0/layouts/${layout.id}`, options);
      const data = await response.json();
      setLayout(data);
      fetchLayouts(token); // Refresh the layouts
    } catch (error) {
      console.error('Error updating layout:', error);
    }
  };  
  const editPane = async () => {
    const updatedPanes = panes.map(p => (p.id === pane.id ? pane : p));
    setPanes(updatedPanes);
  
    editLayout();
  };  
  const handleLayoutNameChange = (e) => {
    setLayout((prevLayout) => ({
      ...prevLayout,
      name: e.target.value,
    }));
  };
  const handleLayoutSettingsChange = (key, value) => {
    setSettings((prevSettings) => ({
      ...prevSettings,
      [key]: value,
    }));
  };
  const handlePaneChange = (key, value) => {
    setPane((prevPane) => ({
      ...prevPane,
      [key]: value,
    }));
  };   

  //Effects
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const authCode = urlParams.get('code');
  
    if (authCode) {
      fetchTokens(authCode).then(token => {
        setToken(token);
        window.history.pushState({}, document.title, '/');
      });
    } else {
      window.location.href = `https://auth.eagleeyenetworks.com/oauth2/authorize?response_type=code&client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUrl)}&scope=vms.all`;
    }
  }, []);
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
    if (layout) {
      setSettings(layout.settings);
      setPanes(layout.panes);
  
      layout.panes.forEach(async (pane) => {
        const feedData = await fetchCameraFeeds(token, pane.cameraId);
        setFeeds((prevFeeds) => ({
          ...prevFeeds,
          [pane.cameraId]: feedData,
        }));
      });
    }
  }, [layout]);
  useEffect(() => {
    if (token) {
      fetchLayouts(token);
      fetchCameras(token);
    }
  }, [token]);  

  return (
    <div className="App">
      <nav className="nav">
        <h1>Layouts API Test</h1>
        <button onClick={handleOptions}>Options</button>
      </nav>
      <main>
        <section className="layouts">
          {Array.isArray(panes) && panes.map((pane, index) => (
            <div key={index}>
              <p>{pane.name}</p>
              <p>Camera ID: {pane.cameraId}</p>
              {feeds[pane.cameraId] && (
                <img src={feeds[pane.cameraId].preview_image_url} alt={`Camera ${pane.cameraId} feed`} />
              )}
            </div>
          ))}
        </section>
        <aside className="panel">
          <label>Select Layout</label>
          <div className="spacer"/>
          <select onChange={(e) => setLayout(layouts.find(l => l.id === e.target.value))}>
            <option key='' value=''></option>
            {Array.isArray(layouts) && layouts.map((layout) => (
              <option key={layout.id} value={layout.id}>{layout.name}</option>
            ))}
          </select>
          <div className="spacer"/>
          <div>
            <h3>Layout Settings</h3>
            <div className="spacer"/>
            Camera Border: 
            <input 
              type='checkbox' 
              checked={settings.showCameraBorder} 
              onChange={(e) => setSettings({ ...settings, showCameraBorder: e.target.checked })}>
            </input>
            <div className="spacer"/>
            Camera Name: 
            <input 
              type='checkbox' 
              checked={settings.showCameraName} 
              onChange={(e) => setSettings({ ...settings, showCameraName: e.target.checked })}>
            </input>
            <div className="spacer"/>
            Aspect Ratio: 
              <select 
                value={settings.cameraAspectRatio} 
                onChange={(e) => setSettings({ ...settings, cameraAspectRatio: e.target.value })}>
                <option key='' value=''></option>
                <option value="16x9">16x9</option>
                <option value="4x3">4x3</option>
              </select>
            <div className="spacer"/>
            Pane Columns: 
              <select 
                value={settings.paneColumns} 
                onChange={(e) => setSettings({ ...settings, paneColumns: parseInt(e.target.value) })}>
                <option key='' value=''></option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
              </select>
            <div className="spacer"/>
            <div className="spacer"/>
            <div className="spacer"/>
            <h3>Pane Settings</h3>
            <div className="spacer"/>
            Select Pane
            <select onChange={(e) => setPane(panes.find(p => p.id === parseInt(e.target.value)))}>
              <option key='' value=''></option>
              {Array.isArray(panes) && panes.map((pane, index) => (
                <option key={index} value={pane.id}>Pane {index + 1}</option>
              ))}
            </select>
            <div className="spacer"/>
            Pane Name: 
            <input 
              value={pane?.name || ''} 
              onChange={(e) => setPane({ ...pane, name: e.target.value })}>
            </input>
            <div className="spacer"/>
            Pane Camera:
            <select value={pane?.cameraId || ''} onChange={(e) => setPane({ ...pane, cameraId: e.target.value })}>
              <option key='' value=''></option>
              {Array.isArray(cameras) && cameras.map(camera => (
                <option key={camera.id} value={camera.id}>{camera.name}</option>
              ))}
            </select>
            <div className="spacer"/>
            Pane Size:
            <select 
              value={pane?.size || ''} 
              onChange={(e) => setPane({ ...pane, size: parseInt(e.target.value) })}>
              <option value=''></option>
              <option value='1'>1</option>
              <option value='2'>2</option>
              <option value='3'>3</option>
            </select>
            <div className="spacer"/>
            Feed Type: Preview
            <div className="spacer"/>
            <button onClick="">Add Pane</button>
            <button onClick={() => editPane()}>Edit Pane</button>
            <div className="spacer"/>
            <button onClick={() => editLayout()}>Update Layout</button>
          </div>
        </aside>
      </main>
      {showOptions && (
        <div className="menu">
          <button onClick={createLayout}>Create Layout</button>
          <button onClick={() => deleteLayout(layout.id)}>Delete Layout</button>
        </div>
      )}
    </div>
  );  
}

export default App;
