# test_app_youtube_download.py
from fastapi.testclient import TestClient
from app import app  # Adjust this import based on the structure of your project

client = TestClient(app)

def test_youtube_download_valid_url():
    # Replace "valid_youtube_url_here" with an actual YouTube video URL you expect to work
    response = client.post("/youtube/download", data={"yt_url": "https://www.youtube.com/watch?v=QSjOEqVrRAk"})
    assert response.status_code == 200  
    # extract out the task ID
    rsponse_json = response.json()
    assert "task_id" in rsponse_json
    task_id = rsponse_json["task_id"]
    # Star an SSE session 
    response = client.get(f"/status/{task_id}/stream")
    # Process the SSE stream
    message_count = 0
    for line in response.iter_lines(decode_unicode=True):
        # Check if line contains data
        if line.startswith('data:'):
            message_count += 1
            data = line.replace('data: ', '')
            print(f"Received update: {data}")  # Or parse JSON if the data is in JSON format
    assert message_count > 0  # Assuming the stream has at least one update
    
    # Additional assertions can be added here based on the expected response structure

# def test_youtube_download_invalid_url():
#     # Use an obviously invalid YouTube URL for this test
#     response = client.post("/youtube/download", json={"url": "https://invalidurl"})
#     assert response.status_code == 422  # Assuming validation occurs and rejects the URL

# def test_youtube_download_missing_url():
#     # Test posting without a URL to check for proper error handling
#     response = client.post("/youtube/download", json={})
#     assert response.status_code == 422  # FastAPI typically uses 422 for missing fields
