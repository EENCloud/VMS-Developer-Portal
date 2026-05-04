# Core Function 1: authenticate

## Purpose

Exchanges an OAuth 2.0 authorization code for an access token and refresh token. This is the entry point to all authenticated API access. The response also contains the **per-account base URL** (`httpsBaseUrl`) required to construct every subsequent API request correctly.

This function must be called once per user, after they have granted authorization via the browser-based consent flow. After this, `refreshAccessToken` handles all subsequent token acquisition without user involvement.

---

## Prerequisites

Before calling this function, two things must happen:

1. **Client credentials must exist.** A `client_id` and `client_secret` are obtained by registering an application at the Eagle Eye Developer Portal. These credentials identify your application — they are never shown to end users.

2. **The user must have authorized your app.** Redirect the user's browser to the authorization URL below. After login and consent, Eagle Eye redirects to your `redirect_uri` with a `?code=` query parameter. That code is what this function consumes.

### Authorization URL (redirect the user here)

```
https://auth.eagleeyenetworks.com/oauth2/authorize
  ?scope=vms.all
  &client_id={clientId}
  &response_type=code
  &redirect_uri={redirectUri}
```

- `redirect_uri` must exactly match a pre-whitelisted URI. String comparison is exact — `http://127.0.0.1:3333` is not the same as `http://localhost:3333`.
- The authorization code in the redirect expires in **5 minutes**.
- **Do NOT use `URLSearchParams` or `encodeURIComponent` to build this URL in the browser.** These encode `://` as `%3A%2F%2F` and `:` as `%3A`, producing a percent-encoded redirect_uri that EEN does not match against the whitelisted value, resulting in a rejected authorization. Build the URL using string concatenation or a template literal:
  ```typescript
  const authUrl =
    `https://auth.eagleeyenetworks.com/oauth2/authorize` +
    `?scope=vms.all` +
    `&client_id=${clientId}` +
    `&response_type=code` +
    `&redirect_uri=${redirectUri}` // redirect_uri is NOT encoded here
  ```

---

## HTTP Request

**Endpoint:** `POST https://auth.eagleeyenetworks.com/oauth2/token`

This is a fixed URL — it does not use the per-account base URL.

> **Browser SPA / CORS warning:** `auth.eagleeyenetworks.com` does not set CORS headers that allow direct `fetch()` calls from browser pages. If you are building a browser-based app (React, Vue, plain JS), your token exchange request will fail with a CORS error unless you route it through a proxy. With Vite, add a dev server proxy:
> ```typescript
> // vite.config.ts
> server: {
>   proxy: {
>     '/oauth2': {
>       target: 'https://auth.eagleeyenetworks.com',
>       changeOrigin: true,
>       secure: true,
>     },
>   },
> }
> ```
> Then fetch `/oauth2/token` (relative) instead of the absolute URL. For production, use a server-side token exchange endpoint.

### Headers

| Header | Value |
|---|---|
| `Authorization` | `Basic {base64(clientId:clientSecret)}` |
| `Content-Type` | `application/x-www-form-urlencoded` |
| `Accept` | `application/json` |

The `Authorization` header uses HTTP Basic Auth. Encode `clientId:clientSecret` as a single Base64 string.

### Request Body (form-encoded)

| Field | Value |
|---|---|
| `grant_type` | `authorization_code` |
| `scope` | `vms.all` |
| `code` | The code from the redirect query parameter |
| `redirect_uri` | Must exactly match the one used in the authorization URL |

---

## Response

```json
{
  "access_token": "eyJraWQiOiI2ODYxYjBjYS...",
  "expires_in": 43198,
  "refresh_token": "w1P0nwA7NEZmo5tEd76cco3y5bi4Js6Q...",
  "httpsBaseUrl": {
    "hostname": "api.c001.eagleeyenetworks.com",
    "port": 443
  },
  "scope": "vms.all",
  "token_type": "Bearer"
}
```

### Critical fields

| Field | Notes |
|---|---|
| `access_token` | JWT. Valid for up to **12 hours**. Use as `Authorization: Bearer {token}` on all API calls. |
| `refresh_token` | Use with `refreshAccessToken` to get new access tokens without re-prompting the user. |
| `expires_in` | Seconds until the access token expires. |
| `httpsBaseUrl.hostname` | The cluster-specific base hostname for this account, e.g. `api.c001.eagleeyenetworks.com`. **All API calls must use this hostname.** Store it alongside the tokens. |

---

## Base URL Usage

The `httpsBaseUrl.hostname` is account-specific. Every API call after authentication must be constructed as:

```
https://{httpsBaseUrl.hostname}/api/v3.0/{endpoint}
```

Example:
```
https://api.c001.eagleeyenetworks.com/api/v3.0/cameras
```

If you do not yet have a base URL (e.g. you only have stored tokens), you can retrieve it from:
```
GET https://api.eagleeyenetworks.com/api/v3.0/clientSettings
Authorization: Bearer {access_token}
```

---

## Error Cases

| HTTP Status | Meaning |
|---|---|
| `400` | Malformed request, invalid `grant_type`, or mismatched `redirect_uri` |
| `401` | Invalid or expired authorization code, or wrong client credentials |
| `403` | Client not authorized for this scope |

Authorization codes expire after 5 minutes. If the code is expired, the user must be sent through the authorization flow again.

---

## Code Examples

### Python

```python
import requests
import base64

def authenticate(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = requests.post(
        "https://auth.eagleeyenetworks.com/oauth2/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data={
            "grant_type": "authorization_code",
            "scope": "vms.all",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    response.raise_for_status()
    return response.json()
    # Returns: { access_token, refresh_token, expires_in, httpsBaseUrl, ... }
```

### TypeScript

```typescript
async function authenticate(
  clientId: string,
  clientSecret: string,
  code: string,
  redirectUri: string
): Promise<{
  access_token: string;
  refresh_token: string;
  expires_in: number;
  httpsBaseUrl: { hostname: string; port: number };
}> {
  const credentials = btoa(`${clientId}:${clientSecret}`);

  const response = await fetch("https://auth.eagleeyenetworks.com/oauth2/token", {
    method: "POST",
    headers: {
      Authorization: `Basic ${credentials}`,
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      scope: "vms.all",
      code,
      redirect_uri: redirectUri,
    }),
  });

  if (!response.ok) {
    throw new Error(`Authentication failed: ${response.status} ${await response.text()}`);
  }

  return response.json();
}
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public record TokenResponse(
    string AccessToken,
    string RefreshToken,
    int ExpiresIn,
    JsonElement HttpsBaseUrl
);

public static async Task<TokenResponse> Authenticate(
    string clientId,
    string clientSecret,
    string code,
    string redirectUri)
{
    using var client = new HttpClient();

    var credentials = Convert.ToBase64String(Encoding.UTF8.GetBytes($"{clientId}:{clientSecret}"));
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Basic", credentials);
    client.DefaultRequestHeaders.Accept.Add(
        new MediaTypeWithQualityHeaderValue("application/json"));

    var body = new FormUrlEncodedContent(new[]
    {
        new KeyValuePair<string, string>("grant_type", "authorization_code"),
        new KeyValuePair<string, string>("scope", "vms.all"),
        new KeyValuePair<string, string>("code", code),
        new KeyValuePair<string, string>("redirect_uri", redirectUri),
    });

    var response = await client.PostAsync(
        "https://auth.eagleeyenetworks.com/oauth2/token", body);
    response.EnsureSuccessStatusCode();

    var json = await response.Content.ReadAsStringAsync();
    var doc = JsonSerializer.Deserialize<JsonElement>(json);

    return new TokenResponse(
        AccessToken: doc.GetProperty("access_token").GetString()!,
        RefreshToken: doc.GetProperty("refresh_token").GetString()!,
        ExpiresIn: doc.GetProperty("expires_in").GetInt32(),
        HttpsBaseUrl: doc.GetProperty("httpsBaseUrl")
    );
}
```

### Rust

```rust
use base64::{engine::general_purpose, Engine as _};
use reqwest::Client;
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct HttpsBaseUrl {
    pub hostname: String,
    pub port: u16,
}

#[derive(Debug, Deserialize)]
pub struct TokenResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub expires_in: u64,
    pub https_base_url: Option<HttpsBaseUrl>,
}

pub async fn authenticate(
    client_id: &str,
    client_secret: &str,
    code: &str,
    redirect_uri: &str,
) -> Result<TokenResponse, reqwest::Error> {
    let credentials = general_purpose::STANDARD
        .encode(format!("{}:{}", client_id, client_secret));

    let client = Client::new();
    let params = [
        ("grant_type", "authorization_code"),
        ("scope", "vms.all"),
        ("code", code),
        ("redirect_uri", redirect_uri),
    ];

    let response = client
        .post("https://auth.eagleeyenetworks.com/oauth2/token")
        .header("Authorization", format!("Basic {}", credentials))
        .header("Accept", "application/json")
        .form(&params)
        .send()
        .await?
        .error_for_status()?
        .json::<TokenResponse>()
        .await?;

    Ok(response)
}
```

---

## Notes

- **Confidential clients** (server-side apps with a secure backchannel) receive both an `access_token` and `refresh_token`. Use this flow.
- **Public clients** (browser/mobile apps that cannot securely store secrets) only receive a temporary `access_token`. The `refresh_token` field will be absent.
- Never expose `client_secret` or `refresh_token` to end users or in client-side code.
- Store the `httpsBaseUrl.hostname` alongside your tokens — it is needed for all API calls.
