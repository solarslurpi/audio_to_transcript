from pydantic import BaseModel, field_validator, FilePath
from typing import Optional, Union
from env_settings_code import get_settings
import torch
from pathlib import Path
from gdrive_helper_code import GDriveInput
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

class TranscriptionOptionsWithUpload(CommonTranscriptionOptions):
    input_file: Union[UploadFile, GDriveInput]

    @field_validator('input_file')
    @classmethod
    def validate_input_file(cls,v):
        if not isinstance(v, UploadFile) or not isinstance(v,GDriveInput):
            raise ValueError(f"Input file must either be a gfile id (str) or UploadFile type. got {type(v)}")
        if not v.exists() or not v.is_file():
            raise ValueError(f"audio_file_path does not exist or is not a file: {v}")
        return v

class TranscriptText(BaseModel):
    text: str

    @field_validator('text')
    def text_must_be_at_least_50_characters(cls, v):
        if len(v) < 50:
            raise ValueError('Transcript text must be at least 50 characters')
        return v