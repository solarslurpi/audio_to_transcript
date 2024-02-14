import aiofiles
import os
from pydantic import BaseModel
from fastapi import UploadFile
from typing import Union
from file_transcription_tracker import FileTranscriptionTracker
from transcription_tracker_code import GDriveID
from workflowstatus_code import WorkflowStatus
from transformers import pipeline
import torch
import asyncio

# Assuming the existence of necessary imports and global variables

class GDriveInput(BaseModel):
    gdrive_id: str

AUDIO_QUALITY_DEFAULT = "medium.en"
COMPUTE_TYPE_DEFAULT = "float16"

AUDIO_QUALITY_DICT = {
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
    "default": torch.get_default_dtype(),
    # "int8": torch.int8,
    # "int16": torch.int16,
    "float16": torch.float16,
    "float32": torch.float32,
}

class FileOperationError(Exception):
    def __init__(self, message, filename):
        super().__init__(message)
        self.filename = filename

class AudioToTranscript:
    temp_directory = './temp_mp3s'

    def __init__(self, tracker: FileTranscriptionTracker):
        self.tracker = tracker

    async def transcribe(self, input_file: Union[UploadFile, GDriveInput], audio_quality: str = AUDIO_QUALITY_DEFAULT, compute_type: str = COMPUTE_TYPE_DEFAULT):
        try:
            temp_file_path = await self._get_verified_mp3_file(input_file)
            return await self._transcribe_mp3_file(temp_file_path, audio_quality, compute_type)
        except Exception as e:
            raise

    async def _get_verified_mp3_file(self, input_file: Union[UploadFile, GDriveInput]) -> str:
        # Pydantic input validation makes sure we either have a file or a GDrive ID.
        if isinstance(input_file, UploadFile):
            try:
                file_path = await self._copy_uploaded_file_to_temp_file(self.temp_directory, input_file)
            except Exception as e:
                error_message = f"{e}"
                self.tracker.handle_error_message(error_message)
        elif isinstance(input_file, GDriveInput):
            try:
                file_path = await self._copy_file_with_GDrive_ID_to_temp_file(self.temp_directory, input_file.gdrive_id)
            except Exception as e:
                error_message = f"{e}"
                self.tracker.handle_error_message(error_message)

        # Verify if the file is an MP3
        if not file_path.endswith('.mp3'):
            self.tracker.handle_error_message(f"File {file_path} is not an MP3.")
        return file_path

    async def _transcribe_mp3_file(self, file_path: str, audio_quality: str, compute_type: str):
        def transcribe_with_pipe(audio_file, model_name, torch_compute_type):
            self.tracker.task_status.workflow_status = WorkflowStatus.LOADING_MODEL
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device="cuda:0",
                torch_dtype=torch_compute_type,
            )
            self.tracker.task_status.workflow_status = WorkflowStatus.TRANSCRIBING
            self.tracker.update_task_status()
            return pipe(
                file_path, chunk_length_s=30, batch_size=8, return_timestamps=False
            )
        try:
            loop = asyncio.get_running_loop()
            self.tracker.task_status.workflow_status = WorkflowStatus.TRANSCRIBING
            await loop.run_in_executor(None, self.tracker.update_task_status)
            # # Process the audio file - This can also be a blocking call
            model_name = AUDIO_QUALITY_DICT[audio_quality]
            torch_compute_type = COMPUTE_TYPE_MAP[compute_type]
            transcription = await loop.run_in_executor(None, transcribe_with_pipe, file_path, model_name, torch_compute_type)
            self.tracker.task_status.workflow_status = WorkflowStatus.TRANSCRIPTION_COMPLETE
            await loop.run_in_executor(None, self.tracker.update_task_status)
            await self.tracker.upload_to_gdrive(transcription)
        except Exception as e:
            self.tracker.task_status.workflow_status = WorkflowStatus.ERROR
            self.tracker.handle_error_message(f"{e}")
            raise 
    async def _copy_uploaded_file_to_temp_file(self, temp_dir: str, file: UploadFile) -> str:
        try:
            temp_file_path = os.path.join(temp_dir, file.filename)
            async with aiofiles.open(temp_file_path, "wb") as temp_file:
                content = await file.read()
                await temp_file.write(content)
            return temp_file_path
        except Exception as e:
            self.tracker.handle_error_message(f"{e}")

    async def _copy_file_with_GDrive_ID_to_temp_file(self, temp_dir: str, gdrive_id: GDriveID) -> str:
        temp_file_path = await self.tracker.download_from_gdrive(gdrive_id, temp_dir)  # Assuming this is an async method
        return temp_file_path
    

