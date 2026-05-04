# Core Function Group 10: Device Management

## Purpose

Manage the physical layer of the platform — cameras and bridges. This covers retrieving and updating device configuration, monitoring device status, and the provisioning workflow for adding new cameras to a bridge. Any integration that manages its own hardware fleet, builds an admin console, or needs to respond to device connectivity changes needs these functions.

---

## Key Concepts

**Bridges** are on-premise gateways that connect cameras to the EEN cloud. One bridge typically serves multiple cameras. A bridge must exist on the account before cameras connected to it can be added.

**Cameras** are video sources associated with an account through a bridge. The camera `id` (8-char hex) is the primary identifier used throughout the API.

**Available Devices** are cameras discovered by a bridge that have not yet been added to the account. Use `GET /availableDevices` to find them, then `POST /cameras` to provision them.

---

## Cameras

### Get Camera

```
GET https://{baseUrl}/api/v3.0/cameras/{cameraId}
Authorization: Bearer {access_token}
```

| Query Parameter | Description |
|---|---|
| `include` | Additional fields: `status`, `locationSummary`, `bridges`, `permissions` |

**Response:**
```json
{
  "id": "10097dd2",
  "name": "Front Door",
  "accountId": "00001106",
  "bridgeId": "100d4c41",
  "locationId": "loc-abc123",
  "createTimestamp": "2023-06-01T09:00:00.000+00:00",
  "status": {
    "connectionStatus": "online"
  }
}
```

### Update Camera

```
PATCH https://{baseUrl}/api/v3.0/cameras/{cameraId}
Authorization: Bearer {access_token}
Content-Type: application/json
```

Send only the fields to change. Common updatable fields: `name`, `locationId`, `tags`.

```json
{
  "name": "Front Door — Building A",
  "tags": ["entrance", "building-a"]
}
```

Returns `204 No Content`.

### Get Camera Status

```
GET https://{baseUrl}/api/v3.0/cameras/{cameraId}?include=status
```

Or use the status subresource directly for a lightweight check:

```
GET https://{baseUrl}/api/v3.0/cameras/{cameraId}/status
```

**Status response:**
```json
{
  "connectionStatus": "online"
}
```

`connectionStatus` values: `online`, `offline`, `unknown`.

### Update Camera Status

```
PATCH https://{baseUrl}/api/v3.0/cameras/{cameraId}/status
Authorization: Bearer {access_token}
Content-Type: application/json
```

Used to administratively change device state (e.g. enable/disable recording).

### Delete Camera

```
DELETE https://{baseUrl}/api/v3.0/cameras/{cameraId}
```

Disassociates the camera from the account. **Removes all recordings and references.** Returns `204 No Content`.

---

## Bridges

### List Bridges

```
GET https://{baseUrl}/api/v3.0/bridges
Authorization: Bearer {access_token}
```

Key query parameters:

| Parameter | Description |
|---|---|
| `locationId__in` | Filter by location |
| `name__contains` | Filter by name |
| `status__in` | Filter by status (`online`, `offline`) |
| `include` | Additional fields |
| `pageSize`, `pageToken` | Pagination |

**Response:**
```json
{
  "results": [
    {
      "id": "100d4c41",
      "name": "Building A Bridge",
      "locationId": "loc-abc123",
      "status": { "connectionStatus": "online" }
    }
  ],
  "nextPageToken": "",
  "totalSize": 3
}
```

### Get Bridge

```
GET https://{baseUrl}/api/v3.0/bridges/{bridgeId}?include=status
```

### Update Bridge

```
PATCH https://{baseUrl}/api/v3.0/bridges/{bridgeId}
Content-Type: application/json
```

Updatable fields: `name`, `locationId`, `tags`.

### Delete Bridge

```
DELETE https://{baseUrl}/api/v3.0/bridges/{bridgeId}
```

**Removes the bridge and all cameras connected to it, including their recordings.** This is irreversible. Returns `204 No Content`.

### Get Bridge Status

```
GET https://{baseUrl}/api/v3.0/bridges/{bridgeId}/status
```

Returns `{ "connectionStatus": "online" }` — same shape as camera status.

---

## Device Provisioning

### Discover Available Devices

Bridges continuously scan for cameras on the local network. Discovered cameras that haven't been added to the account appear in `/availableDevices`.

```
GET https://{baseUrl}/api/v3.0/availableDevices
Authorization: Bearer {access_token}
```

| Parameter | Description |
|---|---|
| `bridgeId__in` | Filter by specific bridge(s) |
| `deviceType__in` | Filter by device type |
| `state__in` | Filter by discovery state |
| `pageSize`, `pageToken` | Pagination |

**Response:**
```json
{
  "results": [
    {
      "id": "avail-abc123",
      "bridgeId": "100d4c41",
      "deviceType": "camera",
      "ipAddress": "192.168.1.105",
      "macAddress": "AA:BB:CC:DD:EE:FF",
      "model": "Axis P3245-V",
      "state": "discovered"
    }
  ],
  "totalSize": 2
}
```

### Trigger a Bridge Scan

Force a bridge to scan for new devices immediately:

```
POST https://{baseUrl}/api/v3.0/bridges/{bridgeId}/devices:scan
Authorization: Bearer {access_token}
```

Returns `204 No Content`. After a short delay, new devices appear in `/availableDevices`.

### Add Camera to Account

Once a device appears in `/availableDevices`, add it with `POST /cameras` (documented in `03-list-cameras.md`). The bridge handles the association.

---

## Code Examples

### Python

```python
import requests
from typing import Iterator

def get_camera(
    access_token: str,
    base_url: str,
    camera_id: str,
    include: str = "status",
) -> dict:
    r = requests.get(
        f"https://{base_url}/api/v3.0/cameras/{camera_id}",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        params={"include": include},
    )
    r.raise_for_status()
    return r.json()


def update_camera(
    access_token: str,
    base_url: str,
    camera_id: str,
    **fields,
) -> None:
    r = requests.patch(
        f"https://{base_url}/api/v3.0/cameras/{camera_id}",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=fields,
    )
    r.raise_for_status()


def get_camera_status(access_token: str, base_url: str, camera_id: str) -> str:
    r = requests.get(
        f"https://{base_url}/api/v3.0/cameras/{camera_id}/status",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    r.raise_for_status()
    return r.json().get("connectionStatus", "unknown")


def list_bridges(
    access_token: str,
    base_url: str,
    **filters,
) -> Iterator[dict]:
    params = {"pageSize": 100, **filters}
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    while True:
        r = requests.get(f"https://{base_url}/api/v3.0/bridges", headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        yield from data["results"]
        if not data.get("nextPageToken"):
            break
        params["pageToken"] = data["nextPageToken"]


def list_available_devices(
    access_token: str,
    base_url: str,
    bridge_id: str | None = None,
) -> list[dict]:
    params: dict = {"pageSize": 100}
    if bridge_id:
        params["bridgeId__in"] = bridge_id
    r = requests.get(
        f"https://{base_url}/api/v3.0/availableDevices",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        params=params,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def scan_bridge_for_devices(access_token: str, base_url: str, bridge_id: str) -> None:
    r = requests.post(
        f"https://{base_url}/api/v3.0/bridges/{bridge_id}/devices:scan",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    r.raise_for_status()


# Provisioning workflow
import time

def provision_new_cameras(access_token, base_url, bridge_id):
    scan_bridge_for_devices(access_token, base_url, bridge_id)
    time.sleep(15)  # Allow bridge time to complete scan
    available = list_available_devices(access_token, base_url, bridge_id)
    for device in available:
        print(f"Found: {device['model']} at {device.get('ipAddress')} — ID: {device['id']}")
    return available
```

### TypeScript

```typescript
interface CameraStatus {
  connectionStatus: "online" | "offline" | "unknown";
}

interface Bridge {
  id: string;
  name: string;
  locationId?: string;
  status?: CameraStatus;
}

interface AvailableDevice {
  id: string;
  bridgeId: string;
  deviceType: string;
  ipAddress?: string;
  model?: string;
  state: string;
}

async function getCamera(
  accessToken: string,
  baseUrl: string,
  cameraId: string,
  include = "status"
): Promise<Record<string, unknown>> {
  const res = await fetch(
    `https://${baseUrl}/api/v3.0/cameras/${cameraId}?include=${include}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  );
  if (!res.ok) throw new Error(`getCamera: ${res.status}`);
  return res.json();
}

async function updateCamera(
  accessToken: string,
  baseUrl: string,
  cameraId: string,
  fields: Record<string, unknown>
): Promise<void> {
  const res = await fetch(`https://${baseUrl}/api/v3.0/cameras/${cameraId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error(`updateCamera: ${res.status}`);
}

async function listBridges(
  accessToken: string,
  baseUrl: string,
  filters: Record<string, string> = {}
): Promise<Bridge[]> {
  const bridges: Bridge[] = [];
  let pageToken: string | undefined;
  do {
    const params = new URLSearchParams({ pageSize: "100", ...filters });
    if (pageToken) params.set("pageToken", pageToken);
    const res = await fetch(`https://${baseUrl}/api/v3.0/bridges?${params}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) throw new Error(`listBridges: ${res.status}`);
    const data = await res.json();
    bridges.push(...data.results);
    pageToken = data.nextPageToken || undefined;
  } while (pageToken);
  return bridges;
}

async function scanBridgeForDevices(
  accessToken: string,
  baseUrl: string,
  bridgeId: string
): Promise<void> {
  const res = await fetch(
    `https://${baseUrl}/api/v3.0/bridges/${bridgeId}/devices:scan`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
    }
  );
  if (!res.ok) throw new Error(`scanBridge: ${res.status}`);
}

async function listAvailableDevices(
  accessToken: string,
  baseUrl: string,
  bridgeId?: string
): Promise<AvailableDevice[]> {
  const params = new URLSearchParams({ pageSize: "100" });
  if (bridgeId) params.set("bridgeId__in", bridgeId);
  const res = await fetch(
    `https://${baseUrl}/api/v3.0/availableDevices?${params}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  );
  if (!res.ok) throw new Error(`listAvailableDevices: ${res.status}`);
  const data = await res.json();
  return data.results;
}
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public static async Task UpdateCamera(
    string accessToken, string baseUrl,
    string cameraId, object fields)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var body = JsonSerializer.Serialize(fields);
    var response = await client.PatchAsync(
        $"https://{baseUrl}/api/v3.0/cameras/{cameraId}",
        new StringContent(body, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();
}

public static async Task<string> GetCameraConnectionStatus(
    string accessToken, string baseUrl, string cameraId)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);
    client.DefaultRequestHeaders.Accept.Add(
        new MediaTypeWithQualityHeaderValue("application/json"));

    var response = await client.GetAsync(
        $"https://{baseUrl}/api/v3.0/cameras/{cameraId}/status");
    response.EnsureSuccessStatusCode();

    var doc = JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
    return doc.GetProperty("connectionStatus").GetString() ?? "unknown";
}

public static async Task ScanBridgeForDevices(
    string accessToken, string baseUrl, string bridgeId)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/bridges/{bridgeId}/devices:scan",
        new StringContent("", Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();
}
```

### Rust

```rust
use reqwest::Client;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct DeviceStatus {
    #[serde(rename = "connectionStatus")]
    pub connection_status: String,
}

#[derive(Debug, Deserialize)]
pub struct Bridge {
    pub id: String,
    pub name: String,
    #[serde(rename = "locationId")]
    pub location_id: Option<String>,
}

pub async fn get_camera_status(
    access_token: &str,
    base_url: &str,
    camera_id: &str,
) -> Result<DeviceStatus, reqwest::Error> {
    Client::new()
        .get(format!(
            "https://{}/api/v3.0/cameras/{}/status",
            base_url, camera_id
        ))
        .bearer_auth(access_token)
        .header("Accept", "application/json")
        .send()
        .await?
        .error_for_status()?
        .json::<DeviceStatus>()
        .await
}

pub async fn scan_bridge_for_devices(
    access_token: &str,
    base_url: &str,
    bridge_id: &str,
) -> Result<(), reqwest::Error> {
    Client::new()
        .post(format!(
            "https://{}/api/v3.0/bridges/{}/devices:scan",
            base_url, bridge_id
        ))
        .bearer_auth(access_token)
        .send()
        .await?
        .error_for_status()?;
    Ok(())
}
```

---

## Notes

- **Delete is destructive for both cameras and bridges.** Camera deletion removes all recordings. Bridge deletion removes the bridge *and all its cameras* and their recordings. Always confirm intent before calling DELETE on either resource.
- **Scan → wait → list:** After `POST /bridges/{id}/devices:scan`, allow 10–15 seconds before calling `GET /availableDevices`. The bridge needs time to complete the local network scan.
- **Status polling for health monitoring:** For real-time device health, prefer subscribing to `een.deviceCloudStatusUpdateEvent.v1` via the event lifecycle pipeline (document 06) rather than polling `GET /cameras/{id}/status`. Polling is appropriate for occasional checks; webhooks are appropriate for monitoring.
- **`include=status` on list endpoints:** Add `include=status` when calling `GET /cameras` or `GET /bridges` to get connection status for all devices in one request, rather than making N individual status calls.
- **Camera IDs are stable.** Once a camera is added to an account, its ID does not change. You can store IDs safely and use them as long-term identifiers.
