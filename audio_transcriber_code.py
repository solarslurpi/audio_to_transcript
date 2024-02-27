###########################################################################################
# Author: HappyDay Johnson
# Version: 0.01
# Date: 2024-02-27
# Summary: The audio_transcriber module converts speech from audio files into
# written text. It processes audio files either uploaded directly or referenced
# by their Google Drive (gDrive) ID, producing text transcripts. The module
# utilizes Googl  Drive's description field of an audio file to track the
# transcription process and uploads the resulting text to a specified Google Drive
# folder, as defined in the environment settings.
#
# License Information: MIT License
#
# Copyright (c) 2024 HappyDay Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###########################################################################################
import asyncio
from pathlib import Path
from typing import Union, Tuple

import aiofiles
from fastapi import UploadFile
import torch
from transformers import pipeline

from env_settings_code import get_settings
from gdrive_helper_code import GDriveHelper, GDriveInput
from logger_code import LoggerBase
from pydantic_models import TranscriptionOptionsWithPath, TranscriptionOptionsWithUpload, TranscriptText
from workflow_states_code import WorkflowStates
from workflow_tracker_code import WorkflowTracker
import pysnooper


class AudioTranscriber:
    """
    Manages the transcription of audio files into text.

    This class encompasses the initial setup for the transcription environment, including configurations,
    directory paths, logging, and Google Drive helpers. It provides methods to handle the complete workflow
    of the transcription process from input to output. The workflow includes file management (both local and
    Google Drive), transcription using a specific API, and error handling throughout the process.

    Attributes:
        settings: Configuration settings for the transcriber.
        directory (Path): Path to the directory where temporary transcripts are stored.
        tracker (WorkflowTracker): An instance of WorkflowTracker to track the transcription process.
        logger (Logger): A logger for logging information about the transcription process.
        gh (GDriveHelper): A helper for interacting with Google Drive files.
    """
    def __init__(self):
        self.settings = get_settings()
        self.directory = Path('./temp_transcripts')
        self.tracker = WorkflowTracker.get_instance()
        self.logger = LoggerBase.setup_logger("AudioTranscriber")
        self.gh = GDriveHelper()

    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    @pysnooper.snoop()
    async def transcribe(self, options:TranscriptionOptionsWithUpload) -> str:
        """
        Asynchronously transcribes audio from an input source to text. This method handles the entire workflow of the
        transcription process, including loading the audio file from a specified source, transcribing the audio content
        to text, and managing any intermediate steps such as file conversions and quality adjustments.

        The method leverages various internal methods to perform specific tasks such as creating a local copy of the
        audio file, updating workflow status, and actual transcription using chosen models and compute types.

        Parameters:
        - options (Union[TranscriptionOptionsWithUpload, TranscriptionOptionsWithPath]): An instance of
        `TranscriptionOptionsWithUpload` or `TranscriptionOptionsWithPath` containing the necessary configuration
        for the transcription process. This includes the source of the audio file (either a direct upload or a reference
        to a file stored in Google Drive), audio quality preferences, and the desired compute type for transcription.

        Returns:
        - str: The transcribed text from the audio content.

        Raises:
        - Various exceptions related to file handling, transcription errors, or API limitations could be raised and are
        handled by the async_error_handler decorator to update the workflow status accordingly.

        Note:
        - This method is designed to be called asynchronously within an asyncio event loop to efficiently manage I/O
        operations and long-running tasks without blocking the execution of other coroutines.
    """
        # First load the mp3 file (either a GDrive file or uploaded) into a local temporary file
        mp3_temp_path = await self.create_local_mp3_from_input(options.input_file)
        await self.tracker.update_status(state=WorkflowStates.START, comment='Beginning the transcription workflow.', store=bool(self.tracker.mp3_gfile_id))
        transcription_options = TranscriptionOptionsWithPath(
            audio_quality=options.audio_quality,  # Assuming 'high' is a valid key in AUDIO_QUALITY_DICT
            compute_type=options.compute_type,    # Assuming 'gpu' is a valid key in COMPUTE_TYPE_MAP
            audio_file_path=Path(mp3_temp_path)  # Replace with an actual file path
        )
        transcription_text = await self.transcribe_mp3(transcription_options)
        self.logger.debug(f"Transcription: {transcription_text[:200]}")

        return transcription_text

    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def create_local_mp3_from_input(self, input_file: Union[UploadFile, GDriveInput]) -> Path:
        """
        Asynchronously creates a local copy of an MP3 file from the specified input.

        This method handles both uploaded files and Google Drive inputs. For an uploaded file,
        it directly saves the file to a local temporary directory. For a Google Drive input,
        it downloads the file from Google Drive to the local temporary directory. The method
        updates the workflow tracker with the Google Drive file ID (if applicable) and the
        name of the local MP3 file.  The mp3 Google Drive ID in particular is used by the
        workflow to track state of progress.

        Parameters:
        - input_file (Union[UploadFile, GDriveInput]): The source of the MP3 file, which can be
        an uploaded file (UploadFile) or a reference to a file stored in Google Drive (GDriveInput).

        Returns:
        - Path: The path to the local copy of the MP3 file.

        Raises:
        - Exception: Propagates any exceptions raised during the file copying or downloading process.
        """
        if isinstance(input_file, UploadFile):
            self.tracker.mp3_gfile_id, mp3_path = await self.copy_uploadfile_to_local_mp3(input_file)
        elif isinstance(input_file, GDriveInput):
            self.tracker.mp3_gfile_id, mp3_path = await self.copy_gfile_to_local_mp3(input_file.gdrive_id)
        self.tracker.mp3_gfile_name = mp3_path.name
        return mp3_path

    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def copy_uploadfile_to_local_mp3(self, upload_file: UploadFile) -> Tuple[str, Path]:
        """
        Asynchronously copies a FastAPI uploaded UploadFile MP3 file to a local directory and uploads it to Google Drive.

        This method takes an uploaded MP3 file, saves it to a specified local directory, and then uploads
        the file to Google Drive. It ensures the file pointer is at the start before reading, to guarantee
        accurate copying. The method wraps the file saving and uploading process with error handling,
        setting the workflow status to ERROR upon encountering any exceptions.

        Parameters:
        - upload_file (UploadFile): The uploaded file object provided by FastAPI, which contains
        the MP3 file to be copied and uploaded.

        Returns:
        - Tuple[str, Path]: A tuple containing the Google Drive file ID of the uploaded MP3 file and
        the path to the local copy of the MP3 file.

        Raises:
        - Exception: Any exception raised during the file saving or uploading process is caught
        and handled by the `async_error_handler` decorator, which sets the workflow status accordingly.
        """
        local_mp3_file_path = Path(self.settings.local_mp3_dir) / upload_file.filename
        upload_file.file.seek(0)  # Rewind to the start of the file.
        async with aiofiles.open(str(local_mp3_file_path), "wb") as temp_file:
            content = await upload_file.read()
            await temp_file.write(content)
        mp3_gfile_id = await self.gh.upload_mp3_to_gdrive(local_mp3_file_path)
        return mp3_gfile_id, local_mp3_file_path


    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def copy_gfile_to_local_mp3(self, gdrive_id: str) -> Tuple[str, Path]:
        """
        Downloads an MP3 file from Google Drive to the local server directory for processing.

        This function is called when the workflow starts off with a MP3 file stored stored on Google Drive.
        It makes a local copy of the contents of the file found with the gfile id. The method returns the original
        Google Drive ID and the local file path, aiding in file tracking and accessibility for the transcription process.

        Args:
            gdrive_id (str): The Google Drive ID of the MP3 file to be downloaded.

        Returns:
            Tuple[str, Path]: The Google Drive ID and the local file path where the MP3 has been saved.
        """
        local_file_path = await self.gh.download_from_gdrive(gdrive_id, self.settings.local_mp3_dir)
        return gdrive_id, local_file_path


    @WorkflowTracker.async_error_handler(status=WorkflowStates.ERROR)
    async def transcribe_mp3(self,  options: TranscriptionOptionsWithPath) -> str:
        """
        Transcribes a local MP3 file to text using the Whisper API based on specified options.

        Utilizes audio quality and compute type from `options` to tailor the transcription process.
        Updates the workflow tracker to indicate transcription start, relying on a Google Drive file ID if available.

        Args:
            options (TranscriptionOptionsWithPath): Configuration for transcription, including path to MP3 file, audio quality, and compute type.

        Returns:
            str: The transcribed text.

        Insight:
        This method is a core part of the transcription workflow, bridging between file preparation and the final text output.
        It highlights the use of specific transcription options to optimize accuracy and performance.
        """
        await self.tracker.update_status(state=WorkflowStates.TRANSCRIPTION_STARTING, comment='In the beginning.', store=bool(self.tracker.mp3_gfile_id))

        # Proceed with transcription using the validated options
        self.logger.debug(f"Transcribing with quality {options.audio_quality} and compute type {options.compute_type}")
        transcription_text = await self.whisper_transcribe(options)
        return transcription_text



    @WorkflowTracker.async_error_handler(status=WorkflowStates.TRANSCRIPTION_FAILED)
    async def whisper_transcribe(self, options: TranscriptionOptionsWithPath):
        """
        Performs audio transcription using the Whisper model, tailored by audio quality and compute type.

        This method is decorated with an error handler to update the workflow status to `TRANSCRIPTION_FAILED` upon encountering any issues. It leverages the Whisper model to convert audio from an MP3 file to text, utilizing the audio quality and compute type specified in `options`. The workflow tracker is updated at the start and upon completion of the transcription process.

        Args:
            options (TranscriptionOptionsWithPath): Configuration for the transcription process, including the path to the MP3 file, audio quality, and compute type.

        Returns:
            str: The transcribed text from the MP3 file.

        Insight:
        Central to the transcription workflow, this method directly interacts with the transcription model, reflecting the process's start, ongoing status, and completion in the workflow tracker. The choice of model and compute type allows for customizable transcription fidelity and performance.
        """
        model_name = options.audio_quality
        compute_float_type = options.compute_type

        self.logger.debug(f"Starting transcription with model: {model_name} and compute type: {compute_float_type}")
        await self.tracker.update_status(state = WorkflowStates.TRANSCRIBING, comment=f"Start by loading the whisper {model_name} model", store = bool(self.tracker.mp3_gfile_id))
        transcription_text = ""
        audio_file_path_str = str(options.audio_file_path) # Pathname to filename.
        transcription_text = await self._transcribe_pipeline(audio_file_path_str, model_name, compute_float_type)
        await self.tracker.update_status(state=WorkflowStates.TRANSCRIPTION_COMPLETE, comment=f'Success! First 50 chars of pipeline: {transcription_text[:50]}', store=bool(self.tracker.mp3_gfile_id))
        return transcription_text

    @WorkflowTracker.async_error_handler(status=WorkflowStates.TRANSCRIPTION_FAILED)
    async def _transcribe_pipeline(self, audio_filename: str, model_name: str, compute_float_type: torch.dtype) -> str:
        """
        Transcribes an audio file to text using a Hugging Face ASR model, considering model specifics and compute optimization.

        This method employs the Hugging Face `pipeline` for automatic speech recognition (ASR), specifying the model based on audio quality (model_name) and optimizing computation with the provided `compute_float_type`. It is designed to handle heavy lifting of audio processing in an asynchronous workflow, ensuring non-blocking operation in the main event loop.

        Args:
            audio_filename (str): The path to the audio file to be transcribed.
            model_name (str): Identifier for the Hugging Face ASR model to use.
            compute_float_type (torch.dtype): The data type for computation, indicating precision and possibly affecting performance.

        Returns:
            str: The transcribed text from the audio file.

        Insight:
        It's wrapped with an async error handler to gracefully handle failures, marking the transcription phase as failed in such events. The method encapsulates model loading and execution within a synchronous function, offloading it to an executor to maintain async workflow integrity.
        """
        self.logger.debug("FLOW: Transcribe using HF's Transformer pipeline (_transcribe_pipeline)...LOADING MODEL")
        def load_and_run_pipeline():
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1,
                torch_dtype=compute_float_type
            )
            return pipe(audio_filename, chunk_length_s=30, batch_size=8, return_timestamps=False)
        loop = asyncio.get_running_loop()
        # Run the blocking operation in an executor
        result = await loop.run_in_executor(None, load_and_run_pipeline)
        return result['text']

    @WorkflowTracker.async_error_handler(status=WorkflowStates.TRANSCRIPTION_FAILED)
    async def upload_transcript(self,transcript: TranscriptText) -> None:
        """
        Uploads validated transcription text to Google Drive.


        Args:
            transcript (TranscriptText): Validated transcription text encapsulated in a Pydantic model.

        Raises:
            ValueError: If the transcription text does not meet the specified validation criteria.
            Or participates in the try/except chain through the async_error_handler decorator.

        Note:
        The transcription text is validated for a minimum length of 50 characters by the TranscriptText Pydantic model to ensure meaningful content is processed.
        """
        await self.gh.upload_transcript_to_gdrive(transcript.text)
