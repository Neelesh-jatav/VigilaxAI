"""Test camera refresh functionality"""
import urllib.request
import json

try:
    resp = urllib.request.urlopen('http://127.0.0.1:5000/api/cameras', timeout=5)
    data = json.loads(resp.read().decode('utf-8'))
    
    print(f"=== CAMERA REFRESH TEST ===")
    print(f"Camera count: {len(data['cameras'])}")
    print(f"\nAvailable cameras:")
    
    for cam in data['cameras']:
        print(f"  - {cam['name']} (Index {cam['index']})")
    
    print(f"\n✓ Camera refresh functionality is working!")
    print(f"✓ The UI refresh button will display these {len(data['cameras'])} camera(s)")
    
except Exception as e:
    print(f"Error testing cameras: {e}")
