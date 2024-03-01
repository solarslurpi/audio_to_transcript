import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, field_validator, Field
from typing import Union, Optional
import torch
from fastapi import UploadFile

from workflow_states_code import WorkflowStates


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
async def validate_upload_file(upload_file: UploadFile):
    # Validate file extension
    valid_extensions = ['.mp3']
    _, file_extension = os.path.splitext(upload_file.filename)
    if file_extension not in valid_extensions:
        raise ValueError(f"Invalid file extension. It should be .mp3 but it is {file_extension}.")

    # Validate file size (async operation)
    await upload_file.seek(0)  # Move to end of file to get size
    file_size = len(upload_file.file.read()) # read to the end
    await upload_file.seek(0)  # Reset file pointer to beginning
    # Define your file size limit here
    min_size = 10_240  # Minimum mp3 size in bytes (10KB)
    if file_size < min_size:
        raise ValueError("File size too small to be a valid MP3 file.")
    # Return the file if all validations pass
    return upload_file

class GDriveInput(BaseModel):
    gdrive_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{25,33}$')

class ValidFileInput(BaseModel):
    input_file: Union[UploadFile, GDriveInput]

class TranscriptionOptions(BaseModel):
    audio_quality: str
    compute_type: str
    audio_path: Union[Path, None] = None
    input_file: Union[UploadFile, GDriveInput, None] = None

    # Ensure AUDIO_QUALITY_MAP and COMPUTE_TYPE_MAP are defined within the class

    @field_validator('audio_quality')
    @classmethod
    def check_audio_quality(cls, v):
        if v not in AUDIO_QUALITY_MAP.keys():
            raise ValueError(f"{v} is not a valid audio quality.")
        return v

    @field_validator('compute_type')
    @classmethod
    def check_compute_type(cls, v):
        if v not in COMPUTE_TYPE_MAP.keys():
            raise ValueError(f"{v} is not a valid compute type.")
        return v

    @field_validator("audio_path")
    def check_audio_path(cls, v: Union[str, Path, None]) -> Path:
        """
        Validates the audio_path field to be:
            - None
            - A valid Path object (absolute or relative)
            - Not pointing to a non-existent file or is not a file.
            - The file contains at least minimal bytes for an mp3 file (rough estimate)
        """

        if v is None:
            return None

        if not isinstance(v, Path):
            raise ValueError("audio_path must be a Path object or None")

        if not v.exists():
            raise ValueError(f"Path '{v}' does not exist")

        # Check file size (adjust max_file_size as needed)
        min_mp3_file_size = 1_024
        if v.is_file() and v.stat().st_size < min_mp3_file_size:
            raise ValueError(f"Audio file is not large enough to contain an mp3 file. The filesize is {min_mp3_file_size} bytes.")

        return v

class TranscriptText(BaseModel):
    text: str

    @field_validator('text')
    @classmethod
    def text_must_be_at_least_50_characters(cls, v):
        if v is None:
            raise ValueError('Transcript text must have text.  Currently, the value is None.')
        if len(v) < 50:
            raise ValueError('Transcript text must be at least 50 characters.')
        return v

class ValidPath(BaseModel):
    valid_file_path: Path

    @field_validator('valid_file_path')
    @classmethod
    def validate_input_file(cls,v):
        if not v.exists() or not v.is_file():
            raise ValueError(f"The path, {v} does not exist or is not a file.")
        return v



class ExtensionChecker:
    @staticmethod
    def is_mp3(filename: str) -> bool:
        """Check if the filename ends with '.mp3'."""
        return filename.endswith('.mp3')

class FilenameLengthChecker:
    MIN_LENGTH = 5  # Assuming the minimum "right length" for a filename
    MAX_LENGTH = 255  # Assuming the maximum "right length" for a filename

    @classmethod
    def is_right_length(cls, filename: str) -> bool:
        """Check if the filename's length is within the right range."""
        return cls.MIN_LENGTH <= len(filename) <= cls.MAX_LENGTH

class MP3filename(BaseModel):
    filename: str

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not ExtensionChecker.is_mp3(v):
            raise ValueError("It is assumed the file is an mp3 file that ends in mp3.")
        if not FilenameLengthChecker.is_right_length(v):
            raise ValueError(f"The file length is not between {FilenameLengthChecker.MIN_LENGTH} and {FilenameLengthChecker.MAX_LENGTH} .")
        return v
