from run import app

with app.test_client() as client:
    # Test audio status endpoint
    response = client.get('/api/audio_drone/status')
    print(f"Audio Status Code: {response.status_code}")
    print(f"Audio Response: {response.get_json()}")
    print()
    
    # Test ai_status endpoint for comparison
    response2 = client.get('/api/ai_status')
    print(f"AI Status Code: {response2.status_code}")
    print(f"AI Response keys: {list(response2.get_json().keys())}")
