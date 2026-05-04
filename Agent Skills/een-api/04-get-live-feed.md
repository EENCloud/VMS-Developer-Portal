# Core Function 4: getLiveFeed

## Purpose

Retrieves one or more live stream URLs for a given camera. The `include` parameter selects the stream format — RTSP, RTSP over TLS, HLS, WebRTC, local (bridge-direct) RTSP, or audio push HTTPS. A single call to this function satisfies any live video streaming use case the API supports.

---

## Media Session Cookie — Required Before Playback

> **Critical:** Without setting the media session cookie first, all stream URLs (HLS, RTSP, etc.) will return `403 Unauthorized`. This step is mandatory for browser-based playback.

Before loading any stream URL, perform a two-step cookie setup:

**Step 1:** `GET https://{baseUrl}/api/v3.0/media/session` with `Authorization: Bearer {token}` and `credentials: 'include'`. Returns a temporary session URL:
```json
{ "url": "https://media.c013.eagleeyenetworks.com/media/session" }
```

**Step 2:** `GET` the returned `url` with `Authorization: Bearer {token}` and `credentials: 'include'`. Returns `204 No Content` and sets the media cookie in the browser.

```javascript
const res = await fetch(`https://${baseUrl}/api/v3.0/media/session`, {
  headers: { Authorization: `Bearer ${accessToken}` },
  credentials: 'include',
})
const { url } = await res.json()
await fetch(url, {
  headers: { Authorization: `Bearer ${accessToken}` },
  credentials: 'include',
})
// Cookie is now set — stream URLs will work
```

Once set, the cookie covers native browser media elements (`<video>`, `<img>`). For hls.js, you must also send `Authorization: Bearer` on every manifest and segment request via `xhrSetup`.

### hls.js — critical: force `XhrLoader`

hls.js v1.x defaults to the **Fetch API** in modern browsers (Chrome, Firefox, Edge). When using the Fetch loader, `xhrSetup` is **never called**, so the Authorization header is never sent and every request returns `401`.

The fix is to explicitly pass `XhrLoader` in the hls.js config. This forces the XHR transport and guarantees `xhrSetup` fires on every request:

```typescript
import Hls, { XhrLoader } from 'hls.js'

const hls = new Hls({
  loader: XhrLoader,          // required — prevents hls.js defaulting to Fetch API
  xhrSetup: (xhr) => {
    xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`)
  },
})
hls.loadSource(hlsUrl)        // use the hlsUrl as-is — do NOT append &access_token=
hls.attachMedia(videoElement)
```

Without `loader: XhrLoader`, the pattern above silently does nothing in Chrome/Firefox/Edge and playback fails with auth errors even though network traffic appears to show the stream loading.

> **Do not use `fetchSetup` as a substitute.** While hls.js exposes a `fetchSetup` callback, it is unreliable for cross-origin auth and the EEN media servers expect the XHR flow. Stick with `loader: XhrLoader` + `xhrSetup`.

**Timing is critical:** the media session must be fully established (both requests complete) **before** `hls.loadSource()` is called. The safest approach is to `await setMediaSession(...)` immediately before calling `hls.loadSource()`, regardless of whether it was called earlier at app startup.

---

## HTTP Request

```
GET https://{baseUrl}/api/v3.0/feeds
Authorization: Bearer {access_token}
Accept: application/json
```

---

## Query Parameters

### Required

| Parameter | Type | Description |
|---|---|---|
| `deviceId` | string | Camera ID from `listCameras`. E.g. `10097dd2` |
| `type` | string | Stream quality. `main` = full resolution. `preview` = low-quality/thumbnail stream. |
| `include` | string (comma-separated) | Which URL type(s) to return. See table below. |

### Optional

| Parameter | Type | Description |
|---|---|---|
| `deviceId__in` | string (comma-separated) | Fetch feeds for multiple cameras in one call |
| `pageSize` | integer | Results per page |
| `pageToken` | string | Pagination cursor |

## Protocol Support by Stream Type

| Video type | Live formats available |
|---|---|
| **Full video – HQ h264** (`type=main`) | `hlsUrl`, `multipartUrl`, `rtspUrl`, `rtspsUrl` |
| **Preview video – LQ JPEG** (`type=preview`) | `multipartUrl`, `rtspUrl`, `rtspsUrl` — **HLS is not available** |

For browser-based grid views, `multipartUrl` with `type=preview` is the correct choice for thumbnail streams. It plays natively in an `<img>` tag once the media session cookie is set — no JavaScript player needed.

---

### `include` Values

| Value | Description | Notes |
|---|---|---|
| `rtspUrl` | RTSP stream via cloud | Append `&access_token={token}` before use. Available for `main` and `preview`. |
| `rtspsUrl` | RTSP over TLS via cloud | Same as `rtspUrl` but encrypted. Available for `main` and `preview`. |
| `hlsUrl` | HLS stream via cloud | **`main` type only.** Not available for `preview`. Requires media session cookie + `Authorization: Bearer` header in hls.js xhrSetup. Do NOT append `&access_token=`. |
| `multipartUrl` | MJPEG multipart stream | Available for `main` and `preview`. Set as `<img src={multipartUrl}>` directly — media session cookie is sufficient. Ideal for grid/thumbnail views. |
| `webRtcUrl` | WebRTC stream | For browser-native low-latency playback. |
| `localRtspUrl` | RTSP direct from bridge | Bypasses cloud. Not available for shared cameras. |
| `audioPushHttpsUrl` | HTTPS endpoint for pushing audio to the device | For two-way audio (speakers). |

Multiple values can be requested at once: `include=multipartUrl,hlsUrl`

---

## Response

```json
{
  "results": [
    {
      "id": "10097dd2-main",
      "type": "main",
      "deviceId": "10097dd2",
      "mediaType": "video",
      "rtspUrl": "rtsp://rtsp.c001.eagleeyenetworks.com:554/media/streams/main/rtsp?esn=10097dd2&stream_session=d755bb70-...",
      "rtspsUrl": "rtsps://rtsp.c001.eagleeyenetworks.com:554/media/streams/main/rtsp?esn=10097dd2&stream_session=...",
      "hlsUrl": "https://media.c001.eagleeyenetworks.com/media/streams/main/hls?esn=10097dd2&stream_session=...",
      "localRtspUrl": "rtsp://username%40domain.com:password@10.10.180.2:8554/10097dd2"
    }
  ],
  "nextPageToken": "",
  "prevPageToken": "",
  "totalSize": 1
}
```

### Feed Object Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Feed identifier in format `{deviceId}-{type}`, e.g. `10097dd2-main` |
| `type` | string | `main` or `preview` |
| `deviceId` | string | Camera ID |
| `mediaType` | string | `video` |
| `rtspUrl` | string? | Cloud RTSP URL (only present if requested via `include`) |
| `rtspsUrl` | string? | Cloud RTSP over TLS URL |
| `hlsUrl` | string? | HLS stream URL |
| `webRtcUrl` | string? | WebRTC URL |
| `localRtspUrl` | string? | Bridge-direct RTSP URL (pre-authenticated — includes credentials in URL) |
| `audioPushHttpsUrl` | string? | Audio push endpoint |

---

## Using the Stream URLs

### RTSP and RTSPS (cloud)

The `rtspUrl` and `rtspsUrl` require the access token to be appended to the URL before it is passed to a media player:

```
{rtspUrl}&access_token={access_token}
```

Example:
```
rtsp://rtsp.c001.eagleeyenetworks.com:554/media/streams/main/rtsp?esn=10097dd2&stream_session=d755bb70&access_token=eyJraWQ...
```

Use the full constructed URL with VLC, FFplay, FFmpeg, or any RTSP-capable player/library.

### HLS (browser)

Two things are required before any HLS request will succeed:

1. **Media session cookie** — must be set before playback starts (see above).
2. **Authorization header** — must be sent with every manifest and segment request.

For **hls.js**, use `loader: XhrLoader` + `xhrSetup` to inject the header (see the Media Session section above for the full pattern). Do not append `&access_token=` to the URL.

For **Safari native HLS** (`video.canPlayType('application/vnd.apple.mpegurl')`), the media session cookie is typically sufficient since Safari sends cookies with native media requests. Set `video.src = hlsUrl` directly.

### Local RTSP

The `localRtspUrl` is pre-authenticated — credentials are embedded in the URL (`user:pass@host:port/path`). No additional token appending is required. The client must be on the same local network as the bridge.

### WebRTC

The `webRtcUrl` is used with the Eagle Eye Live Video Web SDK or a WebRTC signaling client. See the SDK guide for details.

---

## `main` vs `preview`

| Type | Resolution | Use case |
|---|---|---|
| `main` | Full camera resolution | Recording review, incident analysis, high-fidelity monitoring |
| `preview` | Low resolution (thumbnail stream) | Grid views, motion thumbnails, bandwidth-limited displays |

---

## Code Examples

### Python

```python
import requests

def get_live_feed(
    access_token: str,
    base_url: str,
    device_id: str,
    stream_type: str = "main",
    include: str = "rtspUrl",
) -> list[dict]:
    response = requests.get(
        f"https://{base_url}/api/v3.0/feeds",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        params={
            "deviceId": device_id,
            "type": stream_type,
            "include": include,
        },
    )
    response.raise_for_status()
    return response.json()["results"]


# Get a playable RTSP URL
feeds = get_live_feed(access_token, base_url, "10097dd2", "main", "rtspUrl")
rtsp_url = feeds[0]["rtspUrl"] + f"&access_token={access_token}"
# rtsp_url is now ready to pass to VLC, FFmpeg, etc.

# Get both RTSP and HLS at once
feeds = get_live_feed(
    access_token, base_url, "10097dd2",
    include="rtspUrl,hlsUrl"
)
```

### TypeScript

```typescript
interface Feed {
  id: string;
  type: string;
  deviceId: string;
  mediaType: string;
  rtspUrl?: string;
  rtspsUrl?: string;
  hlsUrl?: string;
  webRtcUrl?: string;
  localRtspUrl?: string;
  audioPushHttpsUrl?: string;
}

async function getLiveFeed(
  accessToken: string,
  baseUrl: string,
  deviceId: string,
  type: "main" | "preview" = "main",
  include: string = "rtspUrl"
): Promise<Feed[]> {
  const params = new URLSearchParams({ deviceId, type, include });

  const response = await fetch(
    `https://${baseUrl}/api/v3.0/feeds?${params}`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(`getLiveFeed failed: ${response.status} ${await response.text()}`);
  }

  const data = await response.json();
  return data.results;
}

// Usage: get a playable RTSP URL (token appended to URL — correct for RTSP)
const feeds = await getLiveFeed(accessToken, baseUrl, "10097dd2");
const playableRtspUrl = `${feeds[0].rtspUrl}&access_token=${accessToken}`;

// Usage: HLS playback in the browser via hls.js
// Step 1: establish media session cookie BEFORE loading the stream
await setMediaSession(accessToken, baseUrl);
// Step 2: fetch the HLS URL
const hlsFeeds = await getLiveFeed(accessToken, baseUrl, "10097dd2", "main", "hlsUrl");
const hlsUrl = hlsFeeds[0].hlsUrl; // use as-is — do NOT append &access_token=
// Step 3: initialize hls.js with XhrLoader (REQUIRED — see Media Session section)
// import Hls, { XhrLoader } from 'hls.js'
// const hls = new Hls({ loader: XhrLoader, xhrSetup: xhr => { xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`) } })
// hls.loadSource(hlsUrl)
// hls.attachMedia(videoElement)
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;

public record Feed(
    string Id,
    string Type,
    string DeviceId,
    string? RtspUrl,
    string? RtspsUrl,
    string? HlsUrl,
    string? LocalRtspUrl
);

public static async Task<List<Feed>> GetLiveFeed(
    string accessToken,
    string baseUrl,
    string deviceId,
    string type = "main",
    string include = "rtspUrl")
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);
    client.DefaultRequestHeaders.Accept.Add(
        new MediaTypeWithQualityHeaderValue("application/json"));

    var qs = $"deviceId={Uri.EscapeDataString(deviceId)}" +
             $"&type={Uri.EscapeDataString(type)}" +
             $"&include={Uri.EscapeDataString(include)}";

    var response = await client.GetAsync(
        $"https://{baseUrl}/api/v3.0/feeds?{qs}");
    response.EnsureSuccessStatusCode();

    var json = await response.Content.ReadAsStringAsync();
    var doc = JsonSerializer.Deserialize<JsonElement>(json);
    var feeds = new List<Feed>();

    foreach (var feed in doc.GetProperty("results").EnumerateArray())
    {
        feeds.Add(new Feed(
            Id: feed.GetProperty("id").GetString()!,
            Type: feed.GetProperty("type").GetString()!,
            DeviceId: feed.GetProperty("deviceId").GetString()!,
            RtspUrl: feed.TryGetProperty("rtspUrl", out var rtsp) ? rtsp.GetString() : null,
            RtspsUrl: feed.TryGetProperty("rtspsUrl", out var rtsps) ? rtsps.GetString() : null,
            HlsUrl: feed.TryGetProperty("hlsUrl", out var hls) ? hls.GetString() : null,
            LocalRtspUrl: feed.TryGetProperty("localRtspUrl", out var local) ? local.GetString() : null
        ));
    }

    return feeds;
}

// Usage
var feeds = await GetLiveFeed(accessToken, baseUrl, "10097dd2");
// Append access token for RTSP playback:
var playableUrl = feeds[0].RtspUrl + $"&access_token={accessToken}";
```

### Rust

```rust
use reqwest::Client;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct Feed {
    pub id: String,
    #[serde(rename = "type")]
    pub feed_type: String,
    #[serde(rename = "deviceId")]
    pub device_id: String,
    #[serde(rename = "rtspUrl")]
    pub rtsp_url: Option<String>,
    #[serde(rename = "rtspsUrl")]
    pub rtsps_url: Option<String>,
    #[serde(rename = "hlsUrl")]
    pub hls_url: Option<String>,
    #[serde(rename = "localRtspUrl")]
    pub local_rtsp_url: Option<String>,
}

#[derive(Debug, Deserialize)]
struct FeedPage {
    results: Vec<Feed>,
}

pub async fn get_live_feed(
    access_token: &str,
    base_url: &str,
    device_id: &str,
    feed_type: &str,      // "main" or "preview"
    include: &str,        // e.g. "rtspUrl" or "rtspUrl,hlsUrl"
) -> Result<Vec<Feed>, reqwest::Error> {
    let client = Client::new();

    let page: FeedPage = client
        .get(format!("https://{}/api/v3.0/feeds", base_url))
        .bearer_auth(access_token)
        .header("Accept", "application/json")
        .query(&[
            ("deviceId", device_id),
            ("type", feed_type),
            ("include", include),
        ])
        .send()
        .await?
        .error_for_status()?
        .json()
        .await?;

    Ok(page.results)
}

// Usage
// let feeds = get_live_feed(token, base_url, "10097dd2", "main", "rtspUrl").await?;
// let playable = format!("{}&access_token={}", feeds[0].rtsp_url.as_ref().unwrap(), token);
```

---

## Notes

- If the camera is offline, the API returns 200 with an empty `results` array rather than an error.
- The `localRtspUrl` requires that both the camera and its bridge are registered to the same account. It is not available for cameras shared from another account.
- Stream session tokens embedded in RTSP URLs are temporary. Do not cache the URL itself for extended periods — fetch a fresh one when starting a new session.
- For multi-camera feeds, use `deviceId__in=id1,id2,id3` instead of making multiple calls.
