import asyncio
import os
import re
from logger_code import LoggerBase

# yt_dlp is a fork of youtube-dl that has stayed current with the latest YouTube isms.  Youtube-dl is no longer
# supported so use yt_dlp.  It is more feature rich and up-to-date.
import yt_dlp as youtube_dl


class YouTubeTransfer():
    directory = "./temp_mp3s"
    # Define a mapping of return codes to messages used by the YouTube download module.
    ret_code_messages = {
        0: "Successfully downloaded.",
        100: "[yt_dlp.download] Update required for yt-dlp, please restart.",
        101: "[yt_dlp.download] Download cancelled due to limits such as --max-downloads.",
        2: "[yt_dlp.download] There was an error with the user-provided options.",
        1: "[yt_dlp.download] An unexpected error occurred.",
        -1: "Expected MP3 file - {} - not found after download and processing.",
        -2: "Exception occured. Error:{} "
    }
    def __init__(self):
        self.logger = LoggerBase.setup_logger()
        self.tracker = None #TODO

    async def download_youtube_audio(self, youtube_url: str):
        self.tracker.task_status.youtube_url = youtube_url
        self.tracker.task_status.workflow_status = WorkflowStatus.DOWNLOAD_STARTING
        self.tracker.update_task_status()
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        # The _hook function defined within adownload_youtube_audio is a closure that captures the downloaded_file_path variable. This function is executed by yt-dlp when the download is finished, and it updates downloaded_file_path with the actual path of the downloaded file.

        # Corrected to use async operation with yt_dlp
        ydl_opts = {
            "format": "mp3/bestaudio/best",
            "logger": self.logger,
            "outtmpl": os.path.join(self.directory, "%(title)s.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "verbose": True,
        }
        loop = asyncio.get_event_loop()
        def download():
            self.tracker.task_status.workflow_status = WorkflowStatus.DOWNLOADING
            self.tracker.update_task_status()
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ret_code = ydl.download([youtube_url])
                return ret_code
                
        ret_code = await loop.run_in_executor(None, download)
        if ret_code != 0:
            error_message = "Download of {youtube_ursl} failed:"+ self.ret_code_messages.get(ret_code, "Unknown error occurred during download.")
            self.logger.error(f"{error_message}")
            # Update task status with the specific error message
            self.tracker.task_status.workflow_status = WorkflowStatus.ERROR
            self.tracker.update_task_status( message=error_message)
        return ret_code

    def _progress_hook(self, response):
        if response['status'] == 'finished':
            self.logger.debug(f"Done downloading.  The current file is {response['filename']}, now post-processing ...")
            original_path = response['filename']
            # # This status comes in from yt-dl before postprocessing.  
            # # First, strip the .webm part if it exists
            base_path = original_path.rsplit('.webm', 1)[0]
            filename = os.path.basename(base_path)
            # Remove non-alphanumeric characters, but keep spaces and periods
            sanitized_filename = re.sub(r'[^\w\s.]', '', filename)
            self.tracker.task_status.workflow_status = WorkflowStatus.DOWNLOADING
            self.tracker.task_status.mp3_gdrive_filename = sanitized_filename
            self.tracker.update_task_status()
            self.downloaded_file_path = f"{base_path}.mp3"
        elif response['status'] == 'downloading':
            self.tracker.update_task_status(message=f"Downloading: {response['filename']}, {response['_percent_str']}, {response['_eta_str']}",store=False)
        else:
            self.tracker.update_task_status( message=f"{response['status']}",store=False)

    async def download_youtube_audio_to_gdrive(self, yt_url:str):
        # If successful, this fills up the self.downladed_file_path because it created it and stored the mp3 bits in it.
        ret_code = await self.download_youtube_audio(yt_url)
        if ret_code == 0 and self.downloaded_file_path:
            # The code will capture errors and let us know.  Since this is the last step in our logic, we'll let the error handling do it's thing.
            await self.tracker.upload_to_gdrive(self.downloaded_file_path)