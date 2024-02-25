import asyncio
from pathlib import Path
import aiofiles
from env_settings_code import get_settings
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
            self.logger.debug("FLOW: Start transcription workflow.")
            # First load the mp3 file (either a GDrive file or uploaded) into a local temporary file
            mp3_temp_file_path = await self._verify_and_prepare_mp3(input_file)
            await self.tracker.update_status(state=WorkflowStates.START, comment='Beginning the transcription workflow.', store=True)
            self.logger.debug(f"FLOW: A local copy of the mp3 file is at {mp3_temp_file_path}")
            await self.tracker.update_status(state=WorkflowStates.TRANSCRIPTION_STARTING, comment='Begin transcribing the mp3 file', store=True)
            transcription_text = await self._transcribe_mp3(mp3_temp_file_path, audio_quality, compute_type)
            await self.tracker.update_status(state=WorkflowStates.TRANSCRIPTION_COMPLETE, comment='Your comment here', store=True)
            return transcription_text
        except Exception as e:
            raise

    async def _verify_and_prepare_mp3(self, input_file: Union[UploadFile, GDriveInput]) -> Path:
        try:
            # Each of the methods will return an exception if the method isn't successful because if an mp3 file can't be processed, it can't be transcribed. Workflow can't continue.
            self.logger.debug("FLOW: Get mp3 files reading for transcription (_verify_and_prepare_mp3)")
            local_mp3_filepath,mp3_gfile_id = await self._copy_UploadFile_or_gfile_to_local(input_file)
            # We want to set these two fields as soon as possible since they are used to track the status of the workflow (through the mp3 gfile's metadata)
            self.tracker.mp3_gfile_id = mp3_gfile_id
            self.tracker.mp3_gfile_name = local_mp3_filepath.name
            return local_mp3_filepath
        except Exception:
            raise
      
    async def _copy_UploadFile_or_gfile_to_local(self, input_file: Union[UploadFile, GDriveInput]):

           
        async def _copy_UploadFile_to_local_and_get_gdrive_id(local_dir):
            try:
                local_mp3_file_path = local_dir / input_file.filename
                async with aiofiles.open(str(local_mp3_file_path), "wb") as temp_file:
                    content = await input_file.read()
                    await temp_file.write(content)
                # We also need to upload to the mp3 gdrive so that we have tracking.
                mp3_gfile_id = await self.gh.upload_mp3_to_gdrive(local_mp3_file_path)
                return local_mp3_file_path, mp3_gfile_id
            except Exception as e:
                await self.tracker.handle_error(status=WorkflowStates.ERROR,error_message='could not create a local copy of the mp3 file with UploadFile as the source.',operation='_copy_UploadFile_to_local_and_get_gdrive_id',store=False, raise_exception=True)
                
        async def _copy_gfile_to_local(local_dir):
            try:
                local_file_path = await self.gh.download_from_gdrive(input_file.gdrive_id, local_dir) 
                return local_file_path
            except Exception as e:
                await self.tracker.handle_error(status=WorkflowStates.ERROR,error_message='could not create a local copy of the mp3 file with GDriveInput as the source.',operation='_copy_UploadFile_mp3_to_local',store=False, raise_exception=True)
        local_dir = self.settings.local_mp3_dir
        if isinstance(input_file, UploadFile):
            # Directly call the nested function with the input_file
            local_mp3_file_path = await _copy_UploadFile_to_local_and_get_gdrive_id(local_dir)
        elif isinstance(input_file, GDriveInput):
            # Set up tracking
            self.tracker.mp3_gfile_id = input_file.gdrive_id
            local_mp3_file_path = await _copy_gfile_to_local(local_dir)
        self.logger.debug(f"Local file path is {local_mp3_file_path}")
        return local_mp3_file_path, input_file.gdrive_id
 
    async def _transcribe_mp3(self, audio_file_path: Path, audio_quality: str, compute_type: str) -> str:
        """
        Transcribes an MP3 file to text using the specified audio quality and compute type.
        """
        self.logger.debug("FLOW: Transcribe MP3 (_transcribe_mp3)")
        async def _validate_properties() -> tuple:
            self.logger.debug("FLOW: In Validate Properties (_validate_properties)")
            # Initialize variables to hold possibly updated values
            validated_audio_quality = audio_quality
            validated_compute_type = compute_type
            self.logger.debug(f"audio path: {audio_file_path}")
            # Validate audio file path
            if audio_file_path is None or not audio_file_path.exists() or not audio_file_path.is_file():
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
        audio_file_path_str = str(audio_file_path) # Pathname to filename.
        try:
            transcription_result = await loop.run_in_executor(
                None,
                lambda: self._transcribe_pipeline(audio_file_path_str, model_name, compute_float_type)
            )
            transcription_text = transcription_result['text']
            self.logger.debug(f"FLOW: SUCCESS!!! First 100 chars of pipeline: {transcription_text[:100]}")
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
            self.logger.debug("FLOW: Transcribe using HF's Transformer pipeline (_transcribe_pipeline)...LOADING MODEL")
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1,
                torch_dtype=compute_float_type
            )
            return pipe(audio_file_path, chunk_length_s=30, batch_size=8, return_timestamps=False)
    
    async def upload_transcript(self,transcript_text:str=None):
        try:
            await self.gh.upload_transcript_to_gdrive(transcript_text)
        except Exception as e:
            await self.tracker.handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED,error_message=f'{e}',operation='upload_transcript', store=True,raise_exception=True)
    
