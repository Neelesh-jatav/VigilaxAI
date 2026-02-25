"""Test script to verify drone detection integration"""
import json
import time
import urllib.request
import urllib.error

base = 'http://127.0.0.1:5000'

def req(path, method='GET', payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    r = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=12) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else '{}'
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {'raw': body}
        return e.code, parsed

print('=== DRONE DETECTION TEST ===\n')
checks = []

# Get available cameras
s, cams = req('/api/cameras')
checks.append(('cameras', s == 200 and isinstance(cams.get('cameras'), list), cams))
print(f'1. Get cameras: {"PASS" if checks[-1][1] else "FAIL"}')

if cams.get('cameras'):
    idx = int(cams['cameras'][0]['index'])
    
    # Select camera
    s, sel = req('/api/select_camera', 'POST', {'index': idx})
    checks.append(('select', s == 200 and sel.get('success') is True, sel))
    print(f'2. Select camera {idx}: {"PASS" if checks[-1][1] else "FAIL"}')
    
    # Start camera
    s, start = req('/api/start', 'POST', {})
    checks.append(('start', s == 200 and start.get('state', {}).get('is_running') is True, start))
    print(f'3. Start camera: {"PASS" if checks[-1][1] else "FAIL"}')
    time.sleep(2)
    
    # Check AI status before enabling
    s, ai0 = req('/api/ai_status')
    checks.append(('ai_status_initial', s == 200 and ai0.get('drone_enabled') is False, ai0))
    print(f'4. AI status (initial): {"PASS" if checks[-1][1] else "FAIL"}')
    print(f'   - Face: {ai0.get("face_enabled")} ({ai0.get("faces_detected")} detected)')
    print(f'   - Drone: {ai0.get("drone_enabled")} ({ai0.get("drones_detected")} detected)')
    
    # Enable drone detection
    s, drone_on = req('/api/toggle_drone', 'POST', {})
    checks.append(('toggle_drone_on', s == 200 and drone_on.get('enabled') is True, drone_on))
    print(f'5. Enable drone detection: {"PASS" if checks[-1][1] else "FAIL"}')
    print(f'   Response: {json.dumps(drone_on)}')
    time.sleep(3)
    
    # Check AI status after enabling
    s, ai1 = req('/api/ai_status')
    checks.append(('ai_status_drone_on', s == 200 and ai1.get('drone_enabled') is True, ai1))
    print(f'6. AI status (drone ON): {"PASS" if checks[-1][1] else "FAIL"}')
    print(f'   - Face: {ai1.get("face_enabled")} ({ai1.get("faces_detected")} detected)')
    print(f'   - Drone: {ai1.get("drone_enabled")} ({ai1.get("drones_detected")} detected)')
    print(f'   - Both active: {ai1.get("both_active")}')
    
    # Enable face detection too
    s, face_on = req('/api/toggle_face', 'POST', {})
    checks.append(('toggle_face_on', s == 200 and face_on.get('enabled') is True, face_on))
    print(f'7. Enable face detection: {"PASS" if checks[-1][1] else "FAIL"}')
    time.sleep(2)
    
    # Check both active
    s, ai2 = req('/api/ai_status')
    checks.append(('ai_status_both_on', s == 200 and ai2.get('both_active') is True, ai2))
    print(f'8. AI status (both ON): {"PASS" if checks[-1][1] else "FAIL"}')
    print(f'   - Face: {ai2.get("face_enabled")} ({ai2.get("faces_detected")} detected)')
    print(f'   - Drone: {ai2.get("drone_enabled")} ({ai2.get("drones_detected")} detected)')
    print(f'   - Both active: {ai2.get("both_active")}')
    
    # Disable drone detection
    s, drone_off = req('/api/toggle_drone', 'POST', {})
    checks.append(('toggle_drone_off', s == 200 and drone_off.get('enabled') is False, drone_off))
    print(f'9. Disable drone detection: {"PASS" if checks[-1][1] else "FAIL"}')
    time.sleep(1)
    
    # Check AI status after disabling drone
    s, ai3 = req('/api/ai_status')
    checks.append(('ai_status_drone_off', s == 200 and ai3.get('drone_enabled') is False and ai3.get('both_active') is False, ai3))
    print(f'10. AI status (drone OFF): {"PASS" if checks[-1][1] else "FAIL"}')
    print(f'   - Face: {ai3.get("face_enabled")} ({ai3.get("faces_detected")} detected)')
    print(f'   - Drone: {ai3.get("drone_enabled")} ({ai3.get("drones_detected")} detected)')
    
    # Stop camera
    s, stop = req('/api/stop', 'POST', {})
    checks.append(('stop', s == 200 and stop.get('state', {}).get('is_running') is False, stop))
    print(f'11. Stop camera: {"PASS" if checks[-1][1] else "FAIL"}')

all_ok = all(item[1] for item in checks)
print()
print('=== TEST RESULT ===')
passed = sum(1 for c in checks if c[1])
total = len(checks)
print(f'Result: {"PASS" if all_ok else "FAIL"} ({passed}/{total} checks passed)')