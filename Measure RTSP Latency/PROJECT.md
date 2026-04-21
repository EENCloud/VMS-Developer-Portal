# What This Project Does

This project is a minimal Python client for the **Eagle Eye Networks (EEN) API v3**. It demonstrates how to authenticate with Eagle Eye's cloud platform, interact with its REST API, and pull live video streams from IP cameras.

---

## Overview

Eagle Eye Networks is a cloud-based video surveillance platform. Cameras connect to EEN's cloud, which exposes an API for listing devices, retrieving live streams, and more. This project covers three areas:

1. **OAuth 2.0 login** — authenticates a user account and stores access tokens locally
2. **REST API calls** — lists cameras and resolves account-specific API endpoints
3. **Live RTSP streaming** — decodes and measures latency of live camera video via GStreamer

---

## Files and What They Do

| File | Purpose |
|---|---|
| `main.py` | CLI entry point — `login`, `cameras`, `stream`, `refresh` commands |
| `auth.py` | OAuth 2.0 token exchange, refresh, and local storage |
| `api.py` | Thin HTTP client wrapping EEN API v3 endpoints |
| `config.py` | Loads credentials from `.env` and defines constants |
| `callback_server.py` | Temporary local HTTP server that captures the OAuth redirect |
| `frames_gst.py` | GStreamer-based RTSP frame decoder with timing support |
| `measure_latency.py` | Measures true camera-to-receipt latency using RTCP NTP timestamps |

---

## How Authentication Works

Eagle Eye uses the **OAuth 2.0 Authorization Code** flow:

1. `main.py login` builds an authorization URL and opens it in the browser
2. The user logs in on Eagle Eye's website and approves the app
3. Eagle Eye redirects to `http://127.0.0.1:3333/callback?code=...`
4. `callback_server.py` captures that redirect on a local HTTP server
5. `auth.py` exchanges the code for an **access token** and **refresh token**, saved to `tokens.json`
6. On subsequent runs, `auth.py` automatically refreshes the access token when it expires (within a 5-minute buffer)

---

## How API Calls Work

Eagle Eye's API uses **account-specific base URLs** (e.g. `https://api.c012.eagleeyenetworks.com/api/v3.0`). `api.py` resolves this on the first call by hitting the global `/clientSettings` endpoint, then caches it for the session.

All requests attach a `Bearer` token from `tokens.json`. If the token is expired, `auth.py` refreshes it transparently before the request goes out.

---

## How Video Streaming Works

`frames_gst.py` builds a **GStreamer pipeline** that connects to an RTSP URL returned by the API:

```
rtspsrc → decodebin → videoconvert → appsink
```

It exposes three generators:

- `iter_frames(url)` — yields raw BGR frames as NumPy arrays
- `iter_frames_timed(url)` — yields frames with PTS-based latency estimates
- `iter_frames_ntp(url)` — yields frames with true NTP wall-clock capture times from RTCP Sender Reports

`cv2.imshow` / `cv2.imwrite` are used only for display and saving snapshots — all decoding goes through GStreamer.

---

## Latency Measurement

`measure_latency.py` uses `iter_frames_ntp` to compute true **camera-capture-to-local-receipt** latency:

- Waits for the first **RTCP Sender Report** (carries the camera's NTP clock)
- Compares the NTP capture timestamp on each frame against `time.time()` at receipt
- Prints per-frame latency in milliseconds and a min/max/avg summary after 10 frames
- Saves a snapshot of the last frame to `latency_snapshot.jpg`

---

## Data Flow Diagram

```
  Browser
     |
     | (1) User logs in at Eagle Eye
     v
Eagle Eye Auth Server
     |
     | (2) Redirects to localhost:3333/callback?code=...
     v
callback_server.py  ──► auth.py  ──► tokens.json
                                          |
                             (3) Bearer token on every request
                                          |
                                          v
                                   api.py ──► EEN REST API v3
                                                    |
                                        (4) Returns RTSP URL
                                                    |
                                                    v
                                            frames_gst.py
                                         (GStreamer pipeline)
                                                    |
                                        (5) Decoded BGR frames
                                                    |
                                                    v
                                         measure_latency.py
                                          cv2.imshow / imwrite
```
