# Core Function Group 7: User & Account Management

## Purpose

Create, read, update, and delete users on an account; define roles with specific permission sets; and assign those roles to users. These functions are the foundation for any admin dashboard, partner onboarding workflow, or multi-tenant integration that needs to manage who has access to what.

---

## Key Concepts

**Users** are individuals with login credentials tied to an account. A new user is created in `pending` state and receives a verification email. They become `active` after verifying.

**Roles** are named permission sets. Instead of assigning permissions directly to users, you define roles (e.g. "Operator", "Auditor", "Admin") and then assign users to roles. Multiple roles can be assigned to one user.

**Role Assignments** are the links between users and roles. Manage them in bulk via `:bulkCreate` and `:bulkDelete`.

> If your account uses the Roles API for permission management, user `permissions` fields become read-only — all permission changes must go through role assignments.

---

## Users

### List Users

```
GET https://{baseUrl}/api/v3.0/users
Authorization: Bearer {access_token}
```

**Key query parameters:**

| Parameter | Description |
|---|---|
| `email__contains` | Filter by partial email match |
| `firstName__contains` | Filter by partial first name |
| `lastName__contains` | Filter by partial last name |
| `id__in` | Comma-separated list of specific user IDs |
| `status.loginStatus__in` | Filter by status: `active`, `pending`, `inactive` |
| `permissions.administrator` | `true` to return only admins |
| `include` | Additional fields to include per user |
| `pageSize`, `pageToken` | Pagination |
| `sort` | Sort field, prefix `-` for descending |
| `q` | Free-text search |

**Response:**
```json
{
  "results": [
    {
      "id": "ca0f61ab",
      "email": "user@example.com",
      "firstName": "Jane",
      "lastName": "Smith",
      "status": { "loginStatus": "active" },
      "permissions": { "administrator": false }
    }
  ],
  "nextPageToken": "",
  "totalSize": 42
}
```

### Get Current User

```
GET https://{baseUrl}/api/v3.0/users/self
Authorization: Bearer {access_token}
```

Returns the authenticated user's profile. Useful for determining the account context after login.

### Create User

```
POST https://{baseUrl}/api/v3.0/users
Authorization: Bearer {access_token}
Content-Type: application/json
```

```json
{
  "firstName": "Jane",
  "lastName": "Smith",
  "email": "jane.smith@example.com"
}
```

- User is created in `pending` state
- EEN sends a verification email automatically
- User becomes `active` after verifying

**Response:** `201 Created` with full user object including assigned `id`.

### Update User

```
PATCH https://{baseUrl}/api/v3.0/users/{userId}
Authorization: Bearer {access_token}
Content-Type: application/json
```

Send only the fields to change. Returns `204 No Content` on success.

### Delete User

```
DELETE https://{baseUrl}/api/v3.0/users/{userId}
Authorization: Bearer {access_token}
```

Returns `204 No Content`. Removes user from account.

---

## Roles

### List Roles

```
GET https://{baseUrl}/api/v3.0/roles
Authorization: Bearer {access_token}
```

| Parameter | Description |
|---|---|
| `roleName__contains` | Filter by partial name |
| `id__in` | Specific role IDs |
| `include` | Additional fields |
| `pageSize`, `pageToken` | Pagination |

**Response:**
```json
{
  "results": [
    {
      "id": "role-abc123",
      "name": "Camera Operator",
      "permissions": ["cameras.view", "feeds.view"],
      "createTimestamp": "2024-01-15T10:00:00.000+00:00"
    }
  ]
}
```

### Create Role

```
POST https://{baseUrl}/api/v3.0/roles
Authorization: Bearer {access_token}
Content-Type: application/json
```

```json
{
  "name": "Camera Operator",
  "description": "Can view cameras and live feeds",
  "permissions": ["cameras.view", "feeds.view", "media.view"]
}
```

**Response:** `201 Created` with role object including `id`.

### Update Role

```
PATCH https://{baseUrl}/api/v3.0/roles/{roleId}
```

Send only fields to change (`name`, `description`, `permissions`). Returns `204 No Content`.

### Delete Role

```
DELETE https://{baseUrl}/api/v3.0/roles/{roleId}
```

A role can only be deleted if it has no active assignments. Returns `204 No Content`.

---

## Role Assignments

### List Assignments

```
GET https://{baseUrl}/api/v3.0/roleAssignments
Authorization: Bearer {access_token}
```

| Parameter | Description |
|---|---|
| `userId__in` | Filter by user IDs |
| `roleId__in` | Filter by role IDs |
| `roleName__contains` | Filter by role name |
| `self` | `true` to return only the current user's assignments |

### Bulk Create Assignments

```
POST https://{baseUrl}/api/v3.0/roleAssignments:bulkCreate
Authorization: Bearer {access_token}
Content-Type: application/json
```

```json
[
  { "userId": "ca0f61ab", "roleId": "role-abc123" },
  { "userId": "ca0f61ab", "roleId": "role-def456" }
]
```

### Bulk Delete Assignments

```
POST https://{baseUrl}/api/v3.0/roleAssignments:bulkDelete
Authorization: Bearer {access_token}
Content-Type: application/json
```

Same body shape as bulk create — sends the list of assignments to remove.

---

## Code Examples

### Python

```python
import requests
from typing import Iterator

def list_users(
    access_token: str,
    base_url: str,
    **filters
) -> Iterator[dict]:
    params = {"pageSize": 100, **filters}
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    while True:
        r = requests.get(f"https://{base_url}/api/v3.0/users", headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        yield from data["results"]
        if not data.get("nextPageToken"):
            break
        params["pageToken"] = data["nextPageToken"]


def create_user(
    access_token: str,
    base_url: str,
    first_name: str,
    last_name: str,
    email: str,
) -> dict:
    r = requests.post(
        f"https://{base_url}/api/v3.0/users",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"firstName": first_name, "lastName": last_name, "email": email},
    )
    r.raise_for_status()
    return r.json()  # includes assigned id


def update_user(access_token: str, base_url: str, user_id: str, **fields) -> None:
    r = requests.patch(
        f"https://{base_url}/api/v3.0/users/{user_id}",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=fields,
    )
    r.raise_for_status()


def delete_user(access_token: str, base_url: str, user_id: str) -> None:
    r = requests.delete(
        f"https://{base_url}/api/v3.0/users/{user_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    r.raise_for_status()


def create_role(
    access_token: str,
    base_url: str,
    name: str,
    permissions: list[str],
    description: str = "",
) -> dict:
    r = requests.post(
        f"https://{base_url}/api/v3.0/roles",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"name": name, "description": description, "permissions": permissions},
    )
    r.raise_for_status()
    return r.json()


def assign_role(
    access_token: str,
    base_url: str,
    assignments: list[dict],  # [{"userId": "...", "roleId": "..."}]
) -> None:
    r = requests.post(
        f"https://{base_url}/api/v3.0/roleAssignments:bulkCreate",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=assignments,
    )
    r.raise_for_status()


# Usage
user = create_user(access_token, base_url, "Jane", "Smith", "jane@example.com")
role = create_role(access_token, base_url, "Operator", ["cameras.view", "feeds.view"])
assign_role(access_token, base_url, [{"userId": user["id"], "roleId": role["id"]}])
```

### TypeScript

```typescript
interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  status: { loginStatus: string };
}

interface Role {
  id: string;
  name: string;
  permissions: string[];
}

async function listUsers(
  accessToken: string,
  baseUrl: string,
  filters: Record<string, string> = {}
): Promise<User[]> {
  const users: User[] = [];
  let pageToken: string | undefined;
  do {
    const params = new URLSearchParams({ pageSize: "100", ...filters });
    if (pageToken) params.set("pageToken", pageToken);
    const res = await fetch(`https://${baseUrl}/api/v3.0/users?${params}`, {
      headers: { Authorization: `Bearer ${accessToken}`, Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`listUsers: ${res.status}`);
    const data = await res.json();
    users.push(...data.results);
    pageToken = data.nextPageToken || undefined;
  } while (pageToken);
  return users;
}

async function createUser(
  accessToken: string,
  baseUrl: string,
  firstName: string,
  lastName: string,
  email: string
): Promise<User> {
  const res = await fetch(`https://${baseUrl}/api/v3.0/users`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ firstName, lastName, email }),
  });
  if (!res.ok) throw new Error(`createUser: ${res.status}`);
  return res.json();
}

async function createRole(
  accessToken: string,
  baseUrl: string,
  name: string,
  permissions: string[],
  description = ""
): Promise<Role> {
  const res = await fetch(`https://${baseUrl}/api/v3.0/roles`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, description, permissions }),
  });
  if (!res.ok) throw new Error(`createRole: ${res.status}`);
  return res.json();
}

async function assignRoles(
  accessToken: string,
  baseUrl: string,
  assignments: { userId: string; roleId: string }[]
): Promise<void> {
  const res = await fetch(
    `https://${baseUrl}/api/v3.0/roleAssignments:bulkCreate`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(assignments),
    }
  );
  if (!res.ok) throw new Error(`assignRoles: ${res.status}`);
}
```

### C#

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public static async Task<JsonElement> CreateUser(
    string accessToken, string baseUrl,
    string firstName, string lastName, string email)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var body = JsonSerializer.Serialize(new { firstName, lastName, email });
    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/users",
        new StringContent(body, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();
    return JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
}

public static async Task<JsonElement> CreateRole(
    string accessToken, string baseUrl,
    string name, string[] permissions, string description = "")
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var body = JsonSerializer.Serialize(new { name, description, permissions });
    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/roles",
        new StringContent(body, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();
    return JsonSerializer.Deserialize<JsonElement>(
        await response.Content.ReadAsStringAsync());
}

public static async Task AssignRoles(
    string accessToken, string baseUrl,
    (string UserId, string RoleId)[] assignments)
{
    using var client = new HttpClient();
    client.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var payload = assignments.Select(a => new { userId = a.UserId, roleId = a.RoleId });
    var body = JsonSerializer.Serialize(payload);
    var response = await client.PostAsync(
        $"https://{baseUrl}/api/v3.0/roleAssignments:bulkCreate",
        new StringContent(body, Encoding.UTF8, "application/json"));
    response.EnsureSuccessStatusCode();
}
```

### Rust

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct User {
    pub id: String,
    pub email: String,
    #[serde(rename = "firstName")]
    pub first_name: String,
    #[serde(rename = "lastName")]
    pub last_name: String,
}

#[derive(Serialize)]
struct CreateUserBody<'a> {
    #[serde(rename = "firstName")]
    first_name: &'a str,
    #[serde(rename = "lastName")]
    last_name: &'a str,
    email: &'a str,
}

pub async fn create_user(
    access_token: &str,
    base_url: &str,
    first_name: &str,
    last_name: &str,
    email: &str,
) -> Result<User, reqwest::Error> {
    Client::new()
        .post(format!("https://{}/api/v3.0/users", base_url))
        .bearer_auth(access_token)
        .json(&CreateUserBody { first_name, last_name, email })
        .send()
        .await?
        .error_for_status()?
        .json::<User>()
        .await
}

#[derive(Serialize)]
struct RoleAssignment<'a> {
    #[serde(rename = "userId")]
    user_id: &'a str,
    #[serde(rename = "roleId")]
    role_id: &'a str,
}

pub async fn assign_roles(
    access_token: &str,
    base_url: &str,
    assignments: Vec<(&str, &str)>,
) -> Result<(), reqwest::Error> {
    let body: Vec<_> = assignments
        .iter()
        .map(|(u, r)| RoleAssignment { user_id: u, role_id: r })
        .collect();

    Client::new()
        .post(format!("https://{}/api/v3.0/roleAssignments:bulkCreate", base_url))
        .bearer_auth(access_token)
        .json(&body)
        .send()
        .await?
        .error_for_status()?;
    Ok(())
}
```

---

## Notes

- New users start in `pending` state until they verify their email. Automations or integrations should not assume `active` status immediately after `POST /users`.
- A role cannot be deleted while it has active assignments. Call `:bulkDelete` on assignments first.
- `GET /users/self` is the fastest way to resolve the authenticated user's account context — use it on startup rather than listing all users.
- The `:bulkCreate` and `:bulkDelete` endpoints for role assignments accept arrays — use them to avoid making N individual calls when provisioning multiple users.
