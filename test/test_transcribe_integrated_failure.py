import pytest
from audio_transcriber_code import AudioTranscriber, GDriveInput
from gdrive_helper_code import GDriveHelper
from workflow_states_code import WorkflowStates
from pathlib import Path
import pytest
from pytest_mock import MockerFixture
from unittest.mock import AsyncMock


@pytest.fixture
def invalid_mp3_path():
    # Provide a path that doesn't exist or is not accessible
    return Path('/invalid/path/test.mp3')

@pytest.fixture
def invalid_mp3_gdrive_id():
    # Provide an invalid Google Drive file ID
    return 'invalid_gdrive_id'

@pytest.fixture
def mock_handle_error(mocker: MockerFixture):
    mock = mocker.patch('workflow_tracker_code.WorkflowTracker.handle_error', new_callable=AsyncMock)
    # raise an exception
    mock.side_effect = Exception("Test Exception")
    return mock

@pytest.fixture
def mock_download_from_gdrive(mocker: MockerFixture):
    mock = mocker.patch('gdrive_helper_code.GDriveHelper.download_from_gdrive', new_callable=AsyncMock)
    # raise an exception
    mock.side_effect = Exception("Test Exception")

    return mock


@pytest.mark.asyncio
async def test_copy_gfile_to_local_mp3_exception_handling(mock_download_from_gdrive,mock_handle_error):
    # Setup the exception to be raised by the mocked download_from_gdrive
    transcriber = AudioTranscriber()
    # Execute the method under test and assert it raises an exception as expected
    with pytest.raises(Exception, match="Test Exception"):
        await transcriber.copy_gfile_to_local_mp3("invalid_gdrive_id")

@pytest.mark.asyncio
async def test_copy_uploadfile_to_local_mp3_exception_handling(mock_handle_error):
    # Setup the exception to be raised by the mocked download_from_gdrive
    transcriber = AudioTranscriber()
    # Execute the method under test and assert it raises an exception as expected
    with pytest.raises(Exception, match="Test Exception"):
        await transcriber.copy_uploadfile_to_local_mp3("invalid_gdrive_id")

@pytest.mark.asyncio
async def test_transcribe_mp3_failure(invalid_mp3_path, mock_handle_error):
    transcriber = AudioTranscriber()
    with pytest.raises(Exception):
        await transcriber.transcribe_mp3(invalid_mp3_path, "medium", "float16")
