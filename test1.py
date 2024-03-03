from io import BytesIO
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from fastapi import UploadFile

from workflow_tracker_code import WorkflowTracker
def valid_mp3_path():
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

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
    assert num_upload_bytes == num_valid_mp3_bytes
    return upload_file

upload_file = valid_UploadFile(valid_mp3_path())

json_item = jsonable_encoder(upload_file)
print(json_item)
# WorkflowTracker.update(status="start",
#                        comment="Starting the transcription workflow.",
#                        upload_file=upload_file
#                       )
