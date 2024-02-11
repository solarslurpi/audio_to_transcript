import asyncio
import os
from logger_code import LoggerBase
from file_transcription_tracker import FileTranscriptionTracker
from workflowstatus_code import WorkflowStatus
# yt_dlp is a fork of youtube-dl that has stayed current with the latest YouTube isms.  Youtube-dl is no longer
# supported so use yt_dlp.  It is more feature rich and up-to-date.
import yt_dlp as youtube_dl
from pydrive2.drive import GoogleDrive
from pydrive2.auth import GoogleAuth

class YouTubeTransfer():
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
    def __init__(self, task_id):
        self.logger = LoggerBase.setup_logger()
        self.tracker = FileTranscriptionTracker()
        self.task_id = task_id
    def login_with_service_account(self):
        """
        Google Drive service with a service account.
        note: for the service account to work, you need to share the folder or
        files with the service account email.

        :return: google auth
        """
        # Define the settings dict to use a service account
        # We also can use all options available for the settings dict like
        # oauth_scope,save_credentials,etc.
        settings = {
                    "client_config_backend": "service",
                    "oauth_scope": ["https://www.googleapis.com/auth/drive"],
                    "service_config": {
                        "client_json_file_path": "service-account-creds.json",
                    }
                }
        # Create instance of GoogleAuth
        gauth = GoogleAuth(settings=settings)
        # Authenticate
        gauth.ServiceAuth()
        return gauth
    async def download_youtube_audio(self, youtube_url: str):

        directory = "./temp_mp3s"
        if not os.path.exists(directory):
            os.makedirs(directory)
        # The _hook function defined within adownload_youtube_audio is a closure that captures the downloaded_file_path variable. This function is executed by yt-dlp when the download is finished, and it updates downloaded_file_path with the actual path of the downloaded file.

        # Corrected to use async operation with yt_dlp
        ydl_opts = {
            "format": "mp3/bestaudio/best",
            "logger": self.logger,
            "outtmpl": os.path.join(directory, "%(title)s.%(ext)s"),
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
            self.tracker.update_task_status(self.task_id, WorkflowStatus.DOWNLOADING)
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ret_code = ydl.download([youtube_url])
                return ret_code
                
        ret_code = await loop.run_in_executor(None, download)
        if ret_code != 0:
            error_message = self.ret_code_messages.get(ret_code, "Unknown error occurred during download.")
            self.logger.error(f"Download of {youtube_url} failed: {error_message}")
            # Update task status with the specific error message
            self.tracker.update_task_status(self.task_id, WorkflowStatus.ERROR, message=error_message)
        return ret_code

    async def upload_to_gdrive(self, gdrive_folder_id: str):
        # Perform authentication; this might be moved to a more central location in your application
        gauth = self.login_with_service_account()
        drive = GoogleDrive(gauth)

        # Ensure `self.downloaded_file_path` is set to the path of the file to upload
        if not self.downloaded_file_path or not os.path.exists(self.downloaded_file_path):
            self.logger.error("No file to upload or file does not exist.")
            self.tracker.update_task_status(self.task_id, WorkflowStatus.ERROR, message="No file to upload or file does not exist.")
            return

        # Define the upload operation as a synchronous function
        def upload_operation():
            try:
                file_name = os.path.basename(self.downloaded_file_path)
                file_metadata = {
                    'title': file_name,
                    'parents': [{'id': gdrive_folder_id}],
                    'mimeType': 'audio/mpeg',
                }
                gfile = drive.CreateFile(file_metadata)
                gfile.SetContentFile(self.downloaded_file_path)
                gfile.Upload()
                # Close the file content stream if it's open
                if hasattr(gfile, 'content') and gfile.content:
                    gfile.content.close()

                # Optionally, remove the local file after upload
                os.remove(self.downloaded_file_path)

                if self.logger:
                    self.logger.info(f"Uploaded {self.downloaded_file_path} to Google Drive.")
                self.tracker.update_task_status(self.task_id, WorkflowStatus.UPLOAD_COMPLETE)
            except Exception as e:
                self.logger.error(f"Error uploading {self.downloaded_file_path} to Google Drive: {e}")
                self.tracker.update_task_status(self.task_id, WorkflowStatus.ERROR, message=f"Error uploading {self.downloaded_file_path} to Google Drive: {e}")


        # Run the synchronous upload operation in the default executor
        await asyncio.get_event_loop().run_in_executor(None, upload_operation)


    def _progress_hook(self, response):
        if response['status'] == 'finished':
            self.logger.debug(f"Done downloading.  The current file is {response['filename']}, now post-processing ...")
            original_path = response['filename']
            # # This status comes in from yt-dl before postprocessing.  
            # # First, strip the .webm part if it exists
            base_path = original_path.rsplit('.webm', 1)[0]
            self.downloaded_file_path = f"{base_path}.mp3"
        elif response['status'] == 'downloading':
            self.tracker.update_task_status(self.task_id, WorkflowStatus.DOWNLOADING, message=f"Downloading: {response['filename']}, {response['_percent_str']}, {response['_eta_str']}")
        else:
            self.tracker.update_task_status(self.task_id, message=f"{response['status']}")

    async def download_youtube_audio_to_gdrive(self, yt_url:str):
        # If successful, this fills up the self.downladed_file_path because it created it and stored the mp3 bits in it.
        ret_code = await self.download_youtube_audio(yt_url)
        if ret_code == 0 and self.downloaded_file_path:
            # The code will capture errors and let us know.  Since this is the last step in our logic, we'll let the error handling do it's thing.
            await self.upload_to_gdrive(self.tracker.GDRIVE_FOLDER_ID)