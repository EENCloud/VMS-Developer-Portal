"""
Measures true camera-to-receipt latency using RTCP Sender Report NTP timestamps.
Run from WSL2 with the venv active:
    python measure_latency.py
"""
import time
import api
import frames_gst
import cv2

SAMPLE_FRAMES = 10

print("Fetching RTSP URL...")
rtsp_url = api.get_live_stream()
print("Stream ready. Waiting for RTCP Sender Report (NTP timestamps)...\n")

latencies = []
last_frame = None

for frame, capture_unix, received_at in frames_gst.iter_frames_ntp(rtsp_url):
    if capture_unix is None:
        print("  (waiting for RTCP SR...)")
        continue

    latency_ms = (received_at - capture_unix) * 1000
    latencies.append(latency_ms)
    last_frame = frame
    print(f"  Frame {len(latencies):3d} | capture {capture_unix:.3f} | latency {latency_ms:.1f} ms")

    if len(latencies) >= SAMPLE_FRAMES:
        break

if not latencies:
    print("\nNo RTCP Sender Reports received — cannot compute latency.")
else:
    if last_frame is not None:
        cv2.imwrite("latency_snapshot.jpg", last_frame)

    print(f"\n--- Summary ({len(latencies)} frames) ---")
    print(f"  Min latency : {min(latencies):.1f} ms")
    print(f"  Max latency : {max(latencies):.1f} ms")
    print(f"  Avg latency : {sum(latencies)/len(latencies):.1f} ms")
    if last_frame is not None:
        print("  Snapshot    : latency_snapshot.jpg")
