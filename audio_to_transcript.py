
import re
import os
# from faster_whisper import WhisperModel
from shared import update_task_status, setup_logger, login_with_service_account
from pydrive2.drive import GoogleDrive
from workflowstatus_code  import WorkflowStatus
from transformers import pipeline
import torch
import asyncio
# yt_dlp is a fork of youtube-dl that has stayed current with the latest YouTube isms.  Youtube-dl is no longer
# supported so use yt_dlp.  It is more feature rich and up-to-date.
import yt_dlp as youtube_dl
from typing import Callable


# Define a mapping of return codes to messages used by the YouTube download module.
ret_code_messages = {
    0: "Placeholder for filename.",
    100: "[yt_dlp.download] Update required for yt-dlp, please restart.",
    101: "[yt_dlp.download] Download cancelled due to limits such as --max-downloads.",
    2: "[yt_dlp.download] There was an error with the user-provided options.",
    1: "[yt_dlp.download] An unexpected error occurred.",
    -1: "Expected MP3 file - {} - not found after download and processing.",
    -2: "Exception occured. Error:{} "
}


class AudioToTranscript:
    def __init__(
        self, task_id='', model_name="openai/whisper-large-v2",  compute_type=torch.float16):
        self.task_id = task_id
        self.model_name = model_name
        self.torch_compute_type = compute_type
        self.logger = setup_logger()
        self.downloaded_file_path = None # See _process_hook()


    async def atranscribe(self, audio_file):

        def transcribe_with_pipe():
            return pipe(audio_file, chunk_length_s=30, batch_size=8, return_timestamps=False)
        def load_pipeline():
            update_task_status(self.task_id, WorkflowStatus.TRANSCRIBING, messasge= f"Loading model {self.model_name}",logger=self.logger)
            pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device='cuda:0',
                torch_dtype=self.torch_compute_type
            )
            update_task_status (self.task_id, "Model loaded.")
            return pipe
        loop = asyncio.get_running_loop()
        # Update task status - this should ideally be an async function
        await loop.run_in_executor(None, update_task_status, self.task_id, WorkflowStatus.TRANSCRIBING,message=f"Starting processing {self.task_id}, logger=self.logger")
        # Process the audio file - This can also be a blocking call
        pipe = await loop.run_in_executor(None, load_pipeline)
        await loop.run_in_executor(None, update_task_status, self.task_id, WorkflowStatus.TRANSCRIBING,logger=self.logger)
        full_transcript = await loop.run_in_executor(None, transcribe_with_pipe)
        return full_transcript['text']



    async def adownload_youtube_audio(self, youtube_url: str):
        directory = "./temp_mp3s"
        if not os.path.exists(directory):
            os.makedirs(directory)
        # The _hook function defined within adownload_youtube_audio is a closure that captures the downloaded_file_path variable. This function is executed by yt-dlp when the download is finished, and it updates downloaded_file_path with the actual path of the downloaded file.
        filename_template = f"{self.task_id}_temp.%(ext)s"
        download_path_template = os.path.join(directory, filename_template)
        # Corrected to use async operation with yt_dlp
        ydl_opts = {
            "format": "mp3/bestaudio/best",
            "logger": self.logger,
            "outtmpl": download_path_template,
            "progress_hooks": [self._progress_hook],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "verbose": True,
        }

        async def download():
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                # yt-dlp download is not natively async, so use thread or process pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: ydl.download([youtube_url]))

        await download()
        mp3_filename = f"{self.task_id}_temp.mp3"
        self.downloaded_file_path = os.path.join(directory, mp3_filename) 
        update_task_status(self.task_id, WorkflowStatus.DOWNLOAD_COMPLETE, message=f"Download complete.  mp3 file saved to {self.downloaded_file_path}.")
        # File has been downloaded (see _process_hook).  Pass back the file path.
        if self.downloaded_file_path:
            self.logger.debug(f"Success! File downloaded to {self.downloaded_file_path}")
            return self.downloaded_file_path
        else:
            self.logger.error("Error downloading file.  No file path returned.")
            update_task_status(self.task_id, WorkflowStatus.DOWNLOAD_FAILED, message="Error downloading file.")
            return None

    async def upload_to_gdrive(self, gdrive_folder_id: str):
        # Perform authentication; this might be moved to a more central location in your application
        gauth = login_with_service_account()
        drive = GoogleDrive(gauth)

        # Ensure `self.downloaded_file_path` is set to the path of the file to upload
        if not self.downloaded_file_path or not os.path.exists(self.downloaded_file_path):
            if self.logger:
                self.logger.error("No file to upload or file does not exist.")
            return

        # Define the upload operation as a synchronous function
        def upload_operation():
            file_metadata = {
                'title': os.path.basename(self.downloaded_file_path),
                'parents': [{'id': gdrive_folder_id}]
            }
            gfile = drive.CreateFile(file_metadata)
            gfile.SetContentFile(self.downloaded_file_path)
            gfile.Upload()
            gfile.content.close()

            # Optionally, remove the local file after upload
            os.remove(self.downloaded_file_path)

            if self.logger:
                self.logger.info(f"Uploaded {self.downloaded_file_path} to Google Drive.")

        # Run the synchronous upload operation in the default executor
        await asyncio.get_event_loop().run_in_executor(None, upload_operation)


    def _progress_hook(self, d):
        if d['status'] == 'finished':
            self.logger.debug(f"Done downloading.  The current file is {d['filename']}, now post-processing ...")

        elif d['status'] == 'downloading':
            update_task_status(self.task_id, WorkflowStatus.DOWNLOADING, message=f"Downloading: {d['filename']}, {d['_percent_str']}, {d['_eta_str']}",logger=self.logger)
        else:
            update_task_status(self.task_id, f"{d['status']}")

    def _sanitize_title(self, title: str) -> str:
        # Replace spaces with underscores and remove unwanted characters
        sanitized_title = title.replace(" ", "_")
        sanitized_title = re.sub(r"[^\w\s-]", "", sanitized_title)
        return sanitized_title

    async def download_youtube_audio_to_gdrive(self, yt_url:str, GDRIVE_FOLDER_ID:str, update_task_status_callback:Callable=update_task_status):
        # If successful, this fills up the self.downladed_file_path because it created it and stored the mp3 bits in it.
        await self.adownload_youtube_audio(yt_url)
        if self.downloaded_file_path:
            await self.upload_to_gdrive(GDRIVE_FOLDER_ID)





