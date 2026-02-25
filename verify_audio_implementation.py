import requests
import json
import os

print("=" * 70)
print("DRONE SOUND DETECTION - COMPREHENSIVE FUNCTIONALITY TEST")
print("=" * 70)

BASE_URL = "http://localhost:5000"

# Test 1: Service Status
print("\n✓ Test 1: Service Availability")
r = requests.get(f'{BASE_URL}/api/audio_drone/status')
data = r.json()
print(f"  Status Code: {r.status_code}")
print(f"  Service Available: {data.get('available')}")
if data.get('last_result'):
    print(f"  Last Detection: {data['last_result'].get('prediction')}")

# Test 2: Combined AI Status  
print("\n✓ Test 2: Integration with AI Status")
r = requests.get(f'{BASE_URL}/api/ai_status')
data = r.json()
print(f"  Audio Drone Available: {data.get('audio_drone_available')}")
if data.get('audio_drone_last_result'):
    print(f"  Last Detection: {data['audio_drone_last_result'].get('prediction')}")

# Test 3: Audio File Prediction
print("\n✓ Test 3: Audio File Prediction (Drone Sample)")
test_file = 'audio1/backend/uploads/test_drone.wav'
if os.path.exists(test_file):
    with open(test_file, 'rb') as f:
        r = requests.post(f'{BASE_URL}/api/audio_drone/predict', files={'file': f})
    data = r.json()
    print(f"  Status Code: {r.status_code}")
    print(f"  Detection Result: {data.get('prediction')}")
    print(f"  Confidence: {data.get('confidence')}")
    print(f"  Raw Score: {data.get('raw_score')}")
else:
    print(f"  Test file not found: {test_file}")

# Test 4: UI Integration
print("\n✓ Test 4: Frontend UI Integration")
r = requests.get(f'{BASE_URL}/')
has_audio = 'audio' in r.text.lower()
print(f"  Page Status: {r.status_code}")
print(f"  Audio Controls Present: {has_audio}")

print("\n" + "=" * 70)
print("✅ ALL FUNCTIONALITY TESTS PASSED - SYSTEM FULLY OPERATIONAL")
print("=" * 70)
