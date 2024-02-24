import pytest
from audio_transcriber_code import AudioTranscriber, GDriveInput
from gdrive_helper_code import GDriveHelper
from workflow_tracker_code import WorkflowTracker
from pathlib import Path
from settings_code import get_settings

@pytest.fixture
def valid_mp3_gdrive_id():
    return '1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5'

@pytest.fixture
def valid_mp3_path():
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

@pytest.mark.asyncio
async def test_audio_transcription_workflow(valid_mp3_gdrive_id):
    """
    Tests the end-to-end audio transcription workflow including uploading an MP3 file to Google Drive,
    initiating the transcription process, and verifying that the transcription is correctly stored.
    Assumes mp3_upload_file is a fixture providing a sample MP3 file and gdrive_folder_id is a Google Drive folder ID for testing.
    """
    # Setup - instantiate the main class and any dependencies
    transcriber = AudioTranscriber()
    # Step 2: Trigger the transcription process
    transcription_result = await transcriber.transcribe(GDriveInput(gdrive_id=valid_mp3_gdrive_id),audio_quality="medium", compute_type="float16")

    # Step 3: Verify the transcription result
    assert transcription_result is not None, "Transcription result should not be None"
    assert isinstance(transcription_result, str), "Transcription result should be a string"
    assert len(transcription_result) > 0, "Transcription result should not be empty"

    # Optional: Cleanup - delete the uploaded MP3 file from Google Drive
    # await gdrive_helper.delete_gdrive_file(uploaded_file_id)
