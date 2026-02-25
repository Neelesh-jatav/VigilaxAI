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
            parsed = {'error': 'HTTP_ERROR', 'status': e.code}
        return e.code, parsed
    except Exception as e:
        return 0, {'error': 'CONNECTION_ERROR', 'message': str(e)}

print('=' * 60)
print('FACE DETECTION API INTEGRATION TEST')
print('=' * 60)

checks = []

# Test 1: Get cameras
print('\n1. GET /api/cameras')
s, cams = req('/api/cameras')
ok = (s == 200 and isinstance(cams.get('cameras'), list))
checks.append(('cameras', ok))
print(f'   Status: {s} - {"PASS" if ok else "FAIL"}')

if cams.get('cameras'):
    idx = int(cams['cameras'][0]['index'])
    
    # Test 2: Select camera
    print(f'\n2. POST /api/select_camera (index={idx})')
    s2, sel = req('/api/select_camera', 'POST', {'index': idx})
    ok2 = (s2 == 200 and sel.get('success') is True)
    checks.append(('select', ok2))
    print(f'   Status: {s2} - {"PASS" if ok2 else "FAIL"}')
    
    # Test 3: Start camera
    print('\n3. POST /api/start')
    s3, start = req('/api/start', 'POST', {})
    ok3 = (s3 == 200 and start.get('state', {}).get('is_running') is True)
    checks.append(('start', ok3))
    print(f'   Status: {s3} - {"PASS" if ok3 else "FAIL"}')
    time.sleep(2)
    
    # Test 4: Ensure detection is ON
    print('\n4. Ensure detection is ON')
    # First check current state
    _, current_state = req('/api/detection_status')
    currently_enabled = current_state.get('enabled', False)
    print(f'   Current state: {"ON" if currently_enabled else "OFF"}')
    
    # Toggle if needed to turn ON
    if not currently_enabled:
        s4, tog1 = req('/api/toggle_detection', 'POST', {})
        ok4 = (s4 == 200 and tog1.get('enabled') is True)
        print(f'   Toggled: {s4} - {"PASS" if ok4 else "FAIL"}')
        if ok4:
            print(f'   Enabled: {tog1.get("enabled")} | Faces: {tog1.get("faces_detected")}')
    else:
        ok4 = True
        print(f'   Already ON - PASS')
    
    checks.append(('ensure_detection_on', ok4))
    
    # Test 5: Verify detection status shows ON
    print('\n5. GET /api/detection_status (verify ON)')
    time.sleep(1)
    s5, ds1 = req('/api/detection_status')
    ok5 = (s5 == 200 and ds1.get('enabled') is True)
    checks.append(('detection_status_on', ok5))
    print(f'   Status: {s5} - {"PASS" if ok5 else "FAIL"}')
    if s5 == 200:
        print(f'   Enabled: {ds1.get("enabled")} | Faces: {ds1.get("faces_detected")}')
    else:
        print(f'   Response: {ds1}')
    
    # Test 6: Check FPS
    print('\n6. GET /api/fps (3 samples)')
    fps = []
    for i in range(3):
        time.sleep(1)
        sf, jf = req('/api/fps')
        fps.append(float(jf.get('fps', 0.0)))
        print(f'   Sample {i+1}: {fps[-1]:.2f} FPS')
    ok6 = any(v > 0 for v in fps)
    checks.append(('fps_positive', ok6))
    print(f'   Result: {"PASS" if ok6 else "FAIL"}')
    
    # Test 7: Check face count is numeric
    print('\n7. GET /api/detection_status (check face count type)')
    s7, ds2 = req('/api/detection_status')
    ok7 = (s7 == 200 and isinstance(ds2.get('faces_detected'), int))
    checks.append(('face_count_numeric', ok7))
    print(f'   Status: {s7} - {"PASS" if ok7 else "FAIL"}')
    if ok7:
        fc = ds2.get('faces_detected')
        print(f'   Faces detected: {fc} (type: int)')
    
    # Test 8: Ensure detection is OFF
    print('\n8. Ensure detection is OFF')
    # First check current state
    _, current_state = req('/api/detection_status')
    currently_enabled = current_state.get('enabled', False)
    print(f'   Current state: {"ON" if currently_enabled else "OFF"}')
    
    # Toggle if needed to turn OFF
    if currently_enabled:
        s8, tog2 = req('/api/toggle_detection', 'POST', {})
        ok8 = (s8 == 200 and tog2.get('enabled') is False)
        print(f'   Toggled: {s8} - {"PASS" if ok8 else "FAIL"}')
        if ok8:
            print(f'   Enabled: {tog2.get("enabled")}')
    else:
        ok8 = True
        print(f'   Already OFF - PASS')
    
    checks.append(('ensure_detection_off', ok8))
    
    # Test 9: Verify detection status shows OFF
    print('\n9. GET /api/detection_status (verify OFF)')
    time.sleep(1)
    s9, ds3 = req('/api/detection_status')
    ok9 = (s9 == 200 and ds3.get('enabled') is False)
    checks.append(('detection_status_off', ok9))
    print(f'   Status: {s9} - {"PASS" if ok9 else "FAIL"}')
    if s9 == 200:
        print(f'   Enabled: {ds3.get("enabled")}')
    
    # Test 10: Check /api/status includes detection fields
    print('\n10. GET /api/status (check detection fields)')
    s10, st = req('/api/status')
    state = st.get('state', {})
    ok10 = (s10 == 200 and 'detection_enabled' in state and 'faces_detected' in state)
    checks.append(('status_has_detection_fields', ok10))
    print(f'   Status: {s10} - {"PASS" if ok10 else "FAIL"}')
    if ok10:
        print(f'   Detection enabled: {state.get("detection_enabled")} | Faces: {state.get("faces_detected")}')
    else:
        print(f'   State keys: {list(state.keys())}')
    
    # Test 11: Stop camera
    print('\n11. POST /api/stop')
    s11, stop = req('/api/stop', 'POST', {})
    ok11 = (s11 == 200 and stop.get('state', {}).get('is_running') is False)
    checks.append(('stop', ok11))
    print(f'   Status: {s11} - {"PASS" if ok11 else "FAIL"}')

print('\n' + '=' * 60)
print('TEST SUMMARY')
print('=' * 60)
passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print(f'Passed: {passed}/{total}')
result_text = 'ALL TESTS PASSED ✓' if passed == total else 'SOME TESTS FAILED ✗'
print(f'Result: {result_text}')
print('=' * 60)

for name, ok in checks:
    symbol = '✓' if ok else '✗'
    print(f'  {symbol} {name}')
