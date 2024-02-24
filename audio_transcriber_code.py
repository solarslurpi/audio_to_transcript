import asyncio
from pathlib import Path
import aiofiles
from typing import Optional
from settings_code import get_settings
from workflow_tracker_code import WorkflowTracker
from logger_code import LoggerBase
from gdrive_helper_code import GDriveHelper
from pydantic import BaseModel
from fastapi import UploadFile
from typing import Union
from workflow_states_code import WorkflowStates
from workflow_status_model import GDriveID
import torch
from transformers import pipeline

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
    "float16": torch.float16,
    "float32": torch.float32,
}

class AudioTranscriber:
    def __init__(self):
        self.settings = get_settings()
        self.directory = Path('./temp_transcripts')
        self.tracker = WorkflowTracker.get_instance()
        self.logger = LoggerBase.setup_logger("AudioTranscriber")
        self.gh = GDriveHelper()

    async def transcribe(self, input_file:Union[UploadFile, GDriveInput],audio_quality: str, compute_type: str) -> str:
        try:
            # First load the mp3 file (either a GDrive file or uploaded) into a local temporary file
            mp3_temp_file_path = await self._verify_and_prepare_mp3(input_file)
            transcription_text = await self._transcribe_mp3(mp3_temp_file_path, audio_quality, compute_type)
            # TODO: Next, transcribe the local mp3 file and return the transcript as a string of text.
            return "Here is a transcription."
        except Exception as e:
            raise


    async def _verify_and_prepare_mp3(self, input_file: Union[UploadFile, GDriveInput]) -> Path:
        # Each of the methods will return an exception if the method isn't successful because if an mp3 file can't be processed, it can't be transcribed. Workflow can't continue.
        
        if isinstance(input_file, UploadFile):
            return await self._process_upload_file(input_file)
        elif isinstance(input_file, GDriveInput):
            self.logger.info(f"input file: {input_file}")
            return await self._process_gdrive_id(input_file.gdrive_id)
        else:
            await self.tracker.handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, error_message = f"The input file was of type {type(input_file)}.  It must be of type {type(UploadFile)} or {type(GDriveInput)}.",operation="_verify_and_prepare_file", store=True, raise_exception=True)
        
    async def _process_upload_file(self, input_file: UploadFile) -> Path:
        # Method returns exception if it does not successfully complete.
        return await self._copy_uploaded_file_to_temp_file(self.directory, input_file)

        
    async def _copy_uploaded_file_to_temp_file(self, temp_dir: Path, file: UploadFile) -> Path:
        try:
            temp_file_path = temp_dir / file.filename
            async with aiofiles.open(str(temp_file_path), "wb") as temp_file:
                content = await file.read()
                await temp_file.write(content)
            return temp_file_path
        except Exception as e:
            await self.tracker.handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, error_message = f"{e}",operation="copy_uploaded_file_to_temp_file", store=True,raise_exception=True)

    async def _process_gdrive_id(self, gdrive_id: GDriveID) -> Path:
        if not await self.gh.check_gdrive_file_exists(gdrive_id):
            await self.tracker.handle_error(
                status=WorkflowStates.TRANSCRIPTION_FAILED, 
                error_message=f"Failed to find file with gdrive_id: {gdrive_id}",
                operation="_process_gdrive_id", 
                store=True,
                raise_exception=True
            )
        return await self._copy_mp3file_with_GDrive_ID_to_temp_file(self.directory, gdrive_id)

        
    async def _copy_mp3file_with_GDrive_ID_to_temp_file(self, temp_dir: Path, gdrive_id: GDriveID) -> Path:
        try:
            return await self.gh.download_from_gdrive(gdrive_id, temp_dir)  # Assuming this is an async method
        
        except Exception as e:
            await self.tracker.handle_error(
                status=WorkflowStates.TRANSCRIPTION_FAILED.value, 
                error_message=f"Failed to copy GDrive file to temp: {e.reason}", 
                operation="copy GDrive file to temp", 
                store=True,
                raise_exception=True
            )
    async def _transcribe_mp3(self, audio_file_path: Path, audio_quality: str, compute_type: str) -> str:
        """
        Transcribes an MP3 file to text using the specified audio quality and compute type.
        """
        async def _validate_properties() -> tuple:
            # Initialize variables to hold possibly updated values
            validated_audio_quality = audio_quality
            validated_compute_type = compute_type
            self.logger.debug(f"audio path: {audio_file_path}")
            # Validate audio file path
            if not audio_file_path.exists() or not audio_file_path.is_file():
                self.logger.debug(f"audio path does not exist or is not a valid file")
                await self.tracker.handle_error(
                    status=WorkflowStates.TRANSCRIPTION_FAILED, 
                    error_message=f"Audio file does not exist or is not a file: {audio_file_path}",
                    operation="_transcribe_mp3", 
                    store=True,
                    raise_exception=True
                )
            
            # Validate audio quality
            if audio_quality not in AUDIO_QUALITY_DICT.keys():
                self.logger.warning(f"Unsupported audio quality '{audio_quality}'. Falling back to default: {self.settings.audio_quality_default}.")
                validated_audio_quality = self.settings.audio_quality_default
            
            # Validate compute type
            if compute_type not in COMPUTE_TYPE_MAP.keys():
                self.logger.warning(f"Unsupported compute type '{compute_type}'. Falling back to default: {self.settings.compute_type_default}.")
                validated_compute_type = self.settings.compute_type_default  
            return validated_audio_quality, validated_compute_type

        audio_quality, compute_type = await _validate_properties()
        self.logger.debug("Properties have been validated.")

        # Proceed with the transcription using validated or defaulted audio_quality and compute_type...

        """
        Asynchronously transcribes an audio file using the specified audio quality and compute type.
        """
        model_name = AUDIO_QUALITY_DICT.get(audio_quality, self.settings.audio_quality_default)
        compute_float_type = COMPUTE_TYPE_MAP.get(compute_type, torch.float32)  # Adjusting the default to float32 for broader support

        self.logger.debug(f"Starting transcription with model: {model_name} and compute type: {compute_float_type}")
        await self.tracker.update_status(state = WorkflowStates.LOADING_MODEL, comment=f"Loading the whisper {audio_quality} model", store = True)
        loop = asyncio.get_running_loop()
        transcription_text = ""

        try:
            transcription_result = await loop.run_in_executor(
                None,
                lambda: self._transcribe_pipeline(audio_file_path, model_name, compute_float_type)
            )
            transcription_text = transcription_result['text']
        except Exception as e:
            await self.tracker.handle_error(
                status=WorkflowStates.TRANSCRIPTION_FAILED, 
                error_message=f"{e}",
                operation="_transcribe_mp3", 
                store=True,
                raise_exception=True
            )

        return transcription_text

    def _transcribe_pipeline(self, audio_file_path: str, model_name: str, compute_float_type: torch.dtype):
            """
            Synchronously transcribes an audio file using the Hugging Face pipeline.
            """
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1,
                torch_dtype=compute_float_type
            )
            return pipe(audio_file_path, chunk_length_s=30, batch_size=8, return_timestamps=False)
    
    

