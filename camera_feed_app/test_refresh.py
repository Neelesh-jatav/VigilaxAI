#!/usr/bin/env python3
"""Test camera refresh speed."""
import json
import time
import urllib.request

print("\n=== TESTING CAMERA REFRESH SPEED ===\n")

url = 'http://127.0.0.1:5000/api/cameras'
print(f"Calling {url}...")

start = time.time()
try:
    with urllib.request.urlopen(url, timeout=15) as response:
        data = json.loads(response.read())
        elapsed = time.time() - start
        
        print(f"✓ Response received in {elapsed:.2f}s")
        print(f"✓ Status: {response.status}")
        print(f"✓ Found {len(data.get('cameras', []))} camera(s)")
        
        for cam in data.get('cameras', []):
            print(f"   - {cam['name']} (index: {cam['index']})")
            
        if elapsed < 5:
            print("\n✅ FAST REFRESH - Good performance!")
        else:
            print(f"\n⚠️  SLOW REFRESH - Took {elapsed:.2f}s")
            
except Exception as e:
    print(f"❌ Error: {e}")
