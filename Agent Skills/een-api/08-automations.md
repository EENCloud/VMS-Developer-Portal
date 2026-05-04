# Core Function Group 8: Automations

## Purpose

Define what the platform does when events occur. Three resources work together as a pipeline: **Alert Actions** declare what to do (send a webhook, SMS, email, Slack message, etc.), **Event Alert Condition Rules** declare when to trigger (which cameras, which event types, what schedule, what priority), and **Alert Action Rules** link the two together.

Without automations, the platform is observational. With them, it reacts.

---

## The Three-Resource Pipeline

```
[Event fires on camera]
        │
        ▼
EventAlertConditionRule ──► "If motion is detected on cameras in Building A
                              between 22:00–06:00 at priority HIGH..."
        │
        ▼
AlertActionRule ────────────► "...then trigger these alert actions:"
        │
        ├──► AlertAction: send Slack message to #security-alerts
        ├──► AlertAction: POST webhook to incident management system
        └──► AlertAction: send SMS to on-call phone
```

Build order: **AlertAction first → EventAlertConditionRule second → AlertActionRule last.**

---

## Resource 1: Alert Actions — What To Do

Alert Actions define the notification or integration endpoint that fires when an alert is triggered. Create them independently so they can be reused across multiple action rules.

### Create Alert Action

```
POST https://{baseUrl}/api/v3.0/alertActions
Authorization: Bearer {access_token}
Content-Type: application/json
```

The `type` field discriminates the action schema. Supported types:

| `type` | Description |
|---|---|
| `notification` | Push notification and/or email to EEN users |
| `sms` | SMS to EEN users |
| `smtp` | Email via custom SMTP server |
| `webhook` | HTTP POST to an external URL |
| `slack` | Message to a Slack channel |
| `zulipPrivate` | Zulip private message |
| `zulipStream` | Zulip stream message |
| `brivo` | Brivo access control integration |
| `zendesk` | Create Zendesk ticket |
| `zapier` | Trigger Zapier zap |
| `outputPort` | Trigger camera I/O output port |
| `playSpeakerAudioClip` | Play audio on a connected speaker |

### Request Body Examples

**Webhook action:**
```json
{
  "type": "webhook",
  "name": "Incident Management Webhook",
  "enabled": true,
  "settings": {
    "url": "https://your-system.com/incidents",
    "auth_token": "your-webhook-secret"
  }
}
```

**EEN notification (push + email):**
```json
{
  "type": "notification",
  "name": "Security Team Alert",
  "enabled": true,
  "settings": {
    "users": [
      { "id": "ca0f61ab", "push": true, "email": true }
    ],
    "rearmSeconds": 300,
    "maxPerHour": 12
  }
}
```

**Slack:**
```json
{
  "type": "slack",
  "name": "Security Slack Channel",
  "enabled": true,
  "settings": {
    "apiToken": "xoxb-your-slack-token",
    "channel": "#security-alerts"
  }
}
```

**SMS:**
```json
{
  "type": "sms",
  "name": "On-Call SMS",
  "enabled": true,
  "settings": {
    "users": [{ "id": "ca0f61ab" }]
  }
}
```

### Response

```json
{
  "id": "action-abc123",
  "type": "webhook",
  "name": "Incident Management Webhook",
  "enabled": true,
  "settings": { ... },
  "createTimestamp": "2024-03-15T10:00:00.000+00:00"
}
```

Store the `id` — it is used when creating Alert Action Rules.

### Manage Alert Actions

```
GET    /alertActions              List all actions (paginated)
GET    /alertActions/{id}         Get one action
PATCH  /alertActions/{id}         Update (name, enabled, settings)
DELETE /alertActions/{id}         Delete action
```

---

## Resource 2: Event Alert Condition Rules — When To Trigger

Defines the conditions under which an alert is generated.

### Create Event Alert Condition Rule

```
POST https://{baseUrl}/api/v3.0/eventAlertConditionRules
Authorization: Bearer {access_token}
Content-Type: application/json
```

```json
{
  "name": "After-Hours Motion — Building A",
  "enabled": true,
  "priority": 2,
  "eventFilter": {
    "resourceType": "camera",
    "resourceIds": ["10097dd2", "100d4c41"],
    "types": ["een.motionDetectionEvent.v1"]
  },
  "schedule": {
    "timeZone": "America/Chicago",
    "windows": [
      { "daysOfWeek": [1,2,3,4,5], "startTime": "22:00", "endTime": "06:00" },
      { "daysOfWeek": [6,7], "startTime": "00:00", "endTime": "23:59" }
    ]
  }
}
```

### Fields

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Human-readable label |
| `enabled` | Yes | `false` to create disabled. Default: `false`. |
| `priority` | Yes | Integer. Higher = more urgent. Used by notification systems to triage. |
| `eventFilter.resourceType` | No | `camera`, `bridge`, etc. |
| `eventFilter.resourceIds` | No | Specific device IDs. Omit for all devices. |
| `eventFilter.types` | No | Event type strings. Omit for all event types. |
| `schedule` | No | Time windows when the rule is active. Omit for always-active. |

### Response

```json
{
  "id": "rule-xyz789",
  "name": "After-Hours Motion — Building A",
  "enabled": true,
  "priority": 2,
  "outputAlertTypes": ["een.motionDetectionEvent.v1"],
  "createTimestamp": "2024-03-15T10:00:00.000+00:00"
}
```

The `outputAlertTypes` field (read-only) lists the alert types this rule will produce. Store the `id`.

### Filter Condition Rules

```
GET /eventAlertConditionRules?actor__in=camera:10097dd2
GET /eventAlertConditionRules?enabled=true
GET /eventAlertConditionRules?eventFilter.eventTypes__contains=een.motionDetectionEvent.v1
GET /eventAlertConditionRules?priority__gte=2&priority__lte=5
```

### Manage Condition Rules

```
GET    /eventAlertConditionRules          List (paginated, filterable)
GET    /eventAlertConditionRules/{id}     Get one rule
PATCH  /eventAlertConditionRules/{id}     Update
DELETE /eventAlertConditionRules/{id}     Delete
```

---

## Resource 3: Alert Action Rules — Linking Condition to Action

Connects one or more Alert Actions to a triggering condition.

### Create Alert Action Rule

```
POST https://{baseUrl}/api/v3.0/alertActionRules
Authorization: Bearer {access_token}
Content-Type: application/json
```

```json
{
  "name": "After-Hours Motion Response",
  "alertActionIds": ["action-abc123", "action-def456"]
}
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Human-readable label |
| `alertActionIds` | Yes | Array of Alert Action IDs to fire when this rule triggers |

### Response

```json
{
  "id": "actionrule-111",
  "name": "After-Hours Motion Response",
  "alertActionIds": ["action-abc123", "action-def456"],
  "createTimestamp": "2024-03-15T10:00:00.000+00:00"
}
```

### Manage Action Rules

```
GET    /alertActionRules          List
GET    /alertActionRules/{id}     Get one
PATCH  /alertActionRules/{id}     Update (name, alertActionIds)
DELETE /alertActionRules/{id}     Delete
```

---

## Code Examples

### Python

```python
import requests

def create_alert_action(
    access_token: str,
    base_url: str,
    action_type: str,
    name: str,
    settings: dict,
    enabled: bool = True,
) -> dict:
    r = requests.post(
        f"https://{base_url}/api/v3.0/alertActions",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"type": action_type, "name": name, "enabled": enabled, "settings": settings},
    )
    r.raise_for_status()
    return r.json()


def create_condition_rule(
    access_token: str,
    base_url: str,
    name: str,
    priority: int,
    camera_ids: list[str] | None = None,
    event_types: list[str] | None = None,
    enabled: bool = True,
) -> dict:
    body: dict = {"name": name, "enabled": enabled, "priority": priority}
    if camera_ids or event_types:
        body["eventFilter"] = {}
        if camera_ids:
            body["eventFilter"]["resourceType"] = "camera"
            body["eventFilter"]["resourceIds"] = camera_ids
        if event_types:
            body["eventFilter"]["types"] = event_types

    r = requests.post(
        f"https://{base_url}/api/v3.0/eventAlertConditionRules",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=body,
    )
    r.raise_for_status()
    return r.json()


def create_action_rule(
    access_token: str,
    base_url: str,
    name: str,
    alert_action_ids: list[str],
) -> dict:
    r = requests.post(
        f"https://{base_url}/api/v3.0/alertActionRules",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"name": name, "alertActionIds": alert_action_ids},
    )
    r.raise_for_status()
    return r.json()


# Full setup example
webhook_action = create_alert_action(
    access_token, base_url,
    action_type="webhook",
    name="Incident Webhook",
    settings={"url": "https://your-system.com/incidents", "auth_token": "secret"},
)
condition_rule = create_condition_rule(
    access_token, base_url,
    name="After-Hours Motion",
    priority=2,
    camera_ids=["10097dd2"],
    event_types=["een.motionDetectionEvent.v1"],
)
action_rule = create_action_rule(
    access_token, base_url,
    name="After-Hours Motion Response",
    alert_action_ids=[webhook_action["id"]],
)
```

### TypeScript

```typescript
interface AlertAction {
  id: string;
  type: string;
  name: string;
  enabled: boolean;
}

interface ConditionRule {
  id: string;
  name: string;
  priority: number;
  outputAlertTypes: string[];
}

async function createAlertAction(
  accessToken: string,
  baseUrl: string,
  type: string,
  name: string,
  settings: Record<string, unknown>,
  enabled = true
): Promise<AlertAction> {
  const res = await fetch(`https://${baseUrl}/api/v3.0/alertActions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ type, name, enabled, settings }),
  });
  if (!res.ok) throw new Error(`createAlertAction: ${res.status}`);
  return res.json();
}

async function createConditionRule(
  accessToken: string,
  baseUrl: string,
  name: string,
  priority: number,
  cameraIds?: string[],
  eventTypes?: string[],
  enabled = true
): Promise<ConditionRule> {
  const body: Record<string, unknown> = { name, enabled, priority };
  if (cameraIds || eventTypes) {
    body.eventFilter = {
      ...(cameraIds && { resourceType: "camera", resourceIds: cameraIds }),
      ...(eventTypes && { types: eventTypes }),
    };
  }

  const res = await fetch(
    `https://${baseUrl}/api/v3.0/eventAlertConditionRules`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) throw new Error(`createConditionRule: ${res.status}`);
  return res.json();
}

async function createActionRule(
  accessToken: string,
  baseUrl: string,
  name: string,
  alertActionIds: string[]
): Promise<{ id: string }> {
  const res = await fetch(`https://${baseUrl}/api/v3.0/alertActionRules`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, alertActionIds }),
  });
  if (!res.ok) throw new Error(`createActionRule: ${res.status}`);
  return res.json();
}
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public static async Task<string> CreateAlertAction(
    string accessToken, string baseUrl,
    string type, string name, object settings, bool enabled = true)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var body = JsonSerializer.Serialize(new { type, name, enabled, settings });
    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/alertActions",
        new StringContent(body, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();

    var doc = JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
    return doc.GetProperty("id").GetString()!;
}

public static async Task<string> CreateConditionRule(
    string accessToken, string baseUrl,
    string name, int priority,
    string[]? cameraIds = null,
    string[]? eventTypes = null,
    bool enabled = true)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    object? eventFilter = (cameraIds != null || eventTypes != null)
        ? new
          {
              resourceType = cameraIds != null ? "camera" : null,
              resourceIds = cameraIds,
              types = eventTypes,
          }
        : null;

    var body = JsonSerializer.Serialize(new { name, enabled, priority, eventFilter });
    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/eventAlertConditionRules",
        new StringContent(body, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();

    var doc = JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
    return doc.GetProperty("id").GetString()!;
}

public static async Task<string> CreateActionRule(
    string accessToken, string baseUrl,
    string name, string[] alertActionIds)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var body = JsonSerializer.Serialize(new { name, alertActionIds });
    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/alertActionRules",
        new StringContent(body, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();

    var doc = JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
    return doc.GetProperty("id").GetString()!;
}
```

### Rust

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Serialize)]
struct CreateActionBody<'a> {
    #[serde(rename = "type")]
    action_type: &'a str,
    name: &'a str,
    enabled: bool,
    settings: Value,
}

#[derive(Deserialize)]
pub struct CreatedResource {
    pub id: String,
}

pub async fn create_alert_action(
    access_token: &str,
    base_url: &str,
    action_type: &str,
    name: &str,
    settings: Value,
    enabled: bool,
) -> Result<CreatedResource, reqwest::Error> {
    Client::new()
        .post(format!("https://{}/api/v3.0/alertActions", base_url))
        .bearer_auth(access_token)
        .json(&CreateActionBody { action_type, name, enabled, settings })
        .send()
        .await?
        .error_for_status()?
        .json::<CreatedResource>()
        .await
}

#[derive(Serialize)]
struct CreateActionRuleBody<'a> {
    name: &'a str,
    #[serde(rename = "alertActionIds")]
    alert_action_ids: &'a [String],
}

pub async fn create_action_rule(
    access_token: &str,
    base_url: &str,
    name: &str,
    alert_action_ids: &[String],
) -> Result<CreatedResource, reqwest::Error> {
    Client::new()
        .post(format!("https://{}/api/v3.0/alertActionRules", base_url))
        .bearer_auth(access_token)
        .json(&CreateActionRuleBody { name, alert_action_ids })
        .send()
        .await?
        .error_for_status()?
        .json::<CreatedResource>()
        .await
}
```

---

## Notes

- **Build order matters:** Create Alert Actions first (you need their IDs), then Condition Rules (you need their output alert types), then Action Rules (which link both).
- **`enabled: false`** is the default for condition rules. Always explicitly set `enabled: true` when you want the rule to be active immediately, or activate it with a PATCH after verifying configuration.
- **`priority`** is an integer with no fixed scale — define conventions in your integration (e.g. 1=low, 5=critical) and document them. Higher values surface as more urgent in the EEN notification UI.
- **Alert Actions are reusable.** A single webhook action can be referenced by multiple action rules across different condition rules.
- **`rearmSeconds`** on notification actions prevents alert fatigue by suppressing repeat notifications for the same condition within the rearm window. Set appropriately for the event frequency.
- **Disabling vs deleting:** Use `PATCH .../enabled=false` to temporarily pause a rule. Use DELETE only when the rule is no longer needed — deletion is permanent.
