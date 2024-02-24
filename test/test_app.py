import pytest
from fastapi.testclient import TestClient
import app
from fastapi import status

client = TestClient(app.app)

@pytest.fixture
def audio_transcriber(mocker):
    mocker.patch('gdrive_helper_code.GDriveHelper.download_from_gdrive', return_value='mocked_value')

def test_health_check():
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Hello from Tim!"}

# Hypothetical test for a transcription endpoint that uses the audio_transcriber fixture
def test_transcription_endpoint(audio_transcriber):
    # Assuming there's an endpoint "/transcribe" that initiates the transcription process
    response = client.post("/transcribe/mp3", json={"gdrive_id": "some_gdrive_id"})
    
    # Asserting that the endpoint responds correctly
    # The response and status code will depend on your application's logic
    assert response.status_code == status.HTTP_200_OK
    assert "transcription" in response.json()
    # Further assertions can be made based on the expected response structure


