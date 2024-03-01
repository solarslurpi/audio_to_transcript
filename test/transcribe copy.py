# test_audio_transcriber_init.py in the 'test' directory

import pytest
from unittest.mock import patch, AsyncMock
from pytest_mock import mocker
from audio_transcriber_code import AudioTranscriber, GDriveInput
from workflow_tracker_code import WorkflowTracker
from logger_code import LoggerBase
from gdrive_helper_code import GDriveHelper
from pathlib import Path
from workflow_states_code import WorkflowStates

# @pytest.fixture
# def mock_process_input(mocker):
#     # Mock the process_input dependency
#     mock_input = GDriveInput(gdrive_id="1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5")  # Customize this based on what process_input is expected to return
#     # Whenever the app tries to use this process_input function, don't actually run it. Instead, just pretend it ran and immediately return this fake object or value that's provided.
#     mocker.patch('app.process_input', return_value=mock_input)
#     return mock_input

# def test_audio_transcriber_init():
#     transcriber = AudioTranscriber()
#     print(f"***** {transcriber.logger.name}")
#     assert isinstance(transcriber.tracker, WorkflowTracker)
#     assert transcriber.logger.name == 'AudioTranscriber'
#     assert isinstance(transcriber.gh, GDriveHelper)

@pytest.mark.asyncio
async def test_transcribe_gdrive_simple_success(mocker):
    transcriber = AudioTranscriber()
    mock_input_file = GDriveInput(gdrive_id="1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5")
    mocker.patch.object(AudioTranscriber, '_verify_and_prepare_file',return_value=mock_input_file)
    text = await transcriber.transcribe(mock_input_file)
    assert isinstance(text,str)

@pytest.mark.asyncio
async def test_transcribe_gdrive_simple_failure(mocker):
    transcriber = AudioTranscriber()
    mock_input_file = GDriveInput(gdrive_id="1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5")
    mocker.patch.object(AudioTranscriber, '_verify_and_prepare_file',return_value=None)
    text = await transcriber.transcribe(mock_input_file)
    assert not text


@pytest.mark.asyncio
async def test_copy_mp3file_with_GDrive_ID_to_temp_file_success(mocker):
    # Setup
    transcriber = AudioTranscriber()
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    path_to_test_mp3 = Path(windows_file_path)

    # Use mocker.patch.object with new_callable=AsyncMock to mock the async method
    mocker.patch.object(transcriber.gh, 'download_from_gdrive', new_callable=AsyncMock, return_value=path_to_test_mp3)

    # Execute
    temp_file_path = await transcriber._copy_mp3file_with_GDrive_ID_to_temp_file("/temp/dir", "fake-gdrive-id")

    # Verify
    assert temp_file_path == path_to_test_mp3 # Convert Path object to string for comparison
    transcriber.gh.download_from_gdrive.assert_awaited_once_with("fake-gdrive-id", "/temp/dir")



@pytest.mark.asyncio
async def test_transcribe_exception_handling(mocker):
    transcriber = AudioTranscriber()

    # Use AsyncMock for async methods
    mocker.patch.object(transcriber, '_verify_and_prepare_file', new_callable=AsyncMock, side_effect=Exception('Failed to prepare file'))
    mocker.patch.object(transcriber.tracker, 'handle_error', new_callable=AsyncMock)

    fake_input = ...  # Construct a suitable fake input for the test

    await transcriber.transcribe(fake_input)

    transcriber.tracker.handle_error.assert_awaited_once_with(
        status=WorkflowStates.TRANSCRIPTION_FAILED,
        operation="transcription",
        error_message="Unexpected error: Failed to prepare file",
        store=True
    )



# def test_some_mock():
#     with patch('workflow_tracker_code.WorkflowTracker') as mock_tracker:
#         instance = mock_tracker.return_value
#         instance.make_status_dict.return_value = 'mocked value'
#         assert instance.make_status_dict() == 'mocked value'
#         # transcriber = AudioTranscriber()
        # mock_tracker.assert_called_once()
# @patch('workflow_tracker_code.WorkflowTracker')
# def test_audio_transcriber_init(mocker):
#     # with patch('workflow_tracker_code.WorkflowTracker') as mock_tracker, \
#     #      patch('logger_code.LoggerBase.setup_logger') as mock_setup_logger, \
#     #      patch('gdrive_helper_code.GDriveHelper') as mock_gdrive_helper:
#     mock_workflow_tracker = mocker.patch('workflow_tracker_code.WorkflowTracker')
#     # Instantiate the AudioTranscriber
#     transcriber = AudioTranscriber()

#     mock_workflow_tracker.assert_called_once()
#         # mock_setup_logger.assert_called_once_with("AudioTranscriber")
#         # mock_gdrive_helper.assert_called_once()

        # Assertions to check that the instances are correctly set
        # assert transcriber.tracker is mock_tracker.return_value
        # assert transcriber.logger is mock_setup_logger.return_value
        # assert transcriber.gh is mock_gdrive_helper.return_value
