---
name: een-api
description: Eagle Eye Networks (Brivo Video) API v3 reference. Invoke before answering any questions about the EEN API or generating code against it. Covers authentication, token refresh, camera listing, live feeds, event queries, event lifecycle/webhooks/AI enrichment, user and account management, automations, video export, and device/bridge management — with working code examples in Python, TypeScript, C#, and Rust.
---

# Eagle Eye Networks API v3 — Reference Index

## How to Use This Skill

Before responding to any EEN API question or writing code, read the relevant subject documents listed in the Document Map below using the Read tool. Each document contains exact endpoint details, all query parameters, full response schemas, and working code in Python, TypeScript, C#, and Rust.

---

## System Overview

Eagle Eye Networks API v3 is a cloud-based video surveillance and security management platform. It manages cameras, bridges (on-premise gateways), recorded video, live streams, events (motion, status, LPR, etc.), user accounts, and automated alert rules.

**Base architecture:**
- Auth server: `auth.eagleeyenetworks.com` — handles all OAuth token operations
- API server: per-account hostname returned at login, e.g. `api.c001.eagleeyenetworks.com`
- All API calls use `https://{baseUrl}/api/v3.0/{resource}`
- All requests require `Authorization: Bearer {access_token}`

---

## Core Function Groups

| # | Function Group | Document | When to use |
|---|---|---|---|
| 1 | `authenticate` | [01-authenticate.md](01-authenticate.md) | First-time login; exchange auth code for tokens |
| 2 | `refreshAccessToken` | [02-refresh-access-token.md](02-refresh-access-token.md) | Renew expired access token using refresh token |
| 3 | `listCameras` | [03-list-cameras.md](03-list-cameras.md) | Get camera IDs and metadata |
| 4 | `getLiveFeed` | [04-get-live-feed.md](04-get-live-feed.md) | Get live stream URLs (RTSP, HLS, WebRTC, etc.) |
| 5 | `queryEvents` | [05-query-events.md](05-query-events.md) | Query historical events, motion, status changes |
| 6 | Event Lifecycle | [06-event-lifecycle.md](06-event-lifecycle.md) | Webhooks, snapshot collection, AI enrichment pipeline |
| 7 | User & Account Management | [07-user-account-management.md](07-user-account-management.md) | CRUD for users, roles, role assignments |
| 8 | Automations | [08-automations.md](08-automations.md) | Alert actions, condition rules, action rules |
| 9 | Video Export | [09-video-export.md](09-video-export.md) | Async export pipeline (video, timelapse, bundle) |
| 10 | Device Management | [10-device-management.md](10-device-management.md) | Camera/bridge CRUD, device provisioning |

---

## Authentication and Base URL — Critical Concepts

**All roads start with auth.** No API call works without a valid Bearer token. The standard flow is:

```
1. Redirect user to authorization URL  →  user logs in and consents
2. Receive ?code= in redirect          →  call authenticate()
3. Receive access_token + refresh_token + httpsBaseUrl
4. Store all three. Use httpsBaseUrl for every API call.
5. When access_token expires (≤12h)    →  call refreshAccessToken()
6. After 90 days or 401 on refresh    →  restart from step 1
```

**The base URL is account-specific.** A user on cluster `c001` has a different base URL than one on `c013`. This URL is returned in the token response as `httpsBaseUrl.hostname`. Store it alongside the tokens. Do not hardcode it.

If you have a valid access token but no stored base URL, retrieve it via:
```
GET https://api.eagleeyenetworks.com/api/v3.0/clientSettings
Authorization: Bearer {access_token}
```

---

## Typical Workflows

### "Show me the live video from camera X"

```
1. listCameras()      → find the camera ID by name or list all
2. getLiveFeed()      → request rtspUrl or hlsUrl for that camera ID
3. Append &access_token={token} to the RTSP URL before use
```

### "Show me motion events from yesterday"

```
1. listCameras()      → get camera ID
2. queryEvents()      → actor=camera:{id}, type__in=een.motionDetectionEvent.v1,
                         startTimestamp__gte=..., startTimestamp__lte=...
```

### "Show me recorded video for a time range"

```
1. listCameras()      → get camera ID
2. GET /media         → same query pattern as queryEvents, include=rtspUrl
3. Append &access_token={token} to the RTSP URL before use
```

### "Is camera X online?"

```
1. listCameras()      → include=status, filter by id or name
2. Check status.connectionStatus === "online"
   OR
2. queryEvents()      → type__in=een.deviceCloudStatusUpdateEvent.v1,
                         actor=camera:{id}, sort=-startTimestamp, pageSize=1
```

### "Notify me when motion is detected (webhook / AI enrichment)"

```
1. POST /eventSubscriptions  → subscribe to een.motionDetectionEvent.v1 with deliveryConfig.type="webhook.v1"
2. On webhook receipt:
   - If startTimestamp === endTimestamp → span start; wait for end notification
   - If startTimestamp !== endTimestamp → span end; sample frames via GET /media/recordedImage.jpeg
3. POST /events              → inject derived event with AI analysis result
```

### "Export a video clip"

```
1. POST /exports    → { type: "video", deviceId, startTimestamp, endTimestamp }
2. Poll GET /jobs/{jobId} until status === "done"
3. GET /downloads   → retrieve signed download URL
```

### "Add a new user with a custom role"

```
1. POST /roles         → create role with desired permissions
2. POST /users         → create user (starts in "pending" state)
3. POST /roleAssignments:bulkCreate → assign role to user
```

### "Set up an alert that sends a Slack message on motion"

```
1. POST /alertActions              → type="slack", configure webhook URL
2. POST /eventAlertConditionRules  → type=een.motionDetectionEvent.v1, enabled=true
3. POST /alertActionRules          → link alertActionId + conditionRuleId
```

---

## Universal Pagination Pattern

All list endpoints (`/cameras`, `/feeds`, `/events`, `/media`, etc.) use the same cursor-based pagination:

**Request:** Add `pageSize=N` (max 100) and optionally `pageToken` from previous response.

**Response always contains:**
```json
{
  "results": [...],
  "nextPageToken": "MToxMDA...",
  "prevPageToken": "",
  "totalSize": 156
}
```

**To fetch all pages:**
```python
# Pseudocode — works for any list endpoint
params = { "pageSize": 100, ...other_filters }
while True:
    data = GET /endpoint, params=params
    process(data["results"])
    if not data["nextPageToken"]:
        break
    params["pageToken"] = data["nextPageToken"]
```

`totalSize` is the total count of all matching records, not the count on this page.

---

## Universal Error Pattern

All endpoints return standard HTTP status codes with a JSON error body:

```json
{
  "code": 401,
  "status": "unauthenticated",
  "message": "The request did not include valid authentication credentials."
}
```

| Status | Meaning | Action |
|---|---|---|
| `400` | Validation error — bad parameter, wrong format | Fix the request |
| `401` | Missing or expired access token | Refresh token or re-authenticate |
| `403` | Authenticated but not authorized | User lacks permission for this resource |
| `404` | Resource not found | Check the ID is correct |
| `500` | Server error | Retry once; if persistent, report to support |

On `401` from any API call: attempt `refreshAccessToken`. If the refresh also returns `401`, the refresh token is expired — trigger Phase 1 re-authorization.

---

## Standard Request Headers

Every API call must include:

```
Authorization: Bearer {access_token}
Accept: application/json
```

POST/PATCH calls with a JSON body also need:
```
Content-Type: application/json
```

---

## Timestamp Format

All timestamps throughout the API are ISO 8601 with millisecond precision and `+00:00` timezone offset:
```
2024-03-15T07:59:22.946+00:00
```

**Always use `+00:00` notation. The `Z` suffix is rejected by some endpoints (confirmed: `GET /media` returns 400 on `Z` input).** All responses use `+00:00`.

When constructing timestamps in JavaScript/TypeScript, `Date.toISOString()` produces the `Z` suffix by default. Replace it:

```typescript
// Correct — produces "2024-03-15T07:59:22.946+00:00"
const ts = new Date().toISOString().replace(/Z$/, '+00:00')

// Wrong — toISOString() default produces "2024-03-15T07:59:22.946Z" which is rejected by /media
const ts = new Date().toISOString()
```

For a full UTC day range:
```typescript
const date = '2024-03-15' // YYYY-MM-DD from a date picker

const startOfDay = new Date(`${date}T00:00:00`).toISOString().replace(/Z$/, '+00:00')
// → "2024-03-15T06:00:00.000+00:00"  (if local timezone is UTC-6)

const endOfDay = new Date(`${date}T23:59:59`).toISOString().replace(/Z$/, '+00:00')
// → "2024-03-16T05:59:59.000+00:00"
```

---

## Key Identifiers

| Resource | ID format | Example |
|---|---|---|
| Camera | 8-char hex string | `10097dd2` |
| Bridge | 8-char hex string | `100d4c41` |
| Account | Zero-padded 8-digit string | `00001106` |
| Event | URL-safe base64 string | `nINlL0YuoRAnv9QcHKXi` |
| Location | Prefixed string | `loc-abc123` |

Camera and bridge IDs are stable and can be stored.

---

## What These Documents Do Not Cover

The full API also includes:

- **License Plate Recognition** — `GET /lprEvents`, `POST /lprVehicleLists`
- **AI video search** — `POST /videoAnalyticEvents:deepSearch`
- **PTZ control** — `PATCH /cameras/{id}/ptz`
- **Grouping** — `GET /locations`, `GET /layouts`
- **SSO configuration** — `PATCH /accounts/self/ssoAuthSettings`

For any of these, the same auth + base URL patterns apply. The pagination and error handling patterns transfer directly.

---

## Document Map

Read the relevant file(s) before generating code or answering endpoint-specific questions:

- [01-authenticate.md](01-authenticate.md) — OAuth2 authorization code flow, base URL extraction
- [02-refresh-access-token.md](02-refresh-access-token.md) — Token refresh, rotation, lifecycle
- [03-list-cameras.md](03-list-cameras.md) — GET /cameras, all filters, pagination
- [04-get-live-feed.md](04-get-live-feed.md) — GET /feeds, all stream URL types, RTSP auth
- [05-query-events.md](05-query-events.md) — GET /events, filters, data schemas, GET /media pattern
- [06-event-lifecycle.md](06-event-lifecycle.md) — POST /eventSubscriptions (webhooks), GET /media/recordedImage.jpeg, POST /events; AI enrichment pipeline; span event detection
- [07-user-account-management.md](07-user-account-management.md) — GET/POST/PATCH/DELETE /users, /roles, bulk role assignments
- [08-automations.md](08-automations.md) — AlertActions, EventAlertConditionRules, AlertActionRules; 16 action types; build order
- [09-video-export.md](09-video-export.md) — POST /exports, GET /jobs/{id} poll, GET /downloads; video/timelapse/bundle types
- [10-device-management.md](10-device-management.md) — Camera/bridge CRUD, status subresource, device provisioning scan workflow
