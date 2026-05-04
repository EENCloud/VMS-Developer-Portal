# Core Function 3: listCameras

## Purpose

Retrieves the list of cameras associated with the authenticated account. Camera `id` values are required by virtually every other device-centric operation — feeds, media, events, PTZ, status, exports — making this the standard entry point for any workflow that involves a specific camera.

---

## HTTP Request

```
GET https://{baseUrl}/api/v3.0/cameras
Authorization: Bearer {access_token}
Accept: application/json
```

`{baseUrl}` is the `httpsBaseUrl.hostname` from the token response (e.g. `api.c001.eagleeyenetworks.com`).

---

## Query Parameters

All parameters are optional. Omitting all parameters returns all cameras on the account (paginated).

### Filtering

| Parameter | Type | Description |
|---|---|---|
| `id__in` | string (comma-separated) | Return only cameras with these IDs, e.g. `10097dd2,100d4c41` |
| `name` | string | Exact match on camera name |
| `name__contains` | string | Case-insensitive substring match on camera name |
| `name__in` | string (comma-separated) | Match any of these exact names |
| `locationId__in` | string (comma-separated) | Filter by location ID(s) |
| `bridgeId__in` | string (comma-separated) | Filter by bridge ID(s) |
| `tags__contains` | string | Camera must have all of these tags |
| `tags__any` | string | Camera must have at least one of these tags |
| `status__in` | string (comma-separated) | Filter by status, e.g. `online`, `offline` |
| `shared` | boolean | `true` to include shared cameras only |
| `q` | string | Free-text search across camera fields |

### Including Additional Data

| Parameter | Type | Description |
|---|---|---|
| `include` | string (comma-separated) | Additional fields to include in each result. See values below. |

Common `include` values:
- `status` — adds connection status and health fields
- `locationSummary` — adds location name and ID
- `bridges` — adds bridge associations

### Pagination

| Parameter | Type | Description |
|---|---|---|
| `pageSize` | integer | Number of results per page (max 100). Default varies. |
| `pageToken` | string | Cursor for the next page, from `nextPageToken` in a previous response |

### Sorting

| Parameter | Type | Description |
|---|---|---|
| `sort` | string | Field to sort by. **A direction prefix is required** — `+` for ascending, `-` for descending. E.g. `+name`, `-name`. A bare field name without a prefix (e.g. `name`) is rejected with a 400 error. Valid fields: `name`, `bridgeSummary.name`, `locationSummary.name`. |

---

## Response

```json
{
  "results": [
    {
      "id": "10097dd2",
      "name": "Front Door",
      "locationId": "loc-abc123",
      "bridgeId": "bridge-001",
      "tags": ["entrance", "outdoor"],
      "status": {
        "connectionStatus": "online"
      }
    }
  ],
  "nextPageToken": "MToxMDA6MTY2MDU3NzAzNjM2Njot",
  "prevPageToken": "",
  "totalSize": 42
}
```

### Camera Object Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | **Camera ID.** Use this in all other API calls. Typically 8 hex chars, e.g. `10097dd2`. |
| `name` | string | Human-readable camera name |
| `locationId` | string | ID of the location this camera belongs to |
| `bridgeId` | string | ID of the bridge this camera is connected through |
| `tags` | string[] | User-defined tags |
| `status.connectionStatus` | string | `online`, `offline`, or `unknown` (only present if `include=status`) |

### Pagination Fields

| Field | Description |
|---|---|
| `nextPageToken` | Pass as `pageToken` to get the next page. Empty string means no more pages. |
| `prevPageToken` | Pass as `pageToken` to get the previous page. |
| `totalSize` | Total number of cameras on the account (not the number in this page). |

---

## Pagination Pattern

```
page 1: GET /cameras?pageSize=50
         → results[0..49], nextPageToken="abc"

page 2: GET /cameras?pageSize=50&pageToken=abc
         → results[50..99], nextPageToken="def"

page 3: GET /cameras?pageSize=50&pageToken=def
         → results[100..N], nextPageToken=""   ← done
```

Stop when `nextPageToken` is an empty string.

---

## Code Examples

### Python

```python
import requests
from typing import Iterator

def list_cameras(
    access_token: str,
    base_url: str,
    page_size: int = 100,
    **filters
) -> Iterator[dict]:
    """Yields all cameras, handling pagination automatically."""
    params = {"pageSize": page_size, **filters}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    while True:
        response = requests.get(
            f"https://{base_url}/api/v3.0/cameras",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        data = response.json()

        yield from data["results"]

        next_token = data.get("nextPageToken", "")
        if not next_token:
            break
        params["pageToken"] = next_token


# Usage
cameras = list(list_cameras(access_token, base_url))
camera_ids = [c["id"] for c in cameras]

# With filters
online_cameras = list(list_cameras(
    access_token, base_url,
    status__in="online",
    include="status"
))
```

### TypeScript

```typescript
interface Camera {
  id: string;
  name: string;
  locationId?: string;
  bridgeId?: string;
  tags?: string[];
  status?: { connectionStatus: string };
}

interface CameraListResponse {
  results: Camera[];
  nextPageToken: string;
  prevPageToken: string;
  totalSize: number;
}

async function listCameras(
  accessToken: string,
  baseUrl: string,
  filters: Record<string, string> = {}
): Promise<Camera[]> {
  const cameras: Camera[] = [];
  let pageToken: string | undefined;

  do {
    const params = new URLSearchParams({
      pageSize: "100",
      ...filters,
      ...(pageToken ? { pageToken } : {}),
    });

    const response = await fetch(
      `https://${baseUrl}/api/v3.0/cameras?${params}`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error(`listCameras failed: ${response.status} ${await response.text()}`);
    }

    const data: CameraListResponse = await response.json();
    cameras.push(...data.results);
    pageToken = data.nextPageToken || undefined;
  } while (pageToken);

  return cameras;
}

// Usage
const cameras = await listCameras(accessToken, baseUrl);
const cameraIds = cameras.map(c => c.id);

// With filters
const onlineCameras = await listCameras(accessToken, baseUrl, {
  status__in: "online",
  include: "status",
});
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;

public record Camera(
    string Id,
    string Name,
    string? LocationId,
    string? BridgeId
);

public static async Task<List<Camera>> ListCameras(
    string accessToken,
    string baseUrl,
    Dictionary<string, string>? filters = null)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);
    client.DefaultRequestHeaders.Accept.Add(
        new MediaTypeWithQualityHeaderValue("application/json"));

    var cameras = new List<Camera>();
    string? pageToken = null;

    do
    {
        var query = new Dictionary<string, string> { ["pageSize"] = "100" };
        if (filters != null) foreach (var kv in filters) query[kv.Key] = kv.Value;
        if (pageToken != null) query["pageToken"] = pageToken;

        var qs = string.Join("&", query.Select(kv =>
            $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value)}"));

        var response = await client.GetAsync(
            $"https://{baseUrl}/api/v3.0/cameras?{qs}");
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        var doc = JsonSerializer.Deserialize<JsonElement>(json);

        foreach (var cam in doc.GetProperty("results").EnumerateArray())
        {
            cameras.Add(new Camera(
                Id: cam.GetProperty("id").GetString()!,
                Name: cam.GetProperty("name").GetString()!,
                LocationId: cam.TryGetProperty("locationId", out var loc)
                    ? loc.GetString() : null,
                BridgeId: cam.TryGetProperty("bridgeId", out var br)
                    ? br.GetString() : null
            ));
        }

        var next = doc.GetProperty("nextPageToken").GetString();
        pageToken = string.IsNullOrEmpty(next) ? null : next;

    } while (pageToken != null);

    return cameras;
}
```

### Rust

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Deserialize)]
pub struct Camera {
    pub id: String,
    pub name: String,
    pub location_id: Option<String>,
    pub bridge_id: Option<String>,
    pub tags: Option<Vec<String>>,
}

#[derive(Debug, Deserialize)]
struct CameraPage {
    results: Vec<Camera>,
    #[serde(rename = "nextPageToken")]
    next_page_token: String,
}

pub async fn list_cameras(
    access_token: &str,
    base_url: &str,
    filters: HashMap<&str, &str>,
) -> Result<Vec<Camera>, reqwest::Error> {
    let client = Client::new();
    let mut cameras = Vec::new();
    let mut page_token: Option<String> = None;

    loop {
        let mut params: Vec<(&str, String)> = vec![("pageSize", "100".to_string())];
        for (k, v) in &filters {
            params.push((k, v.to_string()));
        }
        if let Some(ref token) = page_token {
            params.push(("pageToken", token.clone()));
        }

        let page: CameraPage = client
            .get(format!("https://{}/api/v3.0/cameras", base_url))
            .bearer_auth(access_token)
            .header("Accept", "application/json")
            .query(&params)
            .send()
            .await?
            .error_for_status()?
            .json()
            .await?;

        cameras.extend(page.results);

        if page.next_page_token.is_empty() {
            break;
        }
        page_token = Some(page.next_page_token);
    }

    Ok(cameras)
}
```

---

## Notes

- Camera `id` values are short hex strings (e.g. `10097dd2`). They are stable identifiers — store them to avoid repeated listing.
- `totalSize` reflects the total cameras on the account, not the page count. It does not change when filters are applied.
- To fetch a single camera by ID, use `GET /api/v3.0/cameras/{id}` — but `listCameras` with `id__in={id}` also works and returns the same shape.
- Cameras shared from another account (accessed via `shared=true`) have limited operations available.
