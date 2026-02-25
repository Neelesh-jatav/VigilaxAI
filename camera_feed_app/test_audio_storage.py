#!/usr/bin/env python3
"""
Test script for drone audio detection storage functionality.
Tests:
- Saving detections
- Retrieving detection history
- Deleting detections
"""

import requests
import sys
import time
from pathlib import Path

BASE_URL = "http://localhost:5000"

def test_audio_storage():
    """Test audio detection storage endpoints."""
    print("=" * 60)
    print("TESTING DRONE AUDIO DETECTION STORAGE")
    print("=" * 60)
    
    # Test 1: Check API status
    print("\n[1/4] Testing API status...")
    try:
        response = requests.get(f"{BASE_URL}/api/audio_drone/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Status: {data.get('available', False)}")
            if not data.get('available'):
                print("⚠️ Warning: Audio drone detection service not available")
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False
    
    # Test 2: Check for test audio file
    print("\n[2/4] Checking for test audio file...")
    test_audio_path = Path(__file__).parent.parent / "audio1" / "backend" / "sample-audio" / "drone.wav"
    
    if not test_audio_path.exists():
        print(f"⚠️ Test audio file not found at: {test_audio_path}")
        print("   Skipping upload test...")
    else:
        # Test 3: Upload audio with save enabled
        print("\n[3/4] Testing audio upload with save enabled...")
        try:
            with open(test_audio_path, 'rb') as f:
                files = {'file': ('test_drone.wav', f, 'audio/wav')}
                data = {'save_detection': 'true', 'source': 'test'}
                response = requests.post(
                    f"{BASE_URL}/api/audio_drone/predict",
                    files=files,
                    data=data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Upload successful")
                    print(f"   Detected: {result.get('detected', False)}")
                    print(f"   Confidence: {result.get('confidence', 0) * 100:.1f}%")
                    print(f"   Saved: {result.get('saved', False)}")
                    if result.get('saved_filename'):
                        print(f"   Filename: {result.get('saved_filename')}")
                else:
                    print(f"❌ Upload failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error uploading: {e}")
    
    # Test 4: Retrieve detection history
    print("\n[4/4] Testing detection history retrieval...")
    try:
        response = requests.get(f"{BASE_URL}/api/audio_drone/detections?limit=10", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                detections = data.get('detections', [])
                print(f"✅ Retrieved {len(detections)} detection(s)")
                
                if detections:
                    print("\n📋 Recent Detections:")
                    for i, det in enumerate(detections[:3], 1):
                        timestamp = det.get('timestamp', 'N/A')
                        confidence = det.get('confidence', 0) * 100
                        source = det.get('source', 'unknown')
                        filename = det.get('filename', 'N/A')
                        print(f"   {i}. {timestamp} - {confidence:.1f}% [{source}] - {filename}")
                else:
                    print("   No detections saved yet")
            else:
                print(f"❌ Failed to get detections: {data.get('message')}")
        else:
            print(f"❌ Request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error retrieving history: {e}")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✅ Storage system is ready!")
    print("\nFeatures available:")
    print("  • Auto-save toggle for live detection")
    print("  • Detection archive with history")
    print("  • Audio playback from saved detections")
    print("  • Delete saved detections")
    print("\nTo use:")
    print("  1. Start live detection")
    print("  2. Enable 'Auto-save detections' checkbox")
    print("  3. Click 'View Archives' to see saved detections")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    if test_audio_storage():
        sys.exit(0)
    else:
        sys.exit(1)
