# Core Function 2: refreshAccessToken

## Purpose

Exchanges a refresh token for a new access token without requiring user interaction. This is the M2M (machine-to-machine) counterpart to `authenticate`. Any integration running longer than 12 hours — or that needs to survive process restarts — must use this function.

---

## When to Call This

Call `refreshAccessToken` when:
- The access token has expired (or is within a short window of expiring)
- Your application restarts and needs to re-establish an active session
- You receive a `401 Unauthorized` response on any API call

**Token lifetimes:**
| Token | Default lifetime |
|---|---|
| Access token | Up to **12 hours** (watch `expires_in` in the response) |
| Refresh token (inactive) | **14 days** from last use — use it or lose it |
| Refresh token (absolute max) | **90 days** from original Phase 1 authorization |

After the 90-day maximum, the user must re-authorize via the browser flow (`authenticate`). Design your application to handle this gracefully.

---

## HTTP Request

**Endpoint:** `POST https://auth.eagleeyenetworks.com/oauth2/token`

This is the same fixed URL as `authenticate`. It does not use the per-account base URL.

### Headers

| Header | Value |
|---|---|
| `Authorization` | `Basic {base64(clientId:clientSecret)}` |
| `Content-Type` | `application/x-www-form-urlencoded` |
| `Accept` | `application/json` |

### Request Body (form-encoded)

| Field | Value |
|---|---|
| `grant_type` | `refresh_token` |
| `scope` | `vms.all` |
| `refresh_token` | The refresh token from the previous `authenticate` or `refreshAccessToken` call |

---

## Response

Identical in shape to the `authenticate` response:

```json
{
  "access_token": "eyJraWQiOiI2ODYxYjBjYS...",
  "expires_in": 25734,
  "refresh_token": "Mp4k-iSQYwZ3074_e5LUJ2A01BBm5QZ6...",
  "httpsBaseUrl": {
    "hostname": "api.c001.eagleeyenetworks.com",
    "port": 443
  },
  "scope": "vms.all",
  "token_type": "Bearer"
}
```

---

## Token Rotation — Critical Behavior

By default, refresh tokens **rotate on every use**:

1. You call `refreshAccessToken` with refresh token A.
2. You receive a new access token and a new refresh token B.
3. Refresh token A is immediately **invalidated**. The old access token derived from A is also invalidated.
4. You must store and use refresh token B for all future refreshes.

**Consequence:** If your application crashes after receiving the new tokens but before saving them, you may lose the ability to refresh. Design storage (database write, secure keychain) to happen atomically before discarding the old token.

### Non-Rotating Refresh Tokens (Optional)

Eagle Eye offers permanent, non-rotating refresh tokens on request (`api_support@een.com`). These:
- Do not expire
- Do not rotate — the same token is reused indefinitely
- Return the currently active access token (not a new one) if the current access token has not yet expired. Implement retry logic: if you get back the same access token you already have, wait until it expires and call again.

---

## Error Cases

| HTTP Status | Meaning | Action |
|---|---|---|
| `400` | Invalid `grant_type` or malformed body | Fix the request |
| `401` | Refresh token is expired, revoked, or already rotated | Restart Phase 1 — send user through browser auth |
| `401` | Wrong `client_id` / `client_secret` | Check credentials |

A `401` on refresh is the signal to re-run `authenticate`. Your application should have a mechanism to surface this to the user.

---

## Code Examples

### Python

```python
import requests
import base64

def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> dict:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = requests.post(
        "https://auth.eagleeyenetworks.com/oauth2/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data={
            "grant_type": "refresh_token",
            "scope": "vms.all",
            "refresh_token": refresh_token,
        },
    )
    response.raise_for_status()
    return response.json()
    # Returns new: { access_token, refresh_token, expires_in, httpsBaseUrl, ... }
    # Store the NEW refresh_token immediately — the old one is now invalid.
```

### TypeScript

```typescript
async function refreshAccessToken(
  clientId: string,
  clientSecret: string,
  refreshToken: string
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
      grant_type: "refresh_token",
      scope: "vms.all",
      refresh_token: refreshToken,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Token refresh failed: ${response.status} ${text}`);
  }

  // Store the new refresh_token before returning — old one is now invalid
  return response.json();
}
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public static async Task<TokenResponse> RefreshAccessToken(
    string clientId,
    string clientSecret,
    string refreshToken)
{
    using var client = new HttpClient();

    var credentials = Convert.ToBase64String(
        Encoding.UTF8.GetBytes($"{clientId}:{clientSecret}"));
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Basic", credentials);
    client.DefaultRequestHeaders.Accept.Add(
        new MediaTypeWithQualityHeaderValue("application/json"));

    var body = new FormUrlEncodedContent(new[]
    {
        new KeyValuePair<string, string>("grant_type", "refresh_token"),
        new KeyValuePair<string, string>("scope", "vms.all"),
        new KeyValuePair<string, string>("refresh_token", refreshToken),
    });

    var response = await client.PostAsync(
        "https://auth.eagleeyenetworks.com/oauth2/token", body);
    response.EnsureSuccessStatusCode();

    var json = await response.Content.ReadAsStringAsync();
    var doc = JsonSerializer.Deserialize<JsonElement>(json);

    // Persist the new refresh_token immediately before returning
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

pub async fn refresh_access_token(
    client_id: &str,
    client_secret: &str,
    refresh_token: &str,
) -> Result<TokenResponse, reqwest::Error> {
    let credentials = general_purpose::STANDARD
        .encode(format!("{}:{}", client_id, client_secret));

    let client = Client::new();
    let params = [
        ("grant_type", "refresh_token"),
        ("scope", "vms.all"),
        ("refresh_token", refresh_token),
    ];

    // Store the new refresh_token from the response before the old one is used again
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

## Recommended Token Management Pattern

```
On startup:
  Load stored { access_token, refresh_token, expires_at, base_url } from secure storage

Before each API call:
  If now >= expires_at - 5 minutes:
    tokens = refreshAccessToken(client_id, client_secret, refresh_token)
    Save new tokens to secure storage
  Use access_token in Authorization header

On 401 response from any API call:
  Try refreshAccessToken once
  If that also returns 401: trigger Phase 1 re-authorization
```
