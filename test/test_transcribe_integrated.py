import pytest
from audio_transcriber_code import AudioTranscriber, GDriveInput
from gdrive_helper_code import GDriveHelper
from workflow_states_code import WorkflowStates
from pathlib import Path
from fastapi import UploadFile

@pytest.fixture
def valid_mp3_gdrive_id():
    return '1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5'

@pytest.fixture
def valid_mp3_path():
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

async def run_transcription_test_success(input_source, audio_quality="medium", compute_type="float16"):
    """
    Helper function to run the transcription test and perform common assertions.
    """
    transcriber = AudioTranscriber()
    transcription_text = await transcriber.transcribe(input_source, audio_quality, compute_type)

    assert transcription_text is not None, "Transcription result should not be None"
    min_char_count = 100  # Example minimum character count
    assert len(transcription_text) >= min_char_count, f"Transcription text should contain at least {min_char_count} characters."
    assert isinstance(transcription_text, str), "Transcription result should be a string"
    assert len(transcription_text) > 0, "Transcription result should not be empty"

    await transcriber.upload_transcript(transcription_text)
    gh = GDriveHelper()
    transcription_status_dict = await gh.fetch_transcription_status_dict(input_source.gdrive_id if isinstance(input_source, GDriveInput) else transcriber.tracker.mp3_gfile_id)
    assert transcription_status_dict['state'] == WorkflowStates.TRANSCRIPTION_UPLOAD_COMPLETE.name
    assert transcription_status_dict['transcriptionId'], "Transcription ID should not be empty"
    assert len(transcription_status_dict['transcriptionId']) > 20, "Transcription ID seems too short"

@pytest.mark.asyncio
async def test_audio_transcription_workflow_mp3_gdrive_success(valid_mp3_gdrive_id):
    await run_transcription_test_success(GDriveInput(gdrive_id=valid_mp3_gdrive_id))

@pytest.mark.asyncio
async def test_audio_transcription_workflow_mp3_upload_success(valid_mp3_path):
    with open(valid_mp3_path, 'rb') as mp3_file:
        upload_file = UploadFile(filename=valid_mp3_path.name, file=mp3_file)
        await run_transcription_test_success(upload_file)
