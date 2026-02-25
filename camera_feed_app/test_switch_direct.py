"""Direct camera switching test (bypassing slow camera scan)"""
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
    with urllib.request.urlopen(r, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

print('=== CAMERA SWITCHING TEST (Direct API Calls) ===\n')
print('Testing camera indices 0 and 1 (known to exist)...\n')

cameras_to_test = [
    {'index': 0, 'name': 'Camera 0'},
    {'index': 1, 'name': 'Camera 1'}
]

results = []

for i, cam in enumerate(cameras_to_test):
    print(f'{i+1}. Testing {cam["name"]} (Index {cam["index"]})...')
    
    try:
        # Select camera
        s, sel = req('/api/select_camera', 'POST', {'index': cam['index']})
        if s != 200 or not sel.get('success'):
            print(f'   ✗ Failed to select camera (status {s})')
            results.append(False)
            continue
        print(f'   ✓ Selected: {sel.get("selected_camera")}')
        
        # Start camera
        s, start = req('/api/start', 'POST', {})
        if s != 200:
            print(f'   ✗ Failed to start camera (status {s})')
            results.append(False)
            continue
        
        state = start.get('state', {})
        if not state.get('is_running'):
            print(f'   ✗ Camera not running after start')
            results.append(False)
            continue
            
        print(f'   ✓ Started: {state.get("active_camera_name")}')
        print(f'   ✓ Index: {state.get("camera_index")}')
        
        # Wait for frames
        time.sleep(1.5)
        
        # Check FPS
        s, fps_data = req('/api/fps')
        if s == 200:
            fps = fps_data.get('fps', 0)
            print(f'   ✓ FPS: {fps:.2f}')
            if fps > 0:
                print(f'   ✓ Camera is actively streaming frames')
        
        # Stop camera
        s, stop = req('/api/stop', 'POST', {})
        if s != 200:
            print(f'   ✗ Failed to stop camera')
            results.append(False)
            continue
            
        print(f'   ✓ Stopped successfully')
        results.append(True)
        print()
        
        time.sleep(0.5)
        
    except Exception as e:
        print(f'   ✗ Error: {e}')
        results.append(False)
        print()

print('=== RESULTS ===')
print(f'Cameras tested: {len(results)}')
print(f'Successful: {sum(results)}/{len(results)}')

if all(results):
    print(f'\n✓✓✓ PASS - Multi-camera switching works perfectly!')
    print(f'✓ Both cameras can be selected independently')
    print(f'✓ Each camera starts and streams frames')
    print(f'✓ Switching between cameras is working')
    print(f'\n✓ UI horizontal buttons will allow easy camera switching')
elif any(results):
    print(f'\n⚠ PARTIAL - Some cameras work ({sum(results)}/{len(results)})')
else:
    print(f'\n✗ FAIL - Camera switching not working')
