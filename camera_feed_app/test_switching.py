"""Test camera switching between multiple cameras"""
import json
import time
import urllib.request

base = 'http://127.0.0.1:5000'

def req(path, method='GET', payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    r = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(r, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

print('=== MULTI-CAMERA SWITCHING TEST ===\n')

# Get cameras
print('1. Fetching available cameras...')
s, cams = req('/api/cameras')
cameras = cams.get('cameras', [])
print(f'   ✓ Found {len(cameras)} cameras')

if len(cameras) < 2:
    print(f'\n   Only 1 camera available. Switching test requires 2+ cameras.')
    exit(0)

print(f'\n2. Testing camera switching...')
results = []

for i, cam in enumerate(cameras):
    print(f'\n   Test {i+1}: Switching to {cam["name"]} (Index {cam["index"]})')
    
    # Select camera
    s, sel = req('/api/select_camera', 'POST', {'index': cam['index']})
    if s == 200 and sel.get('success'):
        print(f'     ✓ Selected: {sel.get("selected_camera")}')
    else:
        print(f'     ✗ Failed to select camera')
        results.append(False)
        continue
    
    # Start camera
    s, start = req('/api/start', 'POST', {})
    if s == 200 and start.get('state', {}).get('is_running'):
        print(f'     ✓ Camera started')
        print(f'     ✓ Active: {start.get("state", {}).get("active_camera_name")}')
    else:
        print(f'     ✗ Failed to start camera')
        results.append(False)
        continue
    
    # Check status
    time.sleep(1)
    s, status = req('/api/status')
    if s == 200:
        state = status.get('state', {})
        print(f'     ✓ Running: {state.get("is_running")}')
        print(f'     ✓ Camera: {state.get("active_camera_name")}')
        print(f'     ✓ Index: {state.get("camera_index")}')
    
    # Check FPS
    s, fps_data = req('/api/fps')
    if s == 200:
        fps = fps_data.get('fps', 0)
        print(f'     ✓ FPS: {fps:.2f}')
    
    # Stop before switching to next
    s, stop = req('/api/stop', 'POST', {})
    if s == 200:
        print(f'     ✓ Camera stopped')
        results.append(True)
    else:
        print(f'     ✗ Failed to stop camera')
        results.append(False)
    
    time.sleep(0.5)

print(f'\n=== TEST RESULT ===')
print(f'Cameras tested: {len(results)}')
print(f'Successful: {sum(results)}')
print(f'Failed: {len(results) - sum(results)}')
print(f'\nResult: {"✓ PASS - Multi-camera switching works!" if all(results) else "✗ FAIL - Some cameras failed"}')
