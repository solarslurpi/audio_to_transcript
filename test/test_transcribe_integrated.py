import pytest
from audio_transcriber_code import AudioTranscriber, GDriveInput
from gdrive_helper_code import GDriveHelper
from workflow_states_code import WorkflowStates
from pathlib import Path
from fastapi import UploadFile
from io import BytesIO

@pytest.fixture
def valid_mp3_gdrive_id():
    return '1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5'

@pytest.fixture
def valid_mp3_path():
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

@pytest.fixture
def valid_UploadFile(valid_mp3_path):
    file_content = valid_mp3_path.read_bytes()
    # Create a BytesIO object from the binary content
    file_like = BytesIO(file_content)
    # Create an UploadFile object. The filename and content_type can be adjusted as needed.
    upload_file = UploadFile(filename=valid_mp3_path.name, file=file_like)
        # Display the number of bytes in the original file
    upload_file.file.seek(0) # rewrind to beginning
    num_upload_bytes = len(upload_file.file.read()) # read to the end
    upload_file.file.seek(0) # rewind the file for the next reader.
    num_valid_mp3_bytes = valid_mp3_path.stat().st_size
    assert(num_upload_bytes == num_valid_mp3_bytes)
    return upload_file

@pytest.mark.asyncio
async def test_check_upload_file_content(valid_UploadFile: UploadFile):
    # Read the first few bytes to check if the file has content
    assert(valid_UploadFile,UploadFile)
    content = await valid_UploadFile.read(10)  # Read the first 10 bytes
    # Check if anything was read
    if content:
        print(f"The file has content.")
    else:
        print("The file is empty.")
    # Reset the pointer to the beginning of the file for future reads
    await valid_UploadFile.seek(0)

def _run_asserts_for_local_mp3_path(mp3_gdrive_id, local_mp3_path):
    # Ensure mp3_path is an instance of Path and ends with '.mp3'
    assert isinstance(local_mp3_path, Path), "mp3_path should be a Path object"
    assert local_mp3_path.suffix == '.mp3', "The file should have an '.mp3' extension"
    # Check that the file at mp3_path contains bytes
    assert local_mp3_path.is_file(), "mp3_path should point to a file"
    assert local_mp3_path.stat().st_size > 0, "The file should contain bytes"
    # GDriveID
    assert isinstance(mp3_gdrive_id,str)
    assert len(mp3_gdrive_id) > 20 # Gdrive IDs are long...this is perhaps a naive check...

@pytest.mark.asyncio
async def test_copy_UploadFile_to_local_mp3_path(valid_UploadFile):
    transcriber = AudioTranscriber()
    mp3_gdrive_id, local_mp3_path = await transcriber.copy_uploadfile_to_local_mp3(valid_UploadFile)
    _run_asserts_for_local_mp3_path(mp3_gdrive_id, local_mp3_path)

@pytest.mark.asyncio      
async def test_copy_gfile_to_local_mp3_path(valid_mp3_gdrive_id):
    '''
    Test the first major part of the code: Preparing the mp3 file for transcription.
    '''
    transcriber = AudioTranscriber()
    mp3_gdrive_id, local_mp3_path = await transcriber.copy_gfile_to_local_mp3(valid_mp3_gdrive_id)
    # Ensure mp3_path is an instance of Path and ends with '.mp3'
    _run_asserts_for_local_mp3_path(mp3_gdrive_id, local_mp3_path)
    
@pytest.mark.asyncio 
async def test_transcribe_mp3_success(valid_mp3_path) :
    transcriber = AudioTranscriber()
    audio_quality="medium"
    compute_type="float16"
    transcription_text = await transcriber.transcribe_mp3(valid_mp3_path, audio_quality, compute_type)
    assert transcription_text is not None, "Transcription result should not be None"
    min_char_count = 100  # Example minimum character count
    assert len(transcription_text) >= min_char_count, f"Transcription text should contain at least {min_char_count} characters."
    assert isinstance(transcription_text, str), "Transcription result should be a string"
    assert len(transcription_text) > 0, "Transcription result should not be empty"

async def run_transcription_test_success(input_source, audio_quality="medium", compute_type="float16"):
    """Helper function to run the transcription test and perform common assertions."""
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
async def test_audio_transcription_workflow_mp3_upload_success(valid_UploadFile):
    """Test full transcription process for an UploadFile input."""
    await run_transcription_test_success(valid_UploadFile)

@pytest.mark.asyncio
async def test_audio_transcription_workflow_mp3_gdrive_success(valid_mp3_gdrive_id):
    """Test full transcription process for a Google Drive file ID input."""
    await run_transcription_test_success(GDriveInput(gdrive_id=valid_mp3_gdrive_id))
