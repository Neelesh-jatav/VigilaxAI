# Audio Drone Detection Integration - Test Commands

## Quick Verification Tests

Run these commands to verify the integration is working:

### 1. Check Service Status Endpoint
```bash
curl http://localhost:5000/api/audio_drone/status
```

**Expected Response (HTTP 200):**
```json
{
  "available": true,
  "last_result": null,
  "success": true
}
```

### 2. Try Audio File Upload (Drone Detection)
```bash
curl -X POST -F "file=@audio1/backend/uploads/test_drone.wav" \
  http://localhost:5000/api/audio_drone/predict
```

**Expected Response (HTTP 200):**
```json
{
  "available": true,
  "confidence": 1.0,
  "detected": true,
  "prediction": "Drone Detected",
  "raw_score": 1.0,
  "success": true
}
```

### 3. Check Combined AI Status
Make a GET request to see all AI systems including audio:
```bash
curl http://localhost:5000/api/ai_status | jq '.audio_drone_available'
```

**Expected:**
- `audio_drone_available: true`
- `audio_drone_last_result: {...}` (if prediction was made)

### 4. Load Main Page and Check UI
```bash
curl http://localhost:5000/ | grep -i audio
```

Should see references to:
- `audio-panel`
- `analyzeAudioBtn`
- `audioFileInput`
- `audioResult`

### 5. Voice Command Test
In browser console, simulate voice command:
```javascript
// Simulate recognized speech
const event = new Event('speechrecognition');
event.results = [{ transcript: 'analyze audio' }];
if (window.recognition) {
  window.recognition.onresult(event);
}
```

---

## Python Testing

### Test 1: Health Check All Endpoints
```python
import requests
import json

endpoints = [
    ('GET', '/api/audio_drone/status'),
    ('GET', '/api/ai_status'),
    ('GET', '/')
]

base_url = 'http://localhost:5000'
for method, path in endpoints:
    if method == 'GET':
        r = requests.get(base_url + path)
        status = '✅' if r.status_code == 200 else '❌'
        print(f"{status} {method} {path} → {r.status_code}")
```

**Expected Output:**
```
✅ GET /api/audio_drone/status → 200
✅ GET /api/ai_status → 200
✅ GET / → 200
```

### Test 2: Audio File Upload
```python
import requests

with open('audio1/backend/uploads/test_drone.wav', 'rb') as f:
    r = requests.post(
        'http://localhost:5000/api/audio_drone/predict',
        files={'file': f}
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
```

**Expected Output:**
```
Status: 200
Response: {'success': True, 'detected': True, 'confidence': 1.0, 'prediction': 'Drone Detected', ...}
```

### Test 3: Check Service Availability
```python
import requests

r = requests.get('http://localhost:5000/api/audio_drone/status')
data = r.json()

if data['available']:
    print("✅ Audio drone detection service is available")
else:
    print("❌ Audio drone detection service is unavailable")

if data['last_result']:
    result = data['last_result']
    print(f"Last Detection: {result.get('prediction', 'N/A')}")
    print(f"Confidence: {result.get('confidence', 'N/A')}")
```

---

## Comprehensive Integration Test

### Run Full Test Suite
```python
#!/usr/bin/env python3
"""
Comprehensive AudioDroneDetectionService Integration Test
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = 'http://localhost:5000'
TEST_FILE = Path('audio1/backend/uploads/test_drone.wav')

def test_status_endpoint():
    """Test GET status endpoint"""
    print("Test 1: Status Endpoint")
    r = requests.get(f'{BASE_URL}/api/audio_drone/status')
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert 'available' in data
    assert 'last_result' in data
    print("  ✅ Status endpoint working")
    return data

def test_predict_endpoint():
    """Test POST predict endpoint"""
    print("\nTest 2: Prediction Endpoint")
    with open(TEST_FILE, 'rb') as f:
        r = requests.post(f'{BASE_URL}/api/audio_drone/predict', files={'file': f})
    
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    
    required_fields = ['success', 'available', 'detected', 'prediction', 'confidence', 'raw_score']
    for field in required_fields:
        assert field in data, f"Missing field: {field}"
    
    print(f"  ✅ Prediction endpoint working")
    print(f"  Detection Result: {data['prediction']} (confidence: {data['confidence']})")
    return data

def test_ai_status_integration():
    """Test audio drone appears in combined AI status"""
    print("\nTest 3: AI Status Integration")
    r = requests.get(f'{BASE_URL}/api/ai_status')
    data = r.json()
    
    assert 'audio_drone_available' in data, "audio_drone_available not in response"
    assert 'audio_drone_last_result' in data, "audio_drone_last_result not in response"
    
    print("  ✅ Audio drone integrated into AI status")
    print(f"  Available: {data['audio_drone_available']}")
    if data['audio_drone_last_result']:
        print(f"  Last Result: {data['audio_drone_last_result'].get('prediction', 'N/A')}")

def test_ui_contains_audio_controls():
    """Test main page includes audio UI elements"""
    print("\nTest 4: UI Integration")
    r = requests.get(BASE_URL)
    assert r.status_code == 200
    
    ui_elements = ['audio', 'analyze', 'drone']
    text_lower = r.text.lower()
    
    for element in ui_elements:
        assert element in text_lower, f"Missing UI element: {element}"
    
    print("  ✅ UI contains audio controls")

def test_response_consistency():
    """Make multiple predictions and verify consistency"""
    print("\nTest 5: Response Consistency")
    results = []
    
    for i in range(3):
        with open(TEST_FILE, 'rb') as f:
            r = requests.post(f'{BASE_URL}/api/audio_drone/predict', files={'file': f})
        results.append(r.json())
        time.sleep(0.5)
    
    # All should have same prediction for same file
    predictions = [r['detected'] for r in results]
    assert len(set(predictions)) == 1, f"Inconsistent predictions: {predictions}"
    
    print(f"  ✅ Consistent predictions across 3 requests")

def main():
    print("=" * 60)
    print("Audio Drone Detection Integration Test Suite")
    print("=" * 60)
    
    try:
        test_status_endpoint()
        test_predict_endpoint()
        test_ai_status_integration()
        test_ui_contains_audio_controls()
        test_response_consistency()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Integration is working correctly!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
```

**Save as:** `test_audio_integration.py`

**Run with:** `python test_audio_integration.py`

---

## Manual Browser Testing

### Test Workflow
1. **Navigate to**: `http://localhost:5000`
2. **Look for**: Audio Detection panel in UI
3. **Click**: Choose File button
4. **Select**: `audio1/backend/uploads/test_drone.wav`
5. **Click**: "Analyze Audio" button
6. **Observe**: Result displays "Drone Detected!"
7. **Voice Test**: Say "analyze audio" (if microphone available)
8. **Verify**: File picker opens when voice command recognized

### Expected UI Behavior
- Audio panel appears in right column (desktop) or below video feed (mobile)
- File picker filters to audio files (.wav, .mp3, .ogg, .m4a, .flac)
- Button shows loading state while processing
- Result appears immediately after analysis completes
- Status indicator shows "Ready" or latest detection result

---

## Performance Verification

### Inference Speed Test
```bash
time curl -X POST -F "file=@audio1/backend/uploads/test_drone.wav" \
  http://localhost:5000/api/audio_drone/predict > /dev/null
```

**Expected**: < 2 seconds for 3-second audio file

### Memory Usage Test
```bash
# Monitor before and after prediction
# Memory should return to baseline after cleanup
ps aux | grep 'python.*run.py'
```

---

## Cleanup Test Commands

### Delete Test Audio Files
```bash
rm audio1/backend/uploads/test_drone.wav
rm audio1/backend/uploads/test_no_drone.wav
```

### Verify No Temp Files Left
```bash
ls -la /tmp/ | grep camera_feed
find /tmp -name "*drone*.wav" -type f
```

Should return no results (cleanup is working)

---

## Troubleshooting Test Commands

### If Endpoints Return 404
```bash
# Verify routes are registered
python -c "from app import create_app; app = create_app(); 
routes = [str(r) for r in app.url_map.iter_rules() if 'audio' in str(r).lower()];
print('\n'.join(routes))"
```

### If Model Fails to Load
```bash
python -c "import os; 
print('Model exists:', os.path.exists('../audio1/backend/model/drone_audio_model.h5'))"
```

### If Audio File Upload Fails
```bash
# Verify file format
file audio1/backend/uploads/test_drone.wav
# Should output: WAV audio file
```

### If Inference Returns 503
```bash
# Check logs for specific error message
tail -f camera_feed_app.log | grep -i audio
```

---

## Continuous Integration Commands

### Health Check (suitable for CI/CD)
```bash
#!/bin/bash
# Check all audio-related endpoints
curl -s http://localhost:5000/api/audio_drone/status | jq '.available' && echo "✅ Audio detection available" || echo "❌ Audio detection unavailable"
```

### Automated Test (suitable for CI/CD)
```yaml
# GitHub Actions example
- name: Test Audio Integration
  run: |
    python -m pytest test_audio_integration.py -v
    # OR
    python test_audio_integration.py
```

---

## Success Criteria

- [x] GET /api/audio_drone/status returns HTTP 200
- [x] POST /api/audio_drone/predict accepts WAV files
- [x] Inference completes within 5 seconds
- [x] Audio panel visible in main UI
- [x] Voice commands recognized and processed
- [x] Status endpoint includes audio fields
- [x] All responses contain expected fields
- [x] No temporary files left after processing
- [x] Error handling returns appropriate HTTP codes
- [x] Model loads successfully on app startup

---

*Last Updated: 2026-02-25*
*Version: 1.0 - Production Ready*
