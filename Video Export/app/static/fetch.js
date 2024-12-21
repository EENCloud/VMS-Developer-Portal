function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function fetchWithAuthentication(url, authToken) {
  const headers = new Headers();
  headers.set(
    'Authorization', `Bearer ${authToken}`,
    'Accept', 'image/jpeg'
  );
  return fetch(url, { headers });
}

async function displayProtectedImage(imageId, imageUrl, authToken, retries = 5, backoff = 500) {
  try {
      const response = await fetchWithAuthentication(imageUrl, authToken);

      if (!response.ok) {
          // If we got a 429 status and we still have retries left, wait and retry
          if (response.status === 429 && retries > 0) {
              const retryAfter = parseInt(response.headers.get('Retry-After')) || backoff;
              console.warn(`Rate-limited: Retrying image ${imageId} in ${retryAfter}ms`);
              await delay(retryAfter);
              return await displayProtectedImage(imageId, imageUrl, authToken, retries - 1, backoff * 2);
          }

          // Any other error or no more retries left
          throw new Error(`Error fetching image ${imageId}: ${response.status} ${response.statusText}`);
      }

      // Successfully fetched the image; display it
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);

      const imageElement = document.getElementById(imageId);
      imageElement.src = objectUrl;
      imageElement.onload = () => {
        URL.revokeObjectURL(objectUrl);
      };
  } catch (error) {
      // If the error is a network error or something else where we can try again
      // treat it similarly to the 429 scenario if applicable.
      if (retries > 0 && error instanceof Response && error.status === 429) {
          const retryAfter = parseInt(error.headers.get('Retry-After')) || backoff;
          console.warn(`Rate-limited (fetch error): Retrying image ${imageId} in ${retryAfter}ms`);
          await delay(retryAfter);
          return await displayProtectedImage(imageId, imageUrl, authToken, retries - 1, backoff * 2);
      } else {
          console.error(`Error displaying image ${imageId}:`, error);
      }
  }
}


// const imageId = 'some-image';
// const imageUrl = 'https://api.c???.eagleeyenetworks.com/secret-image.png';
// const authToken = 'access_token';
// displayProtectedImage(imageId, imageUrl, authToken);
