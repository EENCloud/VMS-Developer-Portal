function fetchWithAuthentication(url, authToken) {
  const headers = new Headers();
  headers.set(
    'Authorization', `Bearer ${authToken}`,
    'Accept', 'image/jpeg'
  );
  return fetch(url, { headers });
}

async function displayProtectedImage(
  imageId, imageUrl, authToken
) {
  // Fetch the image.
  const response = await fetchWithAuthentication(
    imageUrl, authToken
  );

  // Create an object URL from the data.
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);

  // Update the source of the image.
  const imageElement = document.getElementById(imageId);
  imageElement.src = objectUrl;
  imageElement.onload = () => {
    URL.revokeObjectURL(objectUrl);
  };
}


// const imageId = 'some-image';
// const imageUrl = 'https://api.c???.eagleeyenetworks.com/secret-image.png';
// const authToken = 'access_token';
// displayProtectedImage(imageId, imageUrl, authToken);
