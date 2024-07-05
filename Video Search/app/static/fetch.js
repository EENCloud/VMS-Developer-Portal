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


// const getBlobImageURL = (blobData: ArrayBufferLike) => {
//   const arrayBufferView = new Uint8Array(blobData);
//   const blob = new Blob([arrayBufferView], { type: 'image/jpeg' });
//   const urlCreator = window.URL || window.webkitURL;

//   return urlCreator.createObjectURL(blob);
// };



// const imageId = 'some-image';
// const imageUrl = 'https://api.example.com/secret-image.png';
// const authToken = 'changeme';
// displayProtectedImage(imageId, imageUrl, authToken);

