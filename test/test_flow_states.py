import asyncio
from pathlib import Path
import pytest
from unittest.mock import AsyncMock
from audio_transcriber_code import AudioTranscriber
from gdrive_helper_code import GDriveInput
from audio_transcriber_code import AudioTranscriber


# @pytest fixture
# audio_transcriber_mock_list = [
#     {'function_path':'gdrive_helper_code.GDriveHelper.upload_mp3_to_gdrive',
#     'return_value': 'mp3 gfile id'},
#     {'function_path':'gdrive_helper_code.GDriveHelper.download_from_gdrive',
#     'return_value': 'test/test.mp3'},
#     {'function_path':'gdrive_helper_code.GDriveHelper.upload_transcript_to_gdrive',
#     'return_value': ''},
#     {'function_path':'gdrive_helper_code.GDriveHelper.update_transcription_status_in_gfile',
#     'return_value': ''},
# ]

@pytest.fixture
def mock_upload_mp3_to_gdrive(mocker):
    # Mock the async method
    mock = mocker.patch('gdrive_helper_code.GDriveHelper.upload_mp3_to_gdrive', new_callable=AsyncMock)
    # Set the return value for the mock
    mock.return_value = asyncio.Future()
    mock.return_value.set_result("mocked_gdrive_file_id")  # Set the result of the future to your desired return value
    return mock

@pytest.fixture
def mock_download_from_gdrive(mocker):
    # Mock the async method
    mock = mocker.patch('gdrive_helper_code.GDriveHelper.download_from_gdrive', new_callable=AsyncMock)
    # Set the return value for the mock
    mock.return_value = asyncio.Future()
    mock.return_value.set_result('test/test.mp3')  # Set the result of the future to your desired return value
    return mock

@pytest.fixture
def mock_pipe(mocker):
    mock = mocker.patch('transformers.pipeline', new_callable=AsyncMock)
    transcription_text_dict = {"text": "Some example transcription text"}
    mock.return_value = asyncio.Future()
    mock.return_value.set_result(transcription_text_dict)
    return mock

@pytest.fixture
def mock_copy_uploadfile_to_local(mocker):
    print("\n========\n***** In mock__copy.....")
    mock = mocker.patch('audio_transcriber_code.AudioTranscriber.copy_uploadfile_to_local', new_callable=AsyncMock)
    mock.return_value = asyncio.Future()
    mock.return_value.set_result(("an mp3 gfile id","test/test.mp3"))
    return mock

@pytest.fixture
def mock_copy_gfile_to_local(mocker):
    print("\n========\n***** In mock__copy.....")
    mock = mocker.patch('audio_transcriber_code.AudioTranscriber.copy_gfile_to_local', new_callable=AsyncMock)
    mock.return_value = asyncio.Future()
    mock.return_value.set_result(("an mp3 gfile id","test/test.mp3"))
    return mock

@pytest.fixture
def mock_a_what(mocker):
    print("\n>>>>>>>========\n***** In mock__copy.....")
    mock = mocker.patch('audio_transcriber_code.AudioTranscriber.a_what', new_callable=AsyncMock)
    mock.return_value = asyncio.Future()
    mock.return_value.set_result(("WHAT","WHAT"))
    return mock

@pytest.fixture
def audio_transcriber_fixture(mocker, mock_copy_uploadfile_to_local, mock_copy_gfile_to_local, mock_a_what):
    # mocker.patch('gdrive_helper_code.GDriveHelper.upload_transcript_to_gdrive', new_callable=AsyncMock)
    # mocker.patch('gdrive_helper_code.GDriveHelper.update_transcription_status_in_gfile', new_callable=AsyncMock)

    # Assuming the rest of AudioTranscriber's dependencies don't require async handling
    # or are already handled by other mocks/fixtures
    return AudioTranscriber()



@pytest.mark.asyncio
async def test_audio_transcription_process(audio_transcriber_fixture, caplog):
    # Example input setup
    input_file = GDriveInput(gdrive_id="example_gdrive_id")
    audio_quality = "default"
    compute_type = "float32"


    result = await audio_transcriber_fixture.copy_gfile_to_local()

    print(f"---> {result} <-----")

    # Execute the test
    result = await audio_transcriber_fixture.transcribe(input_file, audio_quality, compute_type)

    # # # Assertions here
    # # # Example: assert "transcription successful" in caplog.text

    # assert "START" in caplog.text
    # assert "TRANSCRIPTION_STARTING" in caplog.text
    # assert "TRANSCRIPTION_COMPLETE" in caplog.text
