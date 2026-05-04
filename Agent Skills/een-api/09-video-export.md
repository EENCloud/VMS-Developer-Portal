# Core Function Group 9: Video Export

## Purpose

Export recorded video from the platform as downloadable files. This is an asynchronous two-step process: submit an export job, then poll until it completes and retrieve the download. Covers three export formats — video clip, timelapse, and bundle (multi-camera or extended period).

This is the path from "I need this footage" to "I have a file I can hand to law enforcement, share with a client, or archive."

---

## The Async Pipeline

```
1. POST /exports          ──► Job created, state: "pending" or "processing"
        │
        ▼
2. GET /jobs/{jobId}      ──► Poll until state == "done"
        │                      (check every 5–10 seconds)
        ▼
3. GET /downloads          ──► List completed downloads
   or
   GET /downloads/{id}     ──► Get download URL for specific export
        │
        ▼
4. Download the file       ──► Fetch the binary from the download URL
```

---

## Step 1: Create Export Job

```
POST https://{baseUrl}/api/v3.0/exports
Authorization: Bearer {access_token}
Content-Type: application/json
```

The `type` field discriminates the export format.

### Video Export

Exports a continuous video clip for a time window:

```json
{
  "deviceId": "10097dd2",
  "type": "video",
  "period": {
    "startTimestamp": "2024-03-15T07:00:00.000+00:00",
    "endTimestamp": "2024-03-15T07:30:00.000+00:00"
  },
  "osd": {
    "timeZone": "America/Chicago"
  },
  "info": {
    "name": "incident_2024-03-15_building-a",
    "directory": "/exports",
    "notes": "Potential unauthorized access — front door",
    "tags": ["incident", "building-a"]
  }
}
```

### Timelapse Export

Exports a compressed timelapse of a longer period:

```json
{
  "deviceId": "10097dd2",
  "type": "timeLapse",
  "period": {
    "startTimestamp": "2024-03-15T00:00:00.000+00:00",
    "endTimestamp": "2024-03-15T23:59:59.000+00:00"
  },
  "playbackMultiplier": 10,
  "osd": { "timeZone": "America/Chicago" },
  "info": { "name": "daily_timelapse_2024-03-15", "directory": "/timelapses" }
}
```

`playbackMultiplier`: how many times faster than real-time the timelapse plays. Default: 10.

### Bundle Export

Exports a multi-camera or extended period bundle:

```json
{
  "deviceId": "10097dd2",
  "type": "bundle",
  "period": {
    "startTimestamp": "2024-03-15T07:00:00.000+00:00",
    "endTimestamp": "2024-03-15T08:00:00.000+00:00"
  },
  "playbackMultiplier": 2,
  "osd": { "timeZone": "America/Chicago" },
  "info": { "name": "incident_bundle", "directory": "/exports" }
}
```

### Common Fields

| Field | Required | Description |
|---|---|---|
| `deviceId` | Yes | Camera ID |
| `type` | Yes | `video`, `timeLapse`, or `bundle` |
| `period.startTimestamp` | Yes | ISO 8601 with `+00:00` |
| `period.endTimestamp` | Yes | ISO 8601 with `+00:00` |
| `osd.timeZone` | No | IANA timezone for on-screen display timestamp overlay |
| `info.name` | No | File name for the export |
| `info.directory` | No | Directory path for the export |
| `info.notes` | No | Free-text notes attached to the export |
| `info.tags` | No | String array of tags |
| `playbackMultiplier` | No | For `timeLapse` and `bundle`. Default: 10 (timeLapse), 1 (bundle) |

### Response

```json
{
  "jobId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

Store the `jobId` for polling.

---

## Step 2: Poll Job Status

```
GET https://{baseUrl}/api/v3.0/jobs/{jobId}
Authorization: Bearer {access_token}
```

### Job States

| State | Meaning |
|---|---|
| `pending` | Queued, not yet started |
| `processing` | Actively being exported |
| `done` | Complete — download is available |
| `failed` | Export failed |
| `cancelled` | Cancelled via DELETE /jobs/{jobId} |

### Response

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "type": "export",
  "state": "done",
  "createTimestamp": "2024-03-15T07:35:00.000+00:00",
  "updateTimestamp": "2024-03-15T07:36:22.000+00:00",
  "expireTimestamp": "2024-03-22T07:36:22.000+00:00"
}
```

Poll `GET /jobs/{jobId}` every 5–10 seconds until `state === "done"` or `"failed"`. Do not poll faster than every 5 seconds.

### Cancel a Job

```
DELETE https://{baseUrl}/api/v3.0/jobs/{jobId}
```

Returns `204 No Content`.

---

## Step 3: Retrieve the Download

Once the job is `done`, the exported file appears in `/downloads`.

### List Downloads

```
GET https://{baseUrl}/api/v3.0/downloads
Authorization: Bearer {access_token}
```

Key query parameters:

| Parameter | Description |
|---|---|
| `name` | Exact match on export name |
| `name__contains` | Partial match on name |
| `directory` | Filter by directory |
| `tags__contains` | Filter by tag |
| `createTimestamp__gte`, `createTimestamp__lte` | Filter by creation time |
| `include` | Include download URL in response |
| `pageSize`, `pageToken` | Pagination |

### Get Specific Download

```
GET https://{baseUrl}/api/v3.0/downloads/{downloadId}?include=url
Authorization: Bearer {access_token}
```

Including `include=url` returns a pre-signed download URL in the response.

---

## Code Examples

### Python — Full Async Export Pipeline

```python
import requests
import time

def create_export(
    access_token: str,
    base_url: str,
    device_id: str,
    start_ts: str,
    end_ts: str,
    export_type: str = "video",
    name: str = "export",
    time_zone: str = "UTC",
    playback_multiplier: int | None = None,
) -> str:
    """Returns jobId."""
    body = {
        "deviceId": device_id,
        "type": export_type,
        "period": {"startTimestamp": start_ts, "endTimestamp": end_ts},
        "osd": {"timeZone": time_zone},
        "info": {"name": name, "directory": "/exports"},
    }
    if playback_multiplier is not None:
        body["playbackMultiplier"] = playback_multiplier

    r = requests.post(
        f"https://{base_url}/api/v3.0/exports",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=body,
    )
    r.raise_for_status()
    return r.json()["jobId"]


def poll_job(
    access_token: str,
    base_url: str,
    job_id: str,
    interval_seconds: int = 5,
    timeout_seconds: int = 600,
) -> dict:
    """Polls until job is done or failed. Returns final job object."""
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        r = requests.get(
            f"https://{base_url}/api/v3.0/jobs/{job_id}",
            headers=headers,
        )
        r.raise_for_status()
        job = r.json()
        state = job.get("state")

        if state == "done":
            return job
        if state == "failed":
            raise RuntimeError(f"Export job {job_id} failed")
        if state == "cancelled":
            raise RuntimeError(f"Export job {job_id} was cancelled")

        time.sleep(interval_seconds)

    raise TimeoutError(f"Export job {job_id} did not complete within {timeout_seconds}s")


def get_download_url(
    access_token: str,
    base_url: str,
    name: str,
) -> str | None:
    """Find a download by name and return its URL."""
    r = requests.get(
        f"https://{base_url}/api/v3.0/downloads",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        params={"name": name, "include": "url"},
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if results:
        return results[0].get("url")
    return None


def export_video_clip(
    access_token: str,
    base_url: str,
    device_id: str,
    start_ts: str,
    end_ts: str,
    name: str = "clip",
) -> str:
    """Full pipeline: create export, wait, return download URL."""
    job_id = create_export(access_token, base_url, device_id, start_ts, end_ts, name=name)
    poll_job(access_token, base_url, job_id)
    url = get_download_url(access_token, base_url, name)
    if not url:
        raise RuntimeError("Download not found after job completed")
    return url


# Usage
download_url = export_video_clip(
    access_token, base_url,
    device_id="10097dd2",
    start_ts="2024-03-15T07:00:00.000+00:00",
    end_ts="2024-03-15T07:30:00.000+00:00",
    name="incident_2024-03-15",
)
print(f"Download ready: {download_url}")
```

### TypeScript

```typescript
async function createExport(
  accessToken: string,
  baseUrl: string,
  deviceId: string,
  startTs: string,
  endTs: string,
  exportType: "video" | "timeLapse" | "bundle" = "video",
  name = "export",
  timeZone = "UTC"
): Promise<string> {
  const res = await fetch(`https://${baseUrl}/api/v3.0/exports`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      deviceId,
      type: exportType,
      period: { startTimestamp: startTs, endTimestamp: endTs },
      osd: { timeZone },
      info: { name, directory: "/exports" },
    }),
  });
  if (!res.ok) throw new Error(`createExport: ${res.status}`);
  const { jobId } = await res.json();
  return jobId;
}

async function pollJob(
  accessToken: string,
  baseUrl: string,
  jobId: string,
  intervalMs = 5000,
  timeoutMs = 600_000
): Promise<void> {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const res = await fetch(`https://${baseUrl}/api/v3.0/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) throw new Error(`pollJob: ${res.status}`);
    const job = await res.json();

    if (job.state === "done") return;
    if (job.state === "failed") throw new Error(`Job ${jobId} failed`);
    if (job.state === "cancelled") throw new Error(`Job ${jobId} was cancelled`);

    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
  throw new Error(`Job ${jobId} timed out`);
}

async function getDownloadUrl(
  accessToken: string,
  baseUrl: string,
  name: string
): Promise<string | null> {
  const params = new URLSearchParams({ name, include: "url" });
  const res = await fetch(`https://${baseUrl}/api/v3.0/downloads?${params}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`getDownloads: ${res.status}`);
  const data = await res.json();
  return data.results?.[0]?.url ?? null;
}

async function exportVideoClip(
  accessToken: string,
  baseUrl: string,
  deviceId: string,
  startTs: string,
  endTs: string,
  name = "clip"
): Promise<string> {
  const jobId = await createExport(accessToken, baseUrl, deviceId, startTs, endTs, "video", name);
  await pollJob(accessToken, baseUrl, jobId);
  const url = await getDownloadUrl(accessToken, baseUrl, name);
  if (!url) throw new Error("Download URL not found after job completed");
  return url;
}
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public static async Task<string> CreateExport(
    string accessToken, string baseUrl,
    string deviceId, string startTs, string endTs,
    string exportType = "video", string name = "export", string timeZone = "UTC")
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var body = JsonSerializer.Serialize(new
    {
        deviceId, type = exportType,
        period = new { startTimestamp = startTs, endTimestamp = endTs },
        osd = new { timeZone },
        info = new { name, directory = "/exports" },
    });

    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/exports",
        new StringContent(body, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();

    var doc = JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
    return doc.GetProperty("jobId").GetString()!;
}

public static async Task PollJob(
    string accessToken, string baseUrl, string jobId,
    int intervalMs = 5000, int timeoutMs = 600_000)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var deadline = DateTime.UtcNow.AddMilliseconds(timeoutMs);

    while (DateTime.UtcNow < deadline)
    {
        var response = await client.GetAsync(
            $"https://{baseUrl}/api/v3.0/jobs/{jobId}");
        response.EnsureSuccessStatusCode();

        var doc = JsonSerializer.Deserialize<JsonElement>(
            await response.Content.ReadAsStringAsync());
        var state = doc.GetProperty("state").GetString();

        if (state == "done") return;
        if (state is "failed" or "cancelled")
            throw new InvalidOperationException($"Job {jobId} ended with state: {state}");

        await Task.Delay(intervalMs);
    }

    throw new TimeoutException($"Job {jobId} did not complete within timeout");
}
```

### Rust

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};
use tokio::time::sleep;

#[derive(Deserialize)]
struct ExportResponse {
    #[serde(rename = "jobId")]
    job_id: String,
}

#[derive(Deserialize)]
struct Job {
    id: String,
    state: String,
}

pub async fn create_export(
    access_token: &str,
    base_url: &str,
    device_id: &str,
    start_ts: &str,
    end_ts: &str,
    export_type: &str,
    name: &str,
) -> Result<String, reqwest::Error> {
    let body = serde_json::json!({
        "deviceId": device_id,
        "type": export_type,
        "period": { "startTimestamp": start_ts, "endTimestamp": end_ts },
        "osd": { "timeZone": "UTC" },
        "info": { "name": name, "directory": "/exports" },
    });

    let response: ExportResponse = Client::new()
        .post(format!("https://{}/api/v3.0/exports", base_url))
        .bearer_auth(access_token)
        .json(&body)
        .send()
        .await?
        .error_for_status()?
        .json()
        .await?;

    Ok(response.job_id)
}

pub async fn poll_job(
    access_token: &str,
    base_url: &str,
    job_id: &str,
    interval: Duration,
    timeout: Duration,
) -> Result<(), Box<dyn std::error::Error>> {
    let client = Client::new();
    let deadline = Instant::now() + timeout;

    loop {
        let job: Job = client
            .get(format!("https://{}/api/v3.0/jobs/{}", base_url, job_id))
            .bearer_auth(access_token)
            .send()
            .await?
            .error_for_status()?
            .json()
            .await?;

        match job.state.as_str() {
            "done" => return Ok(()),
            "failed" | "cancelled" => {
                return Err(format!("Job {} ended with state: {}", job_id, job.state).into())
            }
            _ => {}
        }

        if Instant::now() >= deadline {
            return Err("Export job timed out".into());
        }
        sleep(interval).await;
    }
}
```

---

## Notes

- **Poll interval:** 5–10 seconds is appropriate. Do not poll faster — exports typically take 30 seconds to several minutes depending on clip length and format.
- **Expiry:** Completed downloads expire. The `expireTimestamp` on the job and download indicates when the file will be deleted. Download promptly or store the file externally.
- **Timestamps:** Use `+00:00` notation, not `Z`. The `/exports` endpoint rejects `Z`-suffixed timestamps.
- **`osd.timeZone`:** Controls the timestamp overlay burned into the video. Use the IANA timezone name of the camera's location (e.g. `America/Chicago`, `Europe/London`) so the displayed time matches local time at the site.
- **Timelapse duration:** Very long periods (days, weeks) produce large jobs. Consider the `playbackMultiplier` carefully — a 24-hour timelapse at 10× = ~2.4 hour video, at 100× = ~14 minutes.
- **Job listing:** Use `GET /jobs?type=export&state=done` to list all completed export jobs for audit or cleanup purposes.
