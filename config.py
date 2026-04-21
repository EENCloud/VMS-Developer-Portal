import os


def _load_env(path: str = ".env") -> None:
    """Load key=value pairs from a .env file into os.environ (does not overwrite)."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


_load_env()

# OAuth endpoints
AUTH_URL = "https://auth.eagleeyenetworks.com/oauth2/authorize"
TOKEN_URL = "https://auth.eagleeyenetworks.com/oauth2/token"

# Your app credentials — set these in .env
CLIENT_ID = os.getenv("EEN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("EEN_CLIENT_SECRET", "")

# Redirect URI — must be registered in your app settings
REDIRECT_URI = "http://127.0.0.1:3333/callback"

# Scopes — vms.all grants full VMS access
SCOPE = "vms.all"

# Local callback server port
CALLBACK_PORT = 3333

# Token storage file
TOKEN_FILE = "tokens.json"

# Camera ID to use for stream requests
CAMERA_ID = os.getenv("EEN_CAMERA_ID", "")
