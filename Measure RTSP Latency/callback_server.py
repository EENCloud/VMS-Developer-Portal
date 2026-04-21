"""
A minimal local HTTP server that captures the OAuth callback code.
Starts on 127.0.0.1:CALLBACK_PORT, waits for one request, then shuts down.
"""
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import config


_auth_code: str | None = None
_server_error: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code, _server_error

        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if "error" in params:
            _server_error = params["error"]
            self._respond(400, f"Authorization failed: {params['error']}")
        elif "code" in params:
            _auth_code = params["code"]
            self._respond(200, "Authorization successful! You can close this tab.")
        else:
            _server_error = "No code received"
            self._respond(400, "Unexpected callback — no code parameter.")

        # Signal the server to stop after this request
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _respond(self, status: int, message: str):
        body = message.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Suppress default request logging
        pass


def wait_for_callback() -> str:
    """
    Start the local server and block until the OAuth callback arrives.
    Returns the authorization code.
    Raises RuntimeError on error or if no code is received.
    """
    server = HTTPServer(("127.0.0.1", config.CALLBACK_PORT), _CallbackHandler)
    print(f"Waiting for OAuth callback on http://127.0.0.1:{config.CALLBACK_PORT}/callback ...")
    server.serve_forever()  # Blocks until _CallbackHandler calls shutdown()

    if _server_error:
        raise RuntimeError(f"OAuth error from server: {_server_error}")
    if not _auth_code:
        raise RuntimeError("No authorization code received.")

    return _auth_code
