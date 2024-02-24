import pytest
from fastapi.testclient import TestClient
from fastapi import BackgroundTasks
from unittest.mock import Mock
from app import app  # Adjust the import according to your project structure
# from your_module import Settings  # Adjust the import according to your project structure

client = TestClient(app)

@pytest.fixture
def mock_transcribe(mocker):
    # Mock the AudioToTranscript.transcribe method
    mocker.patch('audio_to_transcript.AudioToTranscript.transcribe', return_value=None)

@pytest.fixture
def mock_background_tasks(mocker):
    # Mock FastAPI's BackgroundTasks to verify tasks are added as expected
    mock_tasks = Mock(spec=BackgroundTasks)
    mocker.patch('fastapi.BackgroundTasks', return_value=mock_tasks)
    return mock_tasks

@pytest.fixture
def mock_process_input(mocker):
    # Mock the process_input dependency
    mock_input = Mock()  # Customize this based on what process_input is expected to return
    # Whenever the app tries to use this process_input function, don't actually run it. Instead, just pretend it ran and immediately return this fake object or value that's provided.
    mocker.patch('app.process_input', return_value=mock_input)
    return mock_input

def test_transcribe_mp3_endpoint(mock_transcribe, mock_background_tasks, mock_process_input):
    # Given: A payload representing an UploadFile or GDriveInput
    payload = {"gdrive_id": "fake_gdrive_id"}  # Adjust this payload as necessary

    # When: Making a POST request to the /transcribe/mp3 endpoint
    response = client.post("/transcribe/mp3", data=payload)
     # Debug: Print the response body to understand the error
    print(response.json())  # Add this line

    # Then: Expect a 200 OK response with the expected workflow_id and message
    assert response.status_code == 200
    assert "workflow_id" in response.json()
    assert "Transcription task started" in response.json().get("message", "")

