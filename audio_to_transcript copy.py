import aiofiles
import os
from pydantic import BaseModel
from fastapi import UploadFile
from typing import Union
from workflow_status_model import GDriveID
from transformers import pipeline
import torch
import asyncio
from settings_code import get_settings
from workflow_tracker_code import WorkflowTracker
from workflow_states_code import WorkflowStates
from workflow_error_code import handle_error
from logger_code import LoggerBase
from gdrive_helper_code import GDriveHelper

# Assuming the existence of necessary imports and global variables

class GDriveInput(BaseModel):
    gdrive_id: str

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
    settings = get_settings()
    directory = './temp_transcripts'


    def __init__(self):
        self.tracker = WorkflowTracker()
        self.logger = LoggerBase.setup_logger()
        self.gh = GDriveHelper()

    async def transcribe(self, input_file: Union[UploadFile, GDriveInput], audio_quality: str = settings.audio_quality_default, compute_type: str = settings.compute_type_default):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        try:
            temp_file_path = await self._get_verified_mp3_file(input_file)
            return await self._transcribe_and_upload(temp_file_path, audio_quality, compute_type)
        except Exception as e:
            await handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, error_message=f"{e}", operation="transcribe")

    async def _get_verified_mp3_file(self, input_file: Union[UploadFile, GDriveInput]) -> str:
        # Pydantic input validation makes sure we either have a file or a GDrive ID.
        if isinstance(input_file, UploadFile):
            try:
                file_path = await self._copy_uploaded_file_to_temp_file(self.directory, input_file)
            except Exception as e:
                error_message = f"{e}"
                await handle_error(error_message=error_message, operation="copy_uploaded_file_to_temp_file")
        elif isinstance(input_file, GDriveInput):
            self.logger.debug(f"Using GDriveInput. input file: {input_file}")
            try:
                file_path = await self._copy_mp3file_with_GDrive_ID_to_temp_file(self.directory, input_file.gdrive_id)
            except Exception as e:
                error_message = f"{e}"
                await handle_error(error_message=error_message, operation="copy_mp3file_with_GDrive_ID_to_temp_file")
        self.logger.debug(f"file_path: {file_path}")
        # Verify if the file is an MP3
        if not file_path.endswith('.mp3'):
            await handle_error(error_message=f"File {file_path} is not an MP3.")
        return file_path

    async def _transcribe_and_upload(self,audio_file_path, audio_quality, compute_type):
        from gdrive_helper_code import GDriveHelper
        self.tracker.workflow_status.transcription_audio_quality = audio_quality
        self.tracker.workflow_status.transcription_compute_type = compute_type
        self.logger.debug("in _transcribe_and_upload, starting transcription")
        transcription_text = await self._pipeline_transcription(audio_file_path, audio_quality, compute_type)
        self.logger.debug("done transcribing.")
        # Processing the transcription result
        base_name = os.path.basename(audio_file_path)
        local_file_name, _ = os.path.splitext(base_name)
        self.tracker.workflow_status.transcription_gdrive_filename = local_file_name
        local_file_path = os.path.join(self.directory, f"{local_file_name}.txt")
        self.logger.debug(f"Transcript at local_file_path: {local_file_path}")
        await self._save_transcription_to_file(transcription_text, local_file_path)
        gh = GDriveHelper()
        self.logger.debug("Starting transcript upload.")
        transcript_folder_gdriveID = self.settings.gdrive_transcripts_folder_id
        self.tracker.workflow_status.transcription_gdrive_id = await gh.upload_to_gdrive(folder_GdriveID=transcript_folder_gdriveID,file_path=local_file_path)
        self.logger.debug("Transcript is done uploading.")
        await self.tracker.update_status()
 
    async def _save_transcription_to_file(self, transcription_text, local_file_path):
        """
        Saves the transcription text to a local file asynchronously.
        """
        async with aiofiles.open(local_file_path, 'w') as file:
            await file.write(transcription_text)

    async def _pipeline_transcription(self,audio_file_path: str,audio_quality: str, compute_type: str) -> str:
        """
        Asynchronously transcribes an audio file using the Hugging Face pipeline.
        """
        loop = asyncio.get_running_loop()

        # Update tracker status asynchronously
        self.tracker.workflow_status.status = WorkflowStates.LOADING_MODEL
        await self.tracker.update_status()

        model_name = AUDIO_QUALITY_DICT.get(audio_quality,"openai/whisper-medium.en")
        compute_float_type = COMPUTE_TYPE_MAP.get(compute_type, torch.float16)
        self.logger.debug(f"in _pipeline_transcription, compute_float_type: {compute_float_type}, model_name: {model_name}")
        # Define the function to be executed in the executor
        def _transcribe_pipeline():
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1,  # Adjust based on your CUDA availability
                torch_dtype=compute_float_type
            )
            return pipe(audio_file_path, chunk_length_s=30, batch_size=8, return_timestamps=False)

        try:
            # Run the synchronous pipeline function in an executor
            transcription_result = await loop.run_in_executor(None, _transcribe_pipeline)
            transcription_text = transcription_result['text']
            self.logger.debug(f"transcription_text: {transcription_text[:50]}")
            return transcription_text
        except Exception as e:
            await handle_error(error_message=f"Transcription failed: {e}")
    



    async def _transcribe_mp3_file(self, file_path: str, audio_quality: str, compute_type: str):
        try:
            # Prepare model parameters
            model_name = AUDIO_QUALITY_DICT[audio_quality]
            torch_compute_type = COMPUTE_TYPE_MAP[compute_type]
            self.tracker.workflow_status.transcription_audio_quality = audio_quality
            self.tracker.workflow_status.transcription_compute_type = compute_type

            # Transcribe the file
            local_file_path = await self._transcribe_with_pipe(file_path, model_name, torch_compute_type)

            # Further processing, such as uploading to GDrive, can be done here
            # Make sure any method called here is properly handling exceptions as well

        except Exception as e:
            # Handle any errors that occurred during transcription or subsequent processing
            await handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, error_message=str(e), operation="_transcribe_mp3_file")


 
    async def _copy_uploaded_file_to_temp_file(self, temp_dir: str, file: UploadFile) -> str:
        try:
            temp_file_path = os.path.join(temp_dir, file.filename)
            async with aiofiles.open(temp_file_path, "wb") as temp_file:
                content = await file.read()
                await temp_file.write(content)
            return temp_file_path
        except Exception as e:
            await handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, error_message = f"{e}",operation="copy_uploaded_file_to_temp_file")

    async def _copy_mp3file_with_GDrive_ID_to_temp_file(self, temp_dir: str, gdrive_id: GDriveID) -> str:
        try:
            temp_file_path = await self.gh.download_from_gdrive(gdrive_id, temp_dir)  # Assuming this is an async method
        except Exception as e:
            await handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, error_message=f"{e}", operation="copy_file_with_GDrive_ID_to_temp_file")
        return temp_file_path
    

