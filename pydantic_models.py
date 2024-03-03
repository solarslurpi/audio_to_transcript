import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, field_validator, Field
from typing import Union, Optional
import torch
from fastapi import UploadFile

from workflow_states_code import WorkflowStates



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
