import pytest
from audio_transcriber_code import AudioTranscriber, GDriveInput
from gdrive_helper_code import GDriveHelper
from workflow_states_code import WorkflowStates
from pathlib import Path
from env_settings_code import get_settings

@pytest.fixture
def valid_mp3_gdrive_id():
    return '1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5'

@pytest.fixture
def valid_mp3_path():
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

@pytest.mark.asyncio
async def test_audio_transcription_workflow_mp3_gdrive_success(valid_mp3_gdrive_id):
    """
    Tests the end-to-end audio transcription workflow including uploading an MP3 file to Google Drive,
    initiating the transcription process, and verifying that the transcription is correctly stored.
    Assumes mp3_upload_file is a fixture providing a sample MP3 file and gdrive_folder_id is a Google Drive folder ID for testing.
    """
    # Setup - instantiate the main class and any dependencies
    transcriber = AudioTranscriber()
    # Step 2: Trigger the transcription process
    transcription_text = await transcriber.transcribe(GDriveInput(gdrive_id=valid_mp3_gdrive_id),audio_quality="medium", compute_type="float16")
    # Step 3: Verify the transcription result
    assert transcription_text is not None, "Transcription result should not be None"
    min_char_count = 100  # Example minimum character count
    assert len(transcription_text) >= min_char_count, f"Transcription text should contain at least {min_char_count} characters."
    assert isinstance(transcription_text, str), "Transcription result should be a string"
    assert len(transcription_text) > 0, "Transcription result should not be empty"
    # Step 4: Save transcription text to the GDrive transcription folder
    await transcriber.upload_transcript(transcription_text)
    gh = GDriveHelper()
    # Check that the status was set 
    transcription_status_dict = await gh.fetch_transcription_status_dict(valid_mp3_gdrive_id)
    assert transcription_status_dict['state'] == WorkflowStates.TRANSCRIPTION_UPLOAD_COMPLETE.name
    # Assert that the transcriptionId is not empty and has a reasonable length
    assert transcription_status_dict['transcriptionId'], "Transcription ID should not be empty"
    assert len(transcription_status_dict['transcriptionId']) > 20, "Transcription ID seems too short"  # Example length check, adjust as needed
    # Did the mp3 gfile's status info get updated to being complete?
    # Get the description from the mp3 gfile.
    # gh = GDriveHelper()
    # transcription_status_dict = gh.fetch_transcription_status_dict(valid_mp3_gdrive_id)





    # Optional: Cleanup - delete the uploaded MP3 file from Google Drive
    # await gdrive_helper.delete_gdrive_file(uploaded_file_id)
