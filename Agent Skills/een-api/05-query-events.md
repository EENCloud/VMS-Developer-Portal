# Core Function 5: queryEvents

## Purpose

Retrieves historical events attributed to a camera or other actor. Events are the central data model of the Eagle Eye API — they represent motion detections, device status changes, license plate reads, object detections, custom integrations, and more. The same query pattern also applies to `GET /media` for recorded video intervals. Mastering this function gives you access to all time-series data in the system.

---

## HTTP Request

```
GET https://{baseUrl}/api/v3.0/events
Authorization: Bearer {access_token}
Accept: application/json
```

---

## Query Parameters

### Actor (who generated the event)

| Parameter | Type | Description |
|---|---|---|
| `actor` | string | Filter by the entity the event is attributed to. Format: `{actorType}:{actorId}`. Example: `camera:10097dd2`. Actor types include `camera`, `bridge`, `user`, `account`. |

### Time Range

All timestamps must be ISO 8601 format with millisecond precision and `+00:00` timezone offset: `2024-03-15T07:59:22.946+00:00`

> **Critical:** Always use `+00:00` — never `Z`. The `Z` suffix is rejected with 400 by `GET /media` (and possibly other endpoints). JavaScript's `Date.toISOString()` produces `Z` by default; replace it: `new Date(...).toISOString().replace(/Z$/, '+00:00')`

| Parameter | Type | Description |
|---|---|---|
| `startTimestamp__gte` | ISO 8601 string | Events whose start time is on or after this value |
| `startTimestamp__lte` | ISO 8601 string | Events whose start time is on or before this value |
| `endTimestamp__gte` | ISO 8601 string | Events whose end time is on or after this value |
| `endTimestamp__lte` | ISO 8601 string | Events whose end time is on or before this value |

For a simple time window query, use `startTimestamp__gte` + `startTimestamp__lte`.

### Event Type

| Parameter | Type | Description |
|---|---|---|
| `type__in` | string (comma-separated) | Filter to specific event types. See common types below. |

### Additional Data

| Parameter | Type | Description |
|---|---|---|
| `include` | string (comma-separated) | Include additional data schemas in each event's `data` array. The valid values for each event type are listed in its `dataSchemas` field. |

### Sorting and Pagination

| Parameter | Type | Description |
|---|---|---|
| `sort` | string | Sort by field. Use `startTimestamp` (ascending) or `-startTimestamp` (descending, most recent first). Default is ascending. |
| `pageSize` | integer | Results per page (max 100) |
| `pageToken` | string | Cursor from `nextPageToken` in previous response |

### Data Filters

Events can be filtered on fields within specific data schemas using the pattern `data.{schemaName}.{fieldName}`:

| Parameter | Description |
|---|---|
| `data.een_deviceCloudStatusUpdate_v1.newStatus_connectionStatus__in` | Filter device status events by connection status (e.g. `online`, `offline`) |
| `data.een_humanValidationDetails_v1.isValid` | Filter validated motion events |
| `data.een_deviceIO_v1.portId__in` | Filter I/O events by port ID |

Note: Applying a data filter excludes event types that do not contain the referenced schema — e.g., filtering by `connectionStatus` will omit motion events.

---

## Common Event Types

| `type` value | Description |
|---|---|
| `een.motionDetectionEvent.v1` | Motion detected by a camera |
| `een.deviceCloudStatusUpdateEvent.v1` | Camera or bridge went online/offline |
| `een.lprPlateReadEvent.v1` | License plate read by LPR camera |
| `een.videoAnalyticEvent.v1` | AI-detected object (person, vehicle, etc.) |
| `een.deviceIO.v1` | I/O port triggered (digital input/output) |
| `een.userLoginEvent.v1` | User logged in to the account |

To retrieve all supported event types for an account:
```
GET https://{baseUrl}/api/v3.0/eventTypes
Authorization: Bearer {access_token}
```

---

## Response

```json
{
  "results": [
    {
      "id": "nINlL0YuoRAnv9QcHKXi",
      "startTimestamp": "2024-03-15T07:34:23.032Z",
      "endTimestamp": "2024-03-15T07:35:00.000Z",
      "span": true,
      "accountId": "00001106",
      "actorId": "10097dd2",
      "actorAccountId": "00001106",
      "actorType": "camera",
      "creatorId": "een.bridgeMotion",
      "type": "een.motionDetectionEvent.v1",
      "dataSchemas": [
        "een.objectDetection.v1",
        "een.croppedFrameImageUrl.v1",
        "een.fullFrameImageUrl.v1"
      ],
      "data": []
    }
  ],
  "nextPageToken": "MToxMDA6MTY2MDU3NzAzNjM2Njot",
  "prevPageToken": "",
  "totalSize": 156
}
```

### Event Object Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique event ID |
| `startTimestamp` | ISO 8601 string | When the event started |
| `endTimestamp` | ISO 8601 string | When the event ended |
| `span` | boolean | `true` if the event has duration (start ≠ end). `false` for instantaneous events. |
| `accountId` | string | Account ID |
| `actorId` | string | ID of the entity that generated the event (e.g. camera ID) |
| `actorType` | string | Type of actor: `camera`, `bridge`, `user`, `account` |
| `creatorId` | string | System or service that created the event (e.g. `een.bridgeMotion`, `een.lpr`) |
| `type` | string | Event type identifier |
| `dataSchemas` | string[] | List of data schema types available for this event — use these values with the `include` parameter |
| `data` | object[] | Additional event data. Empty by default; populated when schemas are requested via `include`. |

### Included Data Example (motion event with object detection)

When `include=een.objectDetection.v1` is added:

```json
"data": [
  {
    "type": "een.objectDetection.v1",
    "creatorId": "een.bridgeMotion",
    "objectId": "camera-46743c2:d3275d08-16df-4176-b9c6-688046c858a2",
    "timestamp": "2024-03-15T07:34:23.000Z",
    "boundingBox": [0.2, 0.9, 0.25, 0.95]
  },
  {
    "type": "een.fullFrameImageUrl.v1",
    "creatorId": "een.bridgeMotion",
    "httpsUrl": "https://media.c001.eagleeyenetworks.com/assets/events/4333af21c0-...jpeg",
    "timestamp": "2024-03-15T07:34:23.000Z"
  }
]
```

---

## Related: Querying Recorded Media

The `GET /media` endpoint lists recording intervals (time ranges for which video is stored). It shares most query conventions with `GET /events` but has two confirmed differences:

1. **Timestamps must use `+00:00` — `Z` suffix returns 400.** (Confirmed from live API responses.)
2. **`sort` parameter is not supported — rejected with 400.** Results are returned in an unspecified order; sort client-side if needed.

```
GET https://{baseUrl}/api/v3.0/media
  ?deviceId={cameraId}
  &type=main
  &mediaType=video
  &startTimestamp__gte=2024-03-15T00:00:00.000+00:00
  &endTimestamp__lte=2024-03-15T23:59:59.000+00:00
  &include=hlsUrl
  &pageSize=100
```

Response:
```json
{
  "results": [
    {
      "type": "main",
      "deviceId": "10097dd2",
      "mediaType": "video",
      "startTimestamp": "2024-03-15T07:56:54.894+00:00",
      "endTimestamp": "2024-03-15T08:27:14.448+00:00",
      "hlsUrl": "https://media.c001.eagleeyenetworks.com/media/streams/main/hls?esn=10097dd2&from=...&till=...&stream_session=..."
    }
  ],
  "nextPageToken": "",
  "totalSize": 3
}
```

For browser playback, use `include=hlsUrl` and load with hls.js + `XhrLoader` (same setup as live feeds — see `04-get-live-feed.md`). The `rtspUrl` format is also available but cannot be played directly in a browser.

### TypeScript — querying a full day of recordings

```typescript
interface MediaSegment {
  type: string
  deviceId: string
  mediaType: string
  startTimestamp: string
  endTimestamp: string
  hlsUrl?: string
}

// Always use +00:00 — never Z. toISOString() produces Z by default; replace it.
function toEenTimestamp(d: Date): string {
  return d.toISOString().replace(/Z$/, '+00:00')
}

async function getMediaSegments(
  accessToken: string,
  baseUrl: string,
  cameraId: string,
  localDateStr: string, // "YYYY-MM-DD" in local time
): Promise<MediaSegment[]> {
  const startOfDay = toEenTimestamp(new Date(`${localDateStr}T00:00:00`))
  const endOfDay   = toEenTimestamp(new Date(`${localDateStr}T23:59:59`))

  const segments: MediaSegment[] = []
  let pageToken: string | undefined

  do {
    const params = new URLSearchParams({
      deviceId: cameraId,
      type: 'main',
      mediaType: 'video',
      startTimestamp__gte: startOfDay,
      endTimestamp__lte: endOfDay,
      include: 'hlsUrl',
      pageSize: '100',
      // NOTE: do NOT include sort= — /media rejects it with 400
      ...(pageToken ? { pageToken } : {}),
    })

    const response = await fetch(`https://${baseUrl}/api/v3.0/media?${params}`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`getMediaSegments failed: ${response.status} ${await response.text()}`)
    }

    const data = await response.json()
    segments.push(...(data.results as MediaSegment[]))
    pageToken = data.nextPageToken || undefined
  } while (pageToken)

  return segments
}

// Usage
const segments = await getMediaSegments(accessToken, baseUrl, '10097dd2', '2024-03-15')
// segments[0].hlsUrl is ready to pass to hls.js (with XhrLoader + xhrSetup)
```

---

## Code Examples

### Python

```python
import requests
from typing import Iterator

def query_events(
    access_token: str,
    base_url: str,
    actor: str | None = None,
    type_in: str | None = None,
    start_gte: str | None = None,
    start_lte: str | None = None,
    include: str | None = None,
    sort: str = "-startTimestamp",
    page_size: int = 100,
) -> Iterator[dict]:
    """Yields all matching events, handling pagination automatically."""
    params = {"pageSize": page_size, "sort": sort}
    if actor:    params["actor"] = actor
    if type_in:  params["type__in"] = type_in
    if start_gte: params["startTimestamp__gte"] = start_gte
    if start_lte: params["startTimestamp__lte"] = start_lte
    if include:  params["include"] = include

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    while True:
        response = requests.get(
            f"https://{base_url}/api/v3.0/events",
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


# Get all motion events for a camera in a time window
events = list(query_events(
    access_token, base_url,
    actor="camera:10097dd2",
    type_in="een.motionDetectionEvent.v1",
    start_gte="2024-03-15T00:00:00Z",
    start_lte="2024-03-15T23:59:59Z",
))

# Get motion events with full-frame image URLs
events = list(query_events(
    access_token, base_url,
    actor="camera:10097dd2",
    type_in="een.motionDetectionEvent.v1",
    include="een.fullFrameImageUrl.v1",
))
```

### TypeScript

```typescript
interface EventData {
  type: string;
  [key: string]: unknown;
}

interface ApiEvent {
  id: string;
  startTimestamp: string;
  endTimestamp: string;
  span: boolean;
  accountId: string;
  actorId: string;
  actorType: string;
  creatorId: string;
  type: string;
  dataSchemas: string[];
  data: EventData[];
}

interface QueryOptions {
  actor?: string;
  typeIn?: string;
  startGte?: string;
  startLte?: string;
  include?: string;
  sort?: string;
  pageSize?: number;
}

async function queryEvents(
  accessToken: string,
  baseUrl: string,
  options: QueryOptions = {}
): Promise<ApiEvent[]> {
  const events: ApiEvent[] = [];
  let pageToken: string | undefined;

  const {
    actor,
    typeIn,
    startGte,
    startLte,
    include,
    sort = "-startTimestamp",
    pageSize = 100,
  } = options;

  do {
    const params = new URLSearchParams({ sort, pageSize: String(pageSize) });
    if (actor) params.set("actor", actor);
    if (typeIn) params.set("type__in", typeIn);
    if (startGte) params.set("startTimestamp__gte", startGte);
    if (startLte) params.set("startTimestamp__lte", startLte);
    if (include) params.set("include", include);
    if (pageToken) params.set("pageToken", pageToken);

    const response = await fetch(
      `https://${baseUrl}/api/v3.0/events?${params}`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error(`queryEvents failed: ${response.status} ${await response.text()}`);
    }

    const data = await response.json();
    events.push(...data.results);
    pageToken = data.nextPageToken || undefined;
  } while (pageToken);

  return events;
}

// Get motion events for a camera today
const motionEvents = await queryEvents(accessToken, baseUrl, {
  actor: "camera:10097dd2",
  typeIn: "een.motionDetectionEvent.v1",
  startGte: "2024-03-15T00:00:00Z",
  startLte: "2024-03-15T23:59:59Z",
});
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;

public record ApiEvent(
    string Id,
    string StartTimestamp,
    string EndTimestamp,
    bool Span,
    string ActorId,
    string ActorType,
    string Type,
    string[] DataSchemas
);

public static async Task<List<ApiEvent>> QueryEvents(
    string accessToken,
    string baseUrl,
    string? actor = null,
    string? typeIn = null,
    string? startGte = null,
    string? startLte = null,
    string? include = null,
    string sort = "-startTimestamp",
    int pageSize = 100)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);
    client.DefaultRequestHeaders.Accept.Add(
        new MediaTypeWithQualityHeaderValue("application/json"));

    var events = new List<ApiEvent>();
    string? pageToken = null;

    do
    {
        var query = new Dictionary<string, string>
        {
            ["sort"] = sort,
            ["pageSize"] = pageSize.ToString(),
        };
        if (actor != null) query["actor"] = actor;
        if (typeIn != null) query["type__in"] = typeIn;
        if (startGte != null) query["startTimestamp__gte"] = startGte;
        if (startLte != null) query["startTimestamp__lte"] = startLte;
        if (include != null) query["include"] = include;
        if (pageToken != null) query["pageToken"] = pageToken;

        var qs = string.Join("&", query.Select(kv =>
            $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value)}"));

        var response = await client.GetAsync(
            $"https://{baseUrl}/api/v3.0/events?{qs}");
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        var doc = JsonSerializer.Deserialize<JsonElement>(json);

        foreach (var ev in doc.GetProperty("results").EnumerateArray())
        {
            var schemas = ev.GetProperty("dataSchemas")
                            .EnumerateArray()
                            .Select(s => s.GetString()!)
                            .ToArray();

            events.Add(new ApiEvent(
                Id: ev.GetProperty("id").GetString()!,
                StartTimestamp: ev.GetProperty("startTimestamp").GetString()!,
                EndTimestamp: ev.GetProperty("endTimestamp").GetString()!,
                Span: ev.GetProperty("span").GetBoolean(),
                ActorId: ev.GetProperty("actorId").GetString()!,
                ActorType: ev.GetProperty("actorType").GetString()!,
                Type: ev.GetProperty("type").GetString()!,
                DataSchemas: schemas
            ));
        }

        var next = doc.GetProperty("nextPageToken").GetString();
        pageToken = string.IsNullOrEmpty(next) ? null : next;

    } while (pageToken != null);

    return events;
}
```

### Rust

```rust
use reqwest::Client;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct ApiEvent {
    pub id: String,
    #[serde(rename = "startTimestamp")]
    pub start_timestamp: String,
    #[serde(rename = "endTimestamp")]
    pub end_timestamp: String,
    pub span: bool,
    #[serde(rename = "actorId")]
    pub actor_id: String,
    #[serde(rename = "actorType")]
    pub actor_type: String,
    #[serde(rename = "type")]
    pub event_type: String,
    #[serde(rename = "dataSchemas")]
    pub data_schemas: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct EventPage {
    results: Vec<ApiEvent>,
    #[serde(rename = "nextPageToken")]
    next_page_token: String,
}

pub struct EventQuery<'a> {
    pub actor: Option<&'a str>,
    pub type_in: Option<&'a str>,
    pub start_gte: Option<&'a str>,
    pub start_lte: Option<&'a str>,
    pub include: Option<&'a str>,
    pub sort: &'a str,
    pub page_size: usize,
}

impl Default for EventQuery<'_> {
    fn default() -> Self {
        Self {
            actor: None,
            type_in: None,
            start_gte: None,
            start_lte: None,
            include: None,
            sort: "-startTimestamp",
            page_size: 100,
        }
    }
}

pub async fn query_events(
    access_token: &str,
    base_url: &str,
    query: EventQuery<'_>,
) -> Result<Vec<ApiEvent>, reqwest::Error> {
    let client = Client::new();
    let mut events = Vec::new();
    let mut page_token: Option<String> = None;

    loop {
        let mut params: Vec<(&str, String)> = vec![
            ("sort", query.sort.to_string()),
            ("pageSize", query.page_size.to_string()),
        ];
        if let Some(a) = query.actor { params.push(("actor", a.to_string())); }
        if let Some(t) = query.type_in { params.push(("type__in", t.to_string())); }
        if let Some(s) = query.start_gte { params.push(("startTimestamp__gte", s.to_string())); }
        if let Some(s) = query.start_lte { params.push(("startTimestamp__lte", s.to_string())); }
        if let Some(i) = query.include { params.push(("include", i.to_string())); }
        if let Some(ref t) = page_token { params.push(("pageToken", t.clone())); }

        let page: EventPage = client
            .get(format!("https://{}/api/v3.0/events", base_url))
            .bearer_auth(access_token)
            .header("Accept", "application/json")
            .query(&params)
            .send()
            .await?
            .error_for_status()?
            .json()
            .await?;

        events.extend(page.results);

        if page.next_page_token.is_empty() {
            break;
        }
        page_token = Some(page.next_page_token);
    }

    Ok(events)
}
```

---

## Notes

- The `actor` parameter format is `{type}:{id}`, e.g. `camera:10097dd2`. Omitting `actor` returns events across all actors on the account.
- `dataSchemas` tells you which additional data is available for each event. Use these values in the `include` parameter to retrieve the structured data payload.
- Events returned without `include` have an empty `data` array. This is normal and intentional for efficiency.
- Use `sort=-startTimestamp` (descending) to get most recent events first — the default is ascending (oldest first).
- The same pagination pattern (`nextPageToken`, `prevPageToken`, `totalSize`) applies universally across all list endpoints in this API.
