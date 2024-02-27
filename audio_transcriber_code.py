import asyncio
from pathlib import Path
import aiofiles
from env_settings_code import get_settings
from workflow_tracker_code import WorkflowTracker,WorkflowException
from logger_code import LoggerBase
from gdrive_helper_code import GDriveHelper,GDriveInput
from fastapi import UploadFile
from typing import Union
from workflow_states_code import WorkflowStates
import torch
from transformers import pipeline



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

    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def transcribe(self, input_file:Union[UploadFile, GDriveInput],audio_quality: str, compute_type: str) -> str:
        # First load the mp3 file (either a GDrive file or uploaded) into a local temporary file
        mp3_temp_path = await self.create_local_mp3_from_input(input_file)
        store = False if not self.tracker.mp3_gfile_id else True
        await self.tracker.update_status(state=WorkflowStates.START, comment='Beginning the transcription workflow.', store=store)
        
        transcription_text = await self.transcribe_mp3(mp3_temp_path, audio_quality, compute_type)

        return transcription_text

    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def create_local_mp3_from_input(self, input_file: Union[UploadFile, GDriveInput]) -> Path:
        if isinstance(input_file, UploadFile):
            self.tracker.mp3_gfile_id, mp3_path = await self.copy_uploadfile_to_local_mp3(input_file)    
        elif isinstance(input_file, GDriveInput):
            self.tracker.mp3_gfile_id, mp3_path = await self.copy_gfile_to_local_mp3(input_file.gdrive_id)   
        self.tracker.mp3_gfile_name = mp3_path.name
        return mp3_path



    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def copy_uploadfile_to_local_mp3(self, upload_file: UploadFile):
        local_mp3_file_path = Path(self.settings.local_mp3_dir) / upload_file.filename
        upload_file.file.seek(0)  # Rewind to the start of the file.
        async with aiofiles.open(str(local_mp3_file_path), "wb") as temp_file:
            content = await upload_file.read()
            await temp_file.write(content)
        mp3_gfile_id = await self.gh.upload_mp3_to_gdrive(local_mp3_file_path)
        return mp3_gfile_id, local_mp3_file_path
    
    
    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def copy_gfile_to_local_mp3(self, gdrive_id: str):
        local_file_path = await self.gh.download_from_gdrive(gdrive_id, self.settings.local_mp3_dir)
        return  gdrive_id, local_file_path


    async def a_what(Self):
        return "text","text"
   
    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def transcribe_mp3(self, audio_file_path: Path, audio_quality: str, compute_type: str) -> str:
        """
        Transcribes an MP3 file to text using the specified audio quality and compute type.
        """
        
        store = False if not self.tracker.mp3_gfile_id else True # whether to store the results depends on if we have mp3_gfile info. If
        # we don't it most likely means we started at transcribe_mp3 and not transcribe.
        await self.tracker.update_status(state=WorkflowStates.TRANSCRIPTION_STARTING, comment='In the beginning.', store=store)
        audio_quality, compute_type = await self.validate_properties(store)
        self.logger.debug("Properties have been validated.")
        self.whisper_transcribe(audio_file_path, audio_quality, compute_type)

        # Proceed with the transcription using validated or defaulted audio_quality and compute_type...

    @WorkflowTracker.async_error_handler(status=WorkflowStates.TRANSCRIPTION_FAILED, error_message="Audio file does not exist or is not a file.")
    async def validate_properties(self, audio_file_path, audio_quality, compute_type) -> bool:
        self.logger.debug("FLOW: In Validate Properties (_validate_properties)")
        # Initialize variables to hold possibly updated values
        validated_audio_quality = audio_quality
        validated_compute_type = compute_type
        self.logger.debug(f"audio path: {audio_file_path}")
        if audio_file_path is None or not audio_file_path.exists() or not audio_file_path.is_file():
              raise WorkflowException
        # Validate audio quality
        if audio_quality not in AUDIO_QUALITY_DICT.keys():
            self.logger.warning(f"Unsupported audio quality '{audio_quality}'. Falling back to default: {self.settings.audio_quality_default}.")
            validated_audio_quality = self.settings.audio_quality_default
        
        # Validate compute type
        if compute_type not in COMPUTE_TYPE_MAP.keys():
            self.logger.warning(f"Unsupported compute type '{compute_type}'. Falling back to default: {self.settings.compute_type_default}.")
            validated_compute_type = self.settings.compute_type_default  
        return validated_audio_quality, validated_compute_type    

        """
        Asynchronously transcribes an audio file using the specified audio quality and compute type.
        """
    @WorkflowTracker.async_error_handler(status=WorkflowStates.TRANSCRIPTION_FAILED)
    async def whisper_transcribe(self, audio_file_path, audio_quality, compute_type):
        model_name = AUDIO_QUALITY_DICT.get(audio_quality, self.settings.audio_quality_default)
        compute_float_type = COMPUTE_TYPE_MAP.get(compute_type, torch.float32)  # Adjusting the default to float32 for broader support

        self.logger.debug(f"Starting transcription with model: {model_name} and compute type: {compute_float_type}")
        await self.tracker.update_status(state = WorkflowStates.TRANSCRIBING, comment=f"Start by loading the whisper {audio_quality} model", store = store)
        loop = asyncio.get_running_loop()
        transcription_text = ""
        audio_file_path_str = str(audio_file_path) # Pathname to filename.
        transcription_result = await loop.run_in_executor(
            None,
            lambda: self._transcribe_pipeline(audio_file_path_str, model_name, compute_float_type)
        )
        transcription_text = transcription_result['text']
            
        await self.tracker.update_status(state=WorkflowStates.TRANSCRIPTION_COMPLETE, comment=f'Success! First 50 chars of pipeline: {transcription_text[:50]}', store=store)
        
        return transcription_text
    
    @WorkflowTracker.async_error_handler(status=WorkflowStates.TRANSCRIPTION_FAILED)
    async def _transcribe_pipeline(self, audio_file_path: str, model_name: str, compute_float_type: torch.dtype):
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
    
    @WorkflowTracker.async_error_handler(status=WorkflowStates.TRANSCRIPTION_FAILED)
    async def upload_transcript(self,transcript_text:str=None):
        store = False if not self.tracker.mp3_gfile_id else True
        await self.gh.upload_transcript_to_gdrive(transcript_text)

    
