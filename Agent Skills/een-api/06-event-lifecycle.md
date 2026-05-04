# Core Function Group 6: Event Lifecycle

## Purpose

Three functions that together form the AI enrichment pipeline: **subscribe** to low-level events via webhook, **capture snapshots** from within the event window, and **create derived events** that encode higher-level inferences back into the EEN timeline.

This pipeline is the foundation for any integration that transforms raw sensor data (motion, object detection) into application-level intelligence (face match, brandished weapon, behavior anomaly). It works because EEN events are first-class data — external systems can both consume and produce them.

---

## The Pipeline

```
[EEN Platform]                          [Your Integration]

1. Low-level event fires
   (motion start, span=true)
        │
        ▼
2. Webhook delivery ─────────────────► Receive start notification
                                        Note: span=true, record startTimestamp
                                              endTimestamp = startTimestamp (not yet ended)
        │
3. Low-level event ends
   (motion end, endTimestamp updated)
        │
        ▼
4. Webhook delivery ─────────────────► Receive end notification
                                        Now: endTimestamp ≠ startTimestamp
                                        Full window: [startTimestamp, endTimestamp]
                                              │
                                              ▼
                                        5. Sample frames across window
                                           GET /media/recordedImage.jpeg
                                           at multiple timestamps within span
                                              │
                                              ▼
                                        6. Run inference (face recognition,
                                           object classification, etc.)
                                              │
                                              ▼
                                        7. POST /events — inject derived
                                           event with enriched data payload
```

---

## Span Events

A span event represents an occurrence with duration. Two webhook deliveries are sent for each span event:

| Delivery | `span` | `startTimestamp` | `endTimestamp` |
|---|---|---|---|
| Start | `true` | Set | Equal to startTimestamp |
| End | `true` | Same value | Now distinct from start |

**Detection rule:** If `span === true` and `endTimestamp !== startTimestamp`, the span has ended and the full window is available for sampling.

Motion detection (`een.motionDetectionEvent.v1`) is the canonical span event. The gap between start and end can range from seconds to hours.

---

## Function 1: subscribeToEvents

### HTTP Request

```
POST https://{baseUrl}/api/v3.0/eventSubscriptions
Authorization: Bearer {access_token}
Content-Type: application/json
```

### Request Body

```json
{
  "deliveryConfig": {
    "type": "webhook.v1",
    "url": "https://your-server.com/een-webhook",
    "authorizationHeader": "Bearer your-webhook-secret"
  },
  "filters": [
    {
      "resourceType": "camera",
      "resourceIds": ["10097dd2", "100d4c41"],
      "types": ["een.motionDetectionEvent.v1"]
    }
  ]
}
```

### deliveryConfig

| Field | Value | Notes |
|---|---|---|
| `type` | `webhook.v1` | For HTTP push delivery. Use `serverSentEvents.v1` for SSE (browser-based). |
| `url` | your HTTPS endpoint | Must be publicly reachable. EEN POSTs the event JSON here. |
| `authorizationHeader` | string | EEN sends this as the `Authorization` header on webhook calls. Use to verify authenticity. |

### filters

Each filter object:

| Field | Type | Description |
|---|---|---|
| `resourceType` | string | `camera`, `bridge`, `user`, or `account` |
| `resourceIds` | string[] | IDs of specific resources to watch. Omit for all resources of type. |
| `types` | string[] | Event type strings to match. Omit for all event types. |

Multiple filter objects in the array are OR'd together.

### Response

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "deliveryConfig": { ... },
  "filters": [ ... ],
  "lifeCycle": "persistent",
  "timeToLiveSeconds": null
}
```

| Field | Notes |
|---|---|
| `id` | Subscription ID. Store this — needed to delete or inspect the subscription. |
| `lifeCycle` | `persistent` for webhooks (survives indefinitely). `temporary` for SSE sessions. |

### Managing Subscriptions

```
GET    /eventSubscriptions              List all subscriptions
GET    /eventSubscriptions/{id}         Get one subscription
DELETE /eventSubscriptions/{id}         Remove subscription (stops webhook delivery)
```

---

## Function 2: getSnapshot

Two endpoints — choose based on whether you need a live frame or a frame from a specific historical moment.

### Live snapshot

```
GET https://{baseUrl}/api/v3.0/media/liveImage.jpeg
Authorization: Bearer {access_token}
```

| Parameter | Required | Description |
|---|---|---|
| `deviceId` | Yes | Camera ID |
| `liveType` | Yes | `main` (full resolution) or `preview` (low resolution) |

Returns `image/jpeg` binary. Response headers include:
- `X-Een-Timestamp` — actual timestamp of the captured frame
- `X-Een-PrevToken` — token to fetch the previous frame sequentially

### Recorded snapshot (for span event sampling)

```
GET https://{baseUrl}/api/v3.0/media/recordedImage.jpeg
Authorization: Bearer {access_token}
```

| Parameter | Required | Description |
|---|---|---|
| `deviceId` | No | Camera ID |
| `recordedType` | Yes | `main` or `preview` |
| `timestamp` | One required | Exact timestamp match (ISO 8601, `+00:00`) |
| `timestampGreaterOrEqual` | One required | Nearest frame at or after this timestamp |
| `timestampLessOrEqual` | One required | Nearest frame at or before this timestamp |
| `timestampGreater` | One required | Nearest frame strictly after this timestamp |
| `timestampLess` | One required | Nearest frame strictly before this timestamp |
| `targetWidth` | No | Resize output to this width (pixels) |
| `targetHeight` | No | Resize output to this height (pixels) |
| `token` | No | Pagination token from previous response for sequential traversal |

Returns `image/jpeg` binary. Response headers:
- `X-Een-Timestamp` — actual timestamp of the returned frame (may differ from requested)
- `X-Een-NextToken` — token for the next frame forward in time
- `X-Een-PrevToken` — token for the previous frame

**Span event sampling pattern:** Request frames at evenly-spaced intervals across `[startTimestamp, endTimestamp]`, or walk forward using `X-Een-NextToken` to get every available frame.

---

## Function 3: createEvent

### HTTP Request

```
POST https://{baseUrl}/api/v3.0/events
Authorization: Bearer {access_token}
Content-Type: application/json
```

### Request Body

```json
{
  "startTimestamp": "2024-03-15T07:34:23.032+00:00",
  "endTimestamp": "2024-03-15T07:35:00.000+00:00",
  "span": true,
  "accountId": "00001106",
  "actorId": "10097dd2",
  "actorAccountId": "00001106",
  "actorType": "camera",
  "creatorId": "your-integration.faceRecognition",
  "type": "your-integration.faceMatchEvent.v1",
  "dataSchemas": ["your-integration.faceMatchData.v1"],
  "data": [
    {
      "type": "your-integration.faceMatchData.v1",
      "creatorId": "your-integration.faceRecognition",
      "personId": "person-abc123",
      "confidence": 0.97,
      "boundingBox": [0.22, 0.35, 0.28, 0.45]
    }
  ]
}
```

### Fields

| Field | Required | Description |
|---|---|---|
| `startTimestamp` | Yes | When the observed occurrence began. Use the triggering event's `startTimestamp`. |
| `endTimestamp` | Yes | When it ended. Use the triggering event's `endTimestamp`. |
| `span` | Yes | `true` if the event has duration, `false` if instantaneous. |
| `accountId` | Yes | The account ID from the triggering event. |
| `actorId` | Yes | The camera or device ID the event is attributed to. |
| `actorAccountId` | Yes | Same as `accountId` in most cases. |
| `actorType` | Yes | `camera`, `bridge`, `user`, or `account`. |
| `creatorId` | Yes | Your system's identifier, e.g. `your-company.serviceName`. |
| `type` | Yes | Your event type string. Must be from the list of supported event types — register custom types with EEN support. |
| `dataSchemas` | No | Array of schema type strings for your `data` objects. |
| `data` | No | Array of structured payload objects. Each must have a `type` matching an entry in `dataSchemas`. |

### Response

```json
{
  "id": "9cff02be-5eae-11ee-8c99-0242ac120002",
  "startTimestamp": "2024-03-15T07:34:23.032+00:00",
  ...all request fields...
}
```

The `id` field is assigned by EEN. The created event is now visible in the EEN timeline, queryable via `GET /events`, and can trigger automations.

---

## Code Examples

### Python — Full Pipeline

```python
import requests
from datetime import datetime

def subscribe_to_events(
    access_token: str,
    base_url: str,
    webhook_url: str,
    webhook_secret: str,
    camera_ids: list[str],
    event_types: list[str],
) -> dict:
    response = requests.post(
        f"https://{base_url}/api/v3.0/eventSubscriptions",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "deliveryConfig": {
                "type": "webhook.v1",
                "url": webhook_url,
                "authorizationHeader": f"Bearer {webhook_secret}",
            },
            "filters": [
                {
                    "resourceType": "camera",
                    "resourceIds": camera_ids,
                    "types": event_types,
                }
            ],
        },
    )
    response.raise_for_status()
    return response.json()  # { id, deliveryConfig, filters, lifeCycle }


def get_recorded_snapshot(
    access_token: str,
    base_url: str,
    device_id: str,
    timestamp: str,  # ISO 8601 with +00:00
    recorded_type: str = "main",
) -> bytes:
    """Returns JPEG bytes of the frame nearest to the given timestamp."""
    response = requests.get(
        f"https://{base_url}/api/v3.0/media/recordedImage.jpeg",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "deviceId": device_id,
            "recordedType": recorded_type,
            "timestampGreaterOrEqual": timestamp,
        },
    )
    response.raise_for_status()
    return response.content


def sample_span_frames(
    access_token: str,
    base_url: str,
    device_id: str,
    start_ts: str,
    end_ts: str,
    num_samples: int = 5,
) -> list[bytes]:
    """Sample N evenly-spaced frames across a span event window."""
    from datetime import datetime, timezone
    start = datetime.fromisoformat(start_ts)
    end = datetime.fromisoformat(end_ts)
    duration = (end - start).total_seconds()
    frames = []
    for i in range(num_samples):
        offset = duration * (i / max(num_samples - 1, 1))
        ts_dt = start + __import__('datetime').timedelta(seconds=offset)
        ts = ts_dt.isoformat().replace('+00:00', '+00:00')
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        frame = get_recorded_snapshot(access_token, base_url, device_id, ts)
        frames.append(frame)
    return frames


def create_derived_event(
    access_token: str,
    base_url: str,
    actor_id: str,
    actor_account_id: str,
    account_id: str,
    start_ts: str,
    end_ts: str,
    creator_id: str,
    event_type: str,
    data_schemas: list[str],
    data: list[dict],
) -> dict:
    response = requests.post(
        f"https://{base_url}/api/v3.0/events",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "startTimestamp": start_ts,
            "endTimestamp": end_ts,
            "span": start_ts != end_ts,
            "accountId": account_id,
            "actorId": actor_id,
            "actorAccountId": actor_account_id,
            "actorType": "camera",
            "creatorId": creator_id,
            "type": event_type,
            "dataSchemas": data_schemas,
            "data": data,
        },
    )
    response.raise_for_status()
    return response.json()


# --- Webhook handler (Flask example) ---
# from flask import Flask, request
# app = Flask(__name__)
# span_starts = {}  # { event_signature: start_data }
#
# @app.route('/een-webhook', methods=['POST'])
# def handle_event():
#     event = request.json
#     if event.get('span') and event['startTimestamp'] == event['endTimestamp']:
#         # Span start — record and wait
#         key = f"{event['actorId']}:{event['type']}:{event['startTimestamp']}"
#         span_starts[key] = event
#     elif event.get('span') and event['startTimestamp'] != event['endTimestamp']:
#         # Span end — full window available
#         frames = sample_span_frames(
#             access_token, base_url,
#             event['actorId'],
#             event['startTimestamp'],
#             event['endTimestamp'],
#         )
#         # Run your model on frames...
#         # Then create derived event:
#         create_derived_event(access_token, base_url, ...)
#     return '', 200
```

### TypeScript — Full Pipeline

```typescript
interface SubscriptionResponse {
  id: string;
  lifeCycle: "persistent" | "temporary";
}

async function subscribeToEvents(
  accessToken: string,
  baseUrl: string,
  webhookUrl: string,
  webhookSecret: string,
  cameraIds: string[],
  eventTypes: string[]
): Promise<SubscriptionResponse> {
  const response = await fetch(
    `https://${baseUrl}/api/v3.0/eventSubscriptions`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        deliveryConfig: {
          type: "webhook.v1",
          url: webhookUrl,
          authorizationHeader: `Bearer ${webhookSecret}`,
        },
        filters: [
          {
            resourceType: "camera",
            resourceIds: cameraIds,
            types: eventTypes,
          },
        ],
      }),
    }
  );
  if (!response.ok) throw new Error(`Subscribe failed: ${response.status}`);
  return response.json();
}

async function getRecordedSnapshot(
  accessToken: string,
  baseUrl: string,
  deviceId: string,
  timestamp: string, // ISO 8601 with +00:00
  recordedType: "main" | "preview" = "main"
): Promise<{ jpeg: ArrayBuffer; actualTimestamp: string; nextToken?: string }> {
  const params = new URLSearchParams({
    deviceId,
    recordedType,
    timestampGreaterOrEqual: timestamp,
  });
  const response = await fetch(
    `https://${baseUrl}/api/v3.0/media/recordedImage.jpeg?${params}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  );
  if (!response.ok) throw new Error(`Snapshot failed: ${response.status}`);
  return {
    jpeg: await response.arrayBuffer(),
    actualTimestamp: response.headers.get("X-Een-Timestamp") ?? timestamp,
    nextToken: response.headers.get("X-Een-NextToken") ?? undefined,
  };
}

async function sampleSpanFrames(
  accessToken: string,
  baseUrl: string,
  deviceId: string,
  startTs: string,
  endTs: string,
  numSamples = 5
): Promise<ArrayBuffer[]> {
  const start = new Date(startTs).getTime();
  const end = new Date(endTs).getTime();
  const duration = end - start;
  const frames: ArrayBuffer[] = [];

  for (let i = 0; i < numSamples; i++) {
    const offset = duration * (i / Math.max(numSamples - 1, 1));
    const ts = new Date(start + offset).toISOString().replace(/Z$/, "+00:00");
    const { jpeg } = await getRecordedSnapshot(accessToken, baseUrl, deviceId, ts);
    frames.push(jpeg);
  }
  return frames;
}

async function createDerivedEvent(
  accessToken: string,
  baseUrl: string,
  params: {
    actorId: string;
    actorAccountId: string;
    accountId: string;
    startTs: string;
    endTs: string;
    creatorId: string;
    eventType: string;
    dataSchemas: string[];
    data: Record<string, unknown>[];
  }
): Promise<{ id: string }> {
  const response = await fetch(`https://${baseUrl}/api/v3.0/events`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      startTimestamp: params.startTs,
      endTimestamp: params.endTs,
      span: params.startTs !== params.endTs,
      accountId: params.accountId,
      actorId: params.actorId,
      actorAccountId: params.actorAccountId,
      actorType: "camera",
      creatorId: params.creatorId,
      type: params.eventType,
      dataSchemas: params.dataSchemas,
      data: params.data,
    }),
  });
  if (!response.ok) throw new Error(`createEvent failed: ${response.status}`);
  return response.json();
}

// Webhook handler — detect span start vs end
function handleWebhookEvent(event: {
  span: boolean;
  startTimestamp: string;
  endTimestamp: string;
  actorId: string;
  type: string;
}) {
  const isSpanEnd =
    event.span && event.startTimestamp !== event.endTimestamp;
  const isSpanStart =
    event.span && event.startTimestamp === event.endTimestamp;

  if (isSpanEnd) {
    // Full window available — sample and enrich
    sampleSpanFrames(accessToken, baseUrl, event.actorId,
      event.startTimestamp, event.endTimestamp)
      .then(frames => {
        // run inference on frames, then create derived event
      });
  }
}
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public static async Task<string> SubscribeToEvents(
    string accessToken, string baseUrl,
    string webhookUrl, string webhookSecret,
    string[] cameraIds, string[] eventTypes)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var body = new
    {
        deliveryConfig = new
        {
            type = "webhook.v1",
            url = webhookUrl,
            authorizationHeader = $"Bearer {webhookSecret}",
        },
        filters = new[]
        {
            new
            {
                resourceType = "camera",
                resourceIds = cameraIds,
                types = eventTypes,
            }
        }
    };

    var json = JsonSerializer.Serialize(body);
    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/eventSubscriptions",
        new StringContent(json, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();

    var result = JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
    return result.GetProperty("id").GetString()!; // subscription ID
}

public static async Task<byte[]> GetRecordedSnapshot(
    string accessToken, string baseUrl,
    string deviceId, string timestamp,
    string recordedType = "main")
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var qs = $"deviceId={Uri.EscapeDataString(deviceId)}" +
             $"&recordedType={recordedType}" +
             $"&timestampGreaterOrEqual={Uri.EscapeDataString(timestamp)}";

    var response = await client.GetAsync(
        $"https://{baseUrl}/api/v3.0/media/recordedImage.jpeg?{qs}");
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadAsByteArrayAsync();
}

public static async Task<string> CreateDerivedEvent(
    string accessToken, string baseUrl,
    string actorId, string accountId,
    string startTs, string endTs,
    string creatorId, string eventType,
    string[] dataSchemas, object[] data)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var body = new
    {
        startTimestamp = startTs,
        endTimestamp = endTs,
        span = startTs != endTs,
        accountId,
        actorId,
        actorAccountId = accountId,
        actorType = "camera",
        creatorId,
        type = eventType,
        dataSchemas,
        data,
    };

    var json = JsonSerializer.Serialize(body);
    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/events",
        new StringContent(json, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();

    var result = JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
    return result.GetProperty("id").GetString()!;
}
```

### Rust

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
struct DeliveryConfig<'a> {
    #[serde(rename = "type")]
    delivery_type: &'a str,
    url: &'a str,
    #[serde(rename = "authorizationHeader")]
    authorization_header: &'a str,
}

#[derive(Serialize)]
struct EventFilter<'a> {
    #[serde(rename = "resourceType")]
    resource_type: &'a str,
    #[serde(rename = "resourceIds")]
    resource_ids: &'a [&'a str],
    types: &'a [&'a str],
}

#[derive(Serialize)]
struct SubscribeBody<'a> {
    #[serde(rename = "deliveryConfig")]
    delivery_config: DeliveryConfig<'a>,
    filters: Vec<EventFilter<'a>>,
}

#[derive(Deserialize)]
pub struct SubscriptionResponse {
    pub id: String,
    #[serde(rename = "lifeCycle")]
    pub life_cycle: String,
}

pub async fn subscribe_to_events(
    access_token: &str,
    base_url: &str,
    webhook_url: &str,
    webhook_secret: &str,
    camera_ids: &[&str],
    event_types: &[&str],
) -> Result<SubscriptionResponse, reqwest::Error> {
    let auth_header = format!("Bearer {}", webhook_secret);
    let body = SubscribeBody {
        delivery_config: DeliveryConfig {
            delivery_type: "webhook.v1",
            url: webhook_url,
            authorization_header: &auth_header,
        },
        filters: vec![EventFilter {
            resource_type: "camera",
            resource_ids: camera_ids,
            types: event_types,
        }],
    };

    Client::new()
        .post(format!("https://{}/api/v3.0/eventSubscriptions", base_url))
        .bearer_auth(access_token)
        .json(&body)
        .send()
        .await?
        .error_for_status()?
        .json::<SubscriptionResponse>()
        .await
}

pub async fn get_recorded_snapshot(
    access_token: &str,
    base_url: &str,
    device_id: &str,
    timestamp: &str,
    recorded_type: &str,
) -> Result<bytes::Bytes, reqwest::Error> {
    Client::new()
        .get(format!("https://{}/api/v3.0/media/recordedImage.jpeg", base_url))
        .bearer_auth(access_token)
        .query(&[
            ("deviceId", device_id),
            ("recordedType", recorded_type),
            ("timestampGreaterOrEqual", timestamp),
        ])
        .send()
        .await?
        .error_for_status()?
        .bytes()
        .await
}
```

---

## Notes

- **Webhook delivery is not guaranteed exactly-once.** Design your handler to be idempotent — the same event may be delivered more than once.
- **Span start detection:** `span === true && startTimestamp === endTimestamp` indicates start. `span === true && startTimestamp !== endTimestamp` indicates end.
- **Custom event types** must be registered with Eagle Eye. Use reverse-domain notation: `com.yourcompany.serviceName.eventName.v1`.
- **`creatorId`** identifies your service, not the actor. Use a stable, unique string like `com.yourcompany.faceRecognition`.
- **Timestamps in snapshots:** The `X-Een-Timestamp` response header contains the actual frame time, which may differ slightly from the requested time. Use this for accurate metadata.
- **SSE alternative:** Set `deliveryConfig.type = "serverSentEvents.v1"` for browser-based real-time subscriptions. SSE subscriptions are `temporary` (session-scoped) rather than `persistent`.
