import aiofiles
import os
from pydantic import BaseModel
from fastapi import UploadFile
from typing import Union
# from faster_whisper import WhisperModel
from file_transcription_tracker import FileTranscriptionTracker
from transcription_tracker_code import GDriveID


from workflowstatus_code  import WorkflowStatus
from transformers import pipeline
import torch
import asyncio

# Define a Pydantic model for the Google Drive ID input
class GDriveInput(BaseModel):
    gdrive_id: str

AUDIO_QUALITY_DEFAULT = "medium.en"
COMPUTE_TYPE_DEFAULT = "float16"

AUDIO_QUALITY_DICT = {
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
    temp_directory = '/temp_mp3s'
    def __init__(self, tracker: FileTranscriptionTracker):
        self.tracker = tracker

        

    async def transcribe(self, input_file: Union[UploadFile, GDriveInput], audio_quality: str= AUDIO_QUALITY_DEFAULT, compute_type: str=COMPUTE_TYPE_DEFAULT):

        def transcribe_with_pipe(audio_filepath, model_name, compute_type):
            self.tracker.task_status.workflow_status = WorkflowStatus.LOADING_MODEL
            self.tracker.update_task_status(
                message=f"Loading Whisper model {model_name}",
            )
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device="cuda:0",
                torch_dtype=compute_type,
            )
            self.tracker.task_status.workflow_status = WorkflowStatus.MODEL_LOADED
            self.tracker.update_task_status()
            return pipe(
                audio_filepath, chunk_length_s=30, batch_size=8, return_timestamps=False
            )

        # Check to make sure the audio_quality value is in the AUDIO_QUALITY_DICT
        if audio_quality not in AUDIO_QUALITY_DICT:
            self.tracker.task_status.workflow_status = WorkflowStatus.ERROR
            error_message = f"Invalid audio quality {audio_quality}"
            self.tracker.update_task_status(message=error_message)
            raise 
        else:
            # set the model name based on the audio quality
            model_name = AUDIO_QUALITY_DICT[audio_quality]
        if compute_type not in COMPUTE_TYPE_MAP:
            self.tracker.task_status.workflow_status = WorkflowStatus.ERROR
            error_message = f"Invalid compute type {compute_type}"
            self.tracker.update_task_status(message=error_message)
            raise 
        else:
            compute_type = COMPUTE_TYPE_MAP[compute_type]

        loop = asyncio.get_running_loop()
        self.tracker.task_status.workflow_status = WorkflowStatus.TRANSCRIBING
        self.tracker.update_task_status()
        try:
            audio_filepath = await loop.run_in_executor(None, self._copy_input_to_temp_file, input_file)
            # # Process the audio file - This can also be a blocking call
            await loop.run_in_executor(None, transcribe_with_pipe, audio_filepath, model_name, compute_type)
            self.tracker.task_status.workflow_status = WorkflowStatus.TRANSCRIPTION_COMPLETE
            await loop.run_in_executor(None, self.tracker.update_task_status, message="Transcription completed.  Uploading")
            await self.tracker.upload_to_gdrive(audio_filepath)
        except Exception as e:
            self.tracker.task_status.workflow_status = WorkflowStatus.ERROR
            self.tracker.update_task_status(message=str(e))
            raise 

    async def _copy_input_to_temp_file(self, input_file):
        # Ensure the temporary directory exists
        os.makedirs(self.temp_directory, exist_ok=True)

        local_file_path = None  # Initialize the variable to ensure it's in scope

        if isinstance(input_file, UploadFile):
            # Handle the file uploaded directly through FastAPI
            try:
                local_file_path = await self._copy_uploaded_file_to_temp_file(self.temp_directory, input_file)
            except FileOperationError as e:
                self.tracker.logger.error(e.message)
                self.tracker.task_status.workflow_status = WorkflowStatus.ERROR
                self.tracker.update_task_status(message=str(e))
                raise  # Reraise the exception to handle it in the calling context

        elif isinstance(input_file, GDriveID):
            # Handle the file specified from Google Drive
            try:
                local_file_path = await self._copy_file_with_GDrive_ID_to_temp(self.temp_directory, input_file)
            except FileOperationError as e:
                self.tracker.logger.error(e.message)
                self.tracker.task_status.workflow_status = WorkflowStatus.ERROR
                self.tracker.update_task_status(message=str(e))
                raise  # Reraise the exception to handle it in the calling context

        else:
            # Handle unsupported file input types
            message_error = f"Unsupported file input type: {type(input_file).__name__}"
            self.tracker.logger.error(message_error)
            self.tracker.task_status.workflow_status = WorkflowStatus.ERROR
            self.tracker.update_task_status(message=message_error)
            raise TypeError(message_error)  # It's better to raise a more specific exception here

        # At this point, local_file_path should have been set by one of the branches above
        if local_file_path:
            self.tracker.logger.debug(f"File path for saving the mp3 file into a temporary directory: {local_file_path}")
            return local_file_path
        else:
            # Handle the case where local_file_path was not set due to an error
            raise FileOperationError("Failed to copy the input file to the temporary directory", input_file.filename if isinstance(input_file, UploadFile) else "GDrive file")
    
    async def _copy_uploaded_file_to_temp_file(self, temp_dir: str, file: UploadFile) -> str:
        try:
            temp_file_path = os.path.join(temp_dir, file.filename)
            async with aiofiles.open(temp_file_path, "wb") as temp_file:
                content = await file.read()  # Assuming UploadFile supports async read
                await temp_file.write(content)
            return temp_file_path
        except Exception as e:
            message_error = f"Error copying uploaded file {file.filename}. Error: {e}"
            raise FileOperationError(message_error, file.filename)

                
    async def _copy_file_with_GDrive_ID_to_temp(temp_dir: str, file_id: GDriveID) -> str:
        # Assuming you have an async method to download from GDrive
        file_name = "downloaded_filename.mp3"  # Placeholder for actual filename determination logic
        temp_file_path = os.path.join(temp_dir, file_name)
        await self.tracker.download_from_gdrive(file_id, temp_file_path)  # Assuming this is an async method
        return temp_file_path





 





