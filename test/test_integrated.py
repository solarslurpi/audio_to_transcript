# These tests go through the full stack.
import pytest
from audio_transcriber_code import AudioTranscriber, GDriveInput
from io import BytesIO
from pathlib import Path
from fastapi import UploadFile
from gdrive_helper_code import GDriveHelper
from settings_code import get_settings

@pytest.fixture
def mp3_test_path():
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

@pytest.fixture
# **> ('The Reasoning Behind Pruning.mp3', '1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5')
#**> ('Episode 125： The Latest in Biocontrols with Suzanne Wainwright Evans.mp3', '1F53nsbXAoTPCSOkEB5W9gYgn28wM_c41')
#**> ('The Importance of Calcium in Cannabis with Bryant Mason (Soil Doctor).mp3', '1IN9ip1e8tt_tKRYjeSZI5vXpYS8sL3c_')
def gdrive_mp3_file():
    gdrive_input = GDriveInput(gdrive_id='1F53nsbXAoTPCSOkEB5W9gYgn28wM_c41')
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

@pytest.fixture
def mp3_upload_file(mp3_test_path:Path):
  # Open the MP3 file in binary read mode
    with open(mp3_test_path, 'rb') as file:
        # Since we can't return the file directly (it would close upon exiting the 'with' block),
        # we read the contents and create a new UploadFile object with BytesIO
        file_content = file.read()
    return UploadFile(filename=mp3_test_path.name, file=BytesIO(file_content))

@pytest.fixture
def gdrive_mp3_folder_id()->str:
     settings = get_settings()
     gdrive_folder_id = settings.gdrive_mp3_folder_id
     return gdrive_folder_id



@pytest.mark.asyncio
async def test_verify_and_prepare_upload_file_success( mp3_upload_file:UploadFile, mp3_file_temp_path:Path ):
    # This will test the copying of the mp3 file in the mp3_upload_file to a temparary file on the local drive.
    # Instantiate the transcriber
    transcriber = AudioTranscriber()

    # Now test the full code path for processing an uploaded mp3 file.
    temp_file_path = await transcriber._verify_and_prepare_file(mp3_upload_file)
    # Assert the returned path is as expected
    assert temp_file_path == mp3_file_temp_path, "The method did not return the correct file path."

@pytest.mark.asyncio
async def test_verify_and_prepare_gfile_id_success( gdrive_mp3_file:GDriveInput, mp3_file_temp_path:Path ):
    # This will test the copying of the mp3 file from the gdrive to a temparary file on the local drive.
    # Instantiate the transcriber
    transcriber = AudioTranscriber()
    helper = GDriveHelper()
    mp3_filename = await helper.get_filename(gdrive_mp3_file.gdrive_id)
    print(f"**> mp3_filename: {mp3_filename}")
    # # Now test the full code path for processing an uploaded mp3 file.
    temp_file_path = await transcriber._verify_and_prepare_file(gdrive_mp3_file)
    # # Assert the returned path is as expected
    assert temp_file_path.name == mp3_filename, "The method did not return the correct file path."

def test_gdrive_folder_list_success(gdrive_mp3_folder_id:str):
    helper = GDriveHelper()
    assert helper.drive is not None  # Checking if drive is initialized
    assert helper.gauth is not None  # Checking if authentication is successful

    # Optionally, perform an actual API call to verify interaction, e.g., list files
    # Be cautious with this approach to avoid unintended effects on your Google Drive.
    query = f"'{gdrive_mp3_folder_id}' in parents and trashed=false and mimeType='audio/mpeg'"
    files = helper.drive.ListFile({'q': query}).GetList()
    assert isinstance(files, list)  # Just a simple check to see if we got a list back
    for file in files:
    # Fetch metadata for the file
        print(f"\n**> {file['title'], file['id']}")
        assert(helper.check_gdrive_file_exists(file['id']))



