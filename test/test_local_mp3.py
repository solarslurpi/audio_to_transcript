import pytest
from unittest.mock import AsyncMock, MagicMock

from audio_transcriber_code import AudioTranscriber, GDriveInput
from pathlib import Path



@pytest.fixture
def mp3_test_path():
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

@pytest.fixture
def mp3_gdrive():
    gdrive_input = GDriveInput(gdrive_id="1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5")
    return gdrive_input



@pytest.fixture
def mp3_file_temp_path():
    # Initialize AudioTranscriber to get the directory path
    transcriber = AudioTranscriber()
    temp_dir = transcriber.directory
    # Ensure the directory exists
    temp_dir.mkdir(parents=True, exist_ok=True)
        # Temporary file path
    temp_file_path = temp_dir / "test.mp3"
    return temp_file_path

@pytest.mark.asyncio
async def test_transcribe_exception_failure(mocker, mp3_gdrive):
    # Instantiate the transcriber
    transcriber = AudioTranscriber()
    # Patch '_verify_and_prepare_file' to raise an exception to simulate a failure
    mocker.patch.object(transcriber, '_verify_and_prepare_file', side_effect=Exception("File verification failed"))
    
    # Expect the transcribe method to handle the exception and not return the exception message.
    with pytest.raises(Exception, match="File verification failed"):
        await transcriber.transcribe(mp3_gdrive)

@pytest.mark.asyncio
async def test_verify_and_prepare_logic_upload_file_success(mocker, mp3_test_path, mp3_upload_file):
    # This will test the logic in _verify_and_prepare_file().
    # Instantiate the transcriber
    transcriber = AudioTranscriber()
    # Mocking the call that copies the file to the temp file since we are testing the process logic.
    mocker.patch.object(transcriber, '_copy_uploaded_file_to_temp_file', return_value=mp3_test_path)

    result_path = await transcriber._verify_and_prepare_file(mp3_upload_file)
    # Assert the returned path is as expected
    assert result_path == mp3_test_path, "The method did not return the correct file path."

@pytest.mark.asyncio
async def test_verify_and_prepare_logic_gdrive_success(mocker, mp3_test_path, mp3_gdrive):
    # This will test the logic in _verify_and_prepare_file().
    # Instantiate the transcriber
    transcriber = AudioTranscriber()
    # To avoid, network calls, the call to the download_from_gdrive is mocked.
    mocker.patch.object(transcriber.gh, 'download_from_gdrive', return_value=mp3_test_path)
    # Now test with the gdrive_input fixture. This will not actually go to gdrive to download
    # because the call that does this (download_from_gdrive) is mocked.  But it does test
    # the logic in _verify_and_prepare.
    result_path = await transcriber._verify_and_prepare_file(mp3_gdrive)

    # Assert the returned path is as expected
    assert result_path == mp3_test_path, "The method did not return the correct file path."





@pytest.mark.asyncio
async def test_verify_and_prepare_gfile_success(mp3_gdrive:GDriveInput):
    # Setup
    transcriber = AudioTranscriber()

    # Now test the full code path for processing an uploaded mp3 file.
    temp_file_path = await transcriber._verify_and_prepare_file(mp3_gdrive)

    # Verify
    assert temp_file_path == mp3_test_path # Convert Path object to string for comparison
    transcriber.gh.download_from_gdrive.assert_awaited_once_with("fake-gdrive-id", "/temp/dir")