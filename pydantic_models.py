import os
import re
from pathlib import Path

from pydantic import BaseModel, field_validator
from typing import Union
import torch
from fastapi import UploadFile


AUDIO_QUALITY_MAP = {
    "default":  "openai/whisper-medium.en",
    "tiny": "openai/whisper-tiny",
    "tiny.en": "openai/whisper-tiny.en",
    "base": "openai/whisper-base",
    "base.en": "openai/whisper-base.en",
    "small": "openai/whisper-small",
    "small.en": "openai/whisper-small.en",
    "medium": "openai/whisper-medium",
    "medium.en": "openai/whisper-medium.en",
    "large": "openai/whisper-large",
    "large-v2": "openai/whisper-large-v2",
}

COMPUTE_TYPE_MAP = {
    "float16": torch.float16,
    "float32": torch.float32,
}

# Asynchronous UploadeFile validation function
async def validate_upload_file(file: UploadFile):
    # Validate file extension
    valid_extensions = ['.mp3']
    _, file_extension = os.path.splitext(file.filename)
    if file_extension not in valid_extensions:
        raise ValueError(f"Invalid file extension. It should be .mp3 but it is {file_extension}.")

    # Validate file size (async operation)
    await file.seek(0, os.SEEK_END)  # Move to end of file to get size
    file_size = await file.tell()  # Get current position in file, which is its size in bytes
    await file.seek(0)  # Reset file pointer to beginning
    # Define your file size limit here
    min_size = 10_240  # Minimum mp3 size in bytes (10KB)
    if file_size < min_size:
        raise ValueError("File size too small to be a valid MP3 file.")if
    if file.content_type != 'audio/mpeg':
        raise ValueError(f"Invalid file type.  Should be audio/mpeg.  But it is: {file.content_type}")
    # Return the file if all validations pass
    return file

class GDriveInput(BaseModel):
    gdrive_id: str

    @field_validator('gdrive_id')
    @classmethod
    def id_must_match_google_drive_format(cls, v):
        # Regex to match the described format: 25-30 characters, including letters, numbers, and underscores
        pattern = re.compile(r'^[a-zA-Z0-9_-]{25,30}$')
        if not pattern.match(v):
            raise ValueError('Invalid Google Drive ID format')
        return v


class CommonTranscriptionOptions(BaseModel):
    audio_quality: str
    compute_type: str


    @field_validator('audio_quality')
    @classmethod
    def validate_audio_quality(cls, v):
        if v is not None and v not in AUDIO_QUALITY_MAP.keys():
            raise ValueError(f'{v} is not a valid model name.')
        return AUDIO_QUALITY_MAP[v]

    @field_validator('compute_type')
    @classmethod
    def validate_compute_type(cls, v):
        if v is not None and v not in COMPUTE_TYPE_MAP.keys():
            raise ValueError(f'{v} is not a valid compute type.')
        return COMPUTE_TYPE_MAP[v]

class TranscriptionOptionsWithPath(CommonTranscriptionOptions):
    audio_file_path: Path

    @field_validator('audio_file_path')
    @classmethod
    def validate_audio_file_path(cls,v):
        if not isinstance(v,Path):
            raise ValueError(f"audio_file_path must be a Path instance, got {type(v)}")
        if not v.exists() or not v.is_file():
            raise ValueError(f"audio_file_path does not exist or is not a file: {v}")
        return v

    # Specific validation for audio_file_path if needed

def validate_input_file(cls, v):
    if isinstance(v, dict):  # Assuming GDriveInput will be passed as a dict
        return GDriveInput(**v)
    elif isinstance(v, UploadFile):  # Or however you wish to validate UploadFile
        return v
    else:
        raise ValueError("Invalid input: must be an UploadFile or GDriveInput")

class TranscriptionOptionsWithUpload(CommonTranscriptionOptions):
    input_file: Union[UploadFile, GDriveInput]

    @field_validator('input_file')
    @classmethod
    def validate(cls,v):
        validate_input_file(cls,v)

class ValidInput(BaseModel):
    input_file: Union[UploadFile, GDriveInput]

    @field_validator('input_file')
    @classmethod
    def validate(cls, v):
        validate_input_file(cls,v)



class TranscriptText(BaseModel):
    text: str

    @field_validator('text')
    @classmethod
    def text_must_be_at_least_50_characters(cls, v):
        if len(v) < 50:
            raise ValueError('Transcript text must be at least 50 characters')
        return v

class ValidPath(BaseModel):
    valid_file_path: Path

    @field_validator('valid_file_path')
    @classmethod
    def validate_input_file(cls,v):
        if not v.exists() or not v.is_file():
            raise ValueError(f"The path, {v} does not exist or is not a file.")
        return v
