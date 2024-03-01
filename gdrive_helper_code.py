# gdrive_manager.py
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pathlib import Path
from workflow_states_code import WorkflowEnum
from workflow_tracker_code import WorkflowTracker
from env_settings_code import get_settings
from logger_code import LoggerBase
from misc_utils import async_error_handler,update_status
import asyncio
import json
from googleapiclient.errors import HttpError
import aiofiles
from pydantic_models import GDriveInput, TranscriptText, ValidPath, MP3filename
from typing import Union



class GDriveHelper:
    def __init__(self):
        self.logger = LoggerBase.setup_logger()
        self.gauth = self._login_with_service_account()
        self.drive = GoogleDrive(self.gauth)
        self.settings = get_settings()

    @async_error_handler(status=WorkflowEnum.ERROR)
    async def _login_with_service_account(self):
        settings = get_settings()
        login_settings = {
            "client_config_backend": "service",
            "oauth_scope": settings.google_drive_oauth_scopes,
            "service_config": {
                "client_json_file_path":settings.google_service_account_credentials_path
            }
        }
        gauth = GoogleAuth(settings=login_settings)
        gauth.ServiceAuth()
        return gauth


    @async_error_handler(status=WorkflowEnum.ERROR)
    async def upload_mp3_to_gdrive(self, mp3_file_path:ValidPath) -> GDriveInput:
        """
        Asynchronously uploads an MP3 file to Google Drive.

        This method uploads a local MP3 file to a specified folder in Google Drive and
        returns the Google Drive file ID of the uploaded MP3 file. The Google Drive folder
        ID is specified in the environment settings.

        Parameters:
        - input (ValidPath): A pydantic class that verifies the mp3_file_path entry is a valid Path variable.

        Returns:
        - str: The Google Drive file ID of the uploaded MP3 file.

        Raises:
        - Exception: Propagates any exceptions raised during the uploading process to Google Drive.
        """
        folder_gdrive_id = self.settings.gdrive_mp3_folder_id
        # Returns the gfile id of the mp3 file.
        return await self.upload(GDriveInput(gdrive_id=folder_gdrive_id), mp3_file_path)

    @async_error_handler(status=WorkflowEnum.ERROR,error_message = 'Could not upload the transcript to a gflie.')
    async def upload_transcript_to_gdrive(self,  transcript_text: TranscriptText) -> None:
            folder_transcript_id = self.settings.gdrive_transcripts_folder_id
            folder_transcript_input = GDriveInput(gdrive_id=folder_transcript_id)
            mp3_filename = await self.get_filename(folder_transcript_input)
            txt_filename = mp3_filename[:-4] + '.txt'
            local_transcript_dir = Path(self.settings.local_transcript_dir)
            local_transcript_file_path = local_transcript_dir / txt_filename
            async with aiofiles.open(str(local_transcript_file_path), "w") as temp_file:
                await temp_file.write(str(transcript_text))
            folder_gdrive_id = self.settings.gdrive_transcripts_folder_id

            # returns the gfile id of the transcription file. We will add this to the next update_status so we are tracking within the
            # mp3 file where the corresponding transcript file is located (by gfile id).
            transcription_gfile_id = await self.upload(GDriveInput(gdrive_id=folder_gdrive_id),local_transcript_file_path)
            WorkflowTracker.update({transcription_gfile_id:transcription_gfile_id})
            await update_status(state=WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE, comment='Adding the transcription gfile tracker id', transcript_gdriveid= transcription_gfile_id, store=True)

    @async_error_handler(status=WorkflowEnum.ERROR,error_message = 'Could not upload the transcript to gdrive transcript folder.')
    async def upload(self, folder_gdrive_input:GDriveInput, file_path: ValidPath) -> GDriveInput:
        folder_gdrive_id = folder_gdrive_input.gdrive_id
        gfile = self.drive.CreateFile({'parents': [{'id': folder_gdrive_id}]})
        gfile.SetContentFile(str(file_path))
        gfile.Upload()
        if hasattr(gfile, 'content') and gfile.content:
            gfile.content.close()
        #  TODO: Can remove the local transcript...
        gtranscription_id = GDriveInput(gdrive_id=gfile['id'])
        return gtranscription_id

    @async_error_handler(status=WorkflowEnum.ERROR,error_message = 'Could not get the filename of the gfile.')
    async def get_filename(self, gfile_input:GDriveInput) -> str:
        gfile_id = gfile_input.gdrive_id
        loop = asyncio.get_running_loop()
        def _get_filename():
                file = self.drive.CreateFile({'id': gfile_id})
                # Fetch the filename from the metadata
                file.FetchMetadata(fields='title')
                filename = file['title']
                return filename
        filename = await loop.run_in_executor(None, _get_filename)
        verified_filename = MP3filename(filename=filename)
        return verified_filename.filename

    @async_error_handler(status=WorkflowEnum.ERROR,error_message = 'Could not fetch the transcription status from the description field of the gfile.')
    async def get_status_dict(self, gdrive_input: GDriveInput) -> Union[dict, None]:
        gfile_id = gdrive_input.gdrive_id
        loop = asyncio.get_running_loop()

        def _get_transcription_status_dict() -> Union[dict, None]:
            gfile = self.drive.CreateFile({'id': gfile_id})
            gfile.FetchMetadata(fields="description")
            transcription_status_json = gfile['description']
            return json.loads(transcription_status_json) if transcription_status_json else None

        transcription_status_dict = await loop.run_in_executor(None, _get_transcription_status_dict)
        self.logger.debug(f"The transcription status dict is {transcription_status_dict} for gfile_id: {gfile_id}")
        return transcription_status_dict
