import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import config


def build_authorization_url() -> str:
    """Construct the authorization URL to redirect the user to."""
    params = {
        "client_id": config.CLIENT_ID,
        "response_type": "code",
        "redirect_uri": config.REDIRECT_URI,
        "scope": config.SCOPE,
    }
    return f"{config.AUTH_URL}?{urllib.parse.urlencode(params)}"


def _basic_auth_header() -> str:
    """Return the Base64-encoded Basic Auth header value."""
    credentials = f"{config.CLIENT_ID}:{config.CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def _post(url: str, headers: dict, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    headers = {
        "Authorization": _basic_auth_header(),
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.REDIRECT_URI,
        "scope": config.SCOPE,
    }
    tokens = _post(config.TOKEN_URL, headers, data)
    tokens["obtained_at"] = time.time()
    return tokens


def refresh_access_token(refresh_token: str) -> dict:
    """Use a refresh token to obtain a new access token."""
    headers = {
        "Authorization": _basic_auth_header(),
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    tokens = _post(config.TOKEN_URL, headers, data)
    tokens["obtained_at"] = time.time()
    return tokens


def save_tokens(tokens: dict) -> None:
    """Persist tokens to a local JSON file."""
    with open(config.TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    print(f"Tokens saved to {config.TOKEN_FILE}")


def load_tokens() -> dict | None:
    """Load tokens from the local JSON file. Returns None if not found."""
    try:
        with open(config.TOKEN_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def is_access_token_expired(tokens: dict, buffer_seconds: int = 300) -> bool:
    """Return True if the access token is expired (or expires within buffer_seconds)."""
    obtained_at = tokens.get("obtained_at", 0)
    expires_in = tokens.get("expires_in", 0)
    return time.time() >= obtained_at + expires_in - buffer_seconds


def get_valid_access_token() -> str:
    """
    Return a valid access token, refreshing automatically if needed.
    Raises RuntimeError if no tokens are stored.
    """
    tokens = load_tokens()
    if tokens is None:
        raise RuntimeError("No tokens found. Run the OAuth flow first (python main.py login).")

    if is_access_token_expired(tokens):
        print("Access token expired — refreshing...")
        tokens = refresh_access_token(tokens["refresh_token"])
        save_tokens(tokens)

    return tokens["access_token"]
