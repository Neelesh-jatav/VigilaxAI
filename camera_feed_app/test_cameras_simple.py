"""Simple camera list test"""
import json
import urllib.request

try:
    print('Fetching cameras from API...')
    resp = urllib.request.urlopen('http://127.0.0.1:5000/api/cameras', timeout=60)
    data = json.loads(resp.read().decode('utf-8'))
    
    print(f'\n✓ API Response: 200 OK')
    print(f'✓ Camera count: {len(data["cameras"])}')
    print(f'\nCamera list:')
    
    for i, cam in enumerate(data['cameras'], 1):
        print(f'  {i}. {cam["name"]} (Index {cam["index"]})')
    
    print(f'\n✓ Camera buttons UI will display {len(data["cameras"])} camera(s) horizontally')
    
except Exception as e:
    print(f'Error: {e}')
