"""
Eagle Eye Networks OAuth 2.0 Demo
----------------------------------
Usage:
  python main.py login    — Run the full OAuth authorization flow
  python main.py cameras  — List cameras (requires prior login)
  python main.py refresh  — Manually refresh the access token
"""
import sys
import webbrowser

import auth
import api
import config


def cmd_login():
    """Open browser for authorization, capture callback, exchange for tokens."""
    if not config.CLIENT_ID or not config.CLIENT_SECRET:
        print("ERROR: EEN_CLIENT_ID and EEN_CLIENT_SECRET must be set in your .env file.")
        sys.exit(1)

    # Step 1 — Build authorization URL and open in browser
    auth_url = auth.build_authorization_url()
    print(f"\nAuthorization URL:\n{auth_url}\n")
    opened = webbrowser.open(auth_url)
    if opened:
        print("Browser opened. Complete authorization there.")
    else:
        print("Could not open browser automatically (common in WSL2).")
        print("Copy the URL above and open it in your browser, then return here.")

    # Step 2 — Start local server, block until callback arrives
    import callback_server
    code = callback_server.wait_for_callback()
    print(f"Received authorization code: {code[:10]}...")

    # Step 3 — Exchange code for tokens
    print("Exchanging authorization code for tokens...")
    tokens = auth.exchange_code_for_tokens(code)
    auth.save_tokens(tokens)

    print("\nLogin successful!")
    print(f"  Access token expires in: {tokens.get('expires_in', '?')}s")
    print(f"  Token type: {tokens.get('token_type', '?')}")


def cmd_cameras():
    """Fetch and display a list of cameras."""
    print("Fetching cameras...")
    try:
        result = api.get("/cameras", params={"pageSize": 10})
        cameras = result.get("results", [])
        if not cameras:
            print("No cameras found.")
            return
        print(f"\nFound {len(cameras)} camera(s):\n")
        for cam in cameras:
            print(f"  [{cam.get('id', '?')}] {cam.get('name', 'Unnamed')} — {cam.get('status', {}).get('connectionStatus', '?')}")
    except Exception as e:
        print(f"Error: {e}")


def cmd_stream():
    """Print the RTSP live stream URL for the configured camera."""
    import config as cfg
    camera_id = cfg.CAMERA_ID
    if not camera_id:
        print("ERROR: EEN_CAMERA_ID must be set in your .env file.")
        sys.exit(1)

    try:
        url = api.get_live_stream()
        print(f"\nLive stream URL for camera {camera_id}:\n{url}\n")
        print("Open this URL in VLC or ffplay:")
        print(f"  vlc \"{url}\"")
    except Exception as e:
        print(f"Error: {e}")


def cmd_refresh():
    """Manually refresh the access token using the stored refresh token."""
    tokens = auth.load_tokens()
    if not tokens:
        print("No tokens stored. Run 'python main.py login' first.")
        sys.exit(1)

    print("Refreshing access token...")
    new_tokens = auth.refresh_access_token(tokens["refresh_token"])
    auth.save_tokens(new_tokens)
    print("Token refreshed successfully.")
    print(f"  New access token expires in: {new_tokens.get('expires_in', '?')}s")


COMMANDS = {
    "login": cmd_login,
    "cameras": cmd_cameras,
    "stream": cmd_stream,
    "refresh": cmd_refresh,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "login"
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available commands: {', '.join(COMMANDS)}")
        sys.exit(1)
    COMMANDS[cmd]()
