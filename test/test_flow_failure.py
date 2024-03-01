import pytest
from unittest.mock import patch, AsyncMock
from audio_transcriber_code import AudioTranscriber, WorkflowTracker

@pytest.fixture
def mock_transcribe_mp3():
    with patch('your_module.AudioTranscriber._transcribe_mp3', new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = "Mock transcription text"
        yield mock_transcribe

@pytest.fixture
async def setup_audio_transcriber():
    # Setup your AudioTranscriber instance here
    # Consider mocking external dependencies if necessary
    transcriber = AudioTranscriber()
    return transcriber

@pytest.fixture
async def setup_workflow_tracker():
    # Since WorkflowTracker is a singleton, you may want to reset its state before each test
    tracker = WorkflowTracker.get_instance()
    # Reset or reinitialize internal state as necessary
    return tracker

@pytest.mark.asyncio
async def test_transcribe_logs_start_state(setup_audio_transcriber, setup_workflow_tracker, mock_transcribe_mp3, caplog):
    # Execute the transcribe method which should trigger logging through update_status
    await setup_audio_transcriber.transcribe("input_file", "audio_quality", "compute_type")

    # Verify that the correct states are logged
    assert "START" in caplog.text
    assert "TRANSCRIPTION_STARTING" in caplog.text
    assert "TRANSCRIPTION_COMPLETE" in caplog.text

    # Further checks can be added to verify specific log messages or error handling



import pytest
import json
from audio_transcriber_code import AudioTranscriber, GDriveInput
from workflow_states_code import WorkflowEnum

@pytest.fixture
def mock_verify_and_prepare_mp3_failure(mocker):
    # Mock _verify_and_prepare_mp3 to raise an exception
    mocker.patch('audio_transcriber_code.AudioTranscriber._verify_and_prepare_mp3', side_effect=Exception("MP3 preparation failed"))

@pytest.fixture
def mock_verify_and_prepare_mp3_success(mocker):
    # Mock _verify_and_prepare_mp3 to raise an exception
    mocker.patch('audio_transcriber_code.AudioTranscriber._verify_and_prepare_mp3', return_value=None)

@pytest.fixture
def mock_transcribe_mp3_failure(mocker):
    # Mock _verify_and_prepare_mp3 to raise an exception
    mocker.patch('audio_transcriber_code.AudioTranscriber._transcribe_mp3', side_effect=Exception("MP3 transcribing failed"))

@pytest.fixture
def audio_transcriber_fixture():
    # Setup fixture for AudioTranscriber instance
    return AudioTranscriber()

@pytest.mark.asyncio
async def test_start_state_failure(audio_transcriber_fixture, mock_verify_and_prepare_mp3_failure, caplog):
    input_file = GDriveInput(gdrive_id="fake_id")

    with pytest.raises(Exception) as exc_info:
        await audio_transcriber_fixture.transcribe(input_file, "medium", "float32")

    assert "MP3 preparation failed" in str(exc_info.value)
    # Check that the "flow_state" in one of the log messages matches the expected state
    assert any(json.loads(record.message)["flow_state"] == WorkflowEnum.START.state_identifier for record in caplog.records)

@pytest.mark.asyncio
async def test_transcript_starting_state_failure(audio_transcriber_fixture,mock_verify_and_prepare_mp3_success, mock_transcribe_mp3_failure, caplog):
    input_file = GDriveInput(gdrive_id="fake_id")

    with pytest.raises(Exception) as exc_info:
        await audio_transcriber_fixture.transcribe(input_file, "medium", "float32")

    assert "MP3 transcribing failed" in str(exc_info.value)
    # Check that the "flow_state" in one of the log messages matches the expected state
    assert any(json.loads(record.message)["flow_state"] == WorkflowEnum.TRANSCRIPTION_STARTING.state_identifier for record in caplog.records)
