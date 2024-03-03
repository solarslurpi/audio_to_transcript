# gdrive_manager.py
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pathlib import Path
from workflow_states_code import WorkflowEnum
from workflow_tracker_code import WorkflowTracker
from env_settings_code import get_settings
from logger_code import LoggerBase
from misc_utils import async_error_handler, update_status
import asyncio
import json
from googleapiclient.errors import HttpError
import aiofiles
from pydantic_models import GDriveInput, TranscriptText, ValidPath, MP3filename
from typing import Union


class GDriveError(Exception):
    """Base class for Google Drive errors with a default error message."""
    def __init__(self, message=None, system_error=None):
        if message is None:
            message = "An error occurred with Google Drive operation."
        if system_error:
            message += f" Error: {system_error}"
        super().__init__(message)

class GDriveFileOperationError(GDriveError):
    """
    Raised for errors during file operations (create, delete, etc.) on Google Drive.
    """
    def __init__(self, operation=None, detail=None, system_error=None):
        message = "An error occurred during a Google Drive file operation."
        if operation:
            message = f"Failed to {operation} the Google Drive file."
        if detail:  # 'detail' can be a file ID, filename, or any relevant info
            message += f" Detail: {detail}."
        if system_error:
            message += f" System Error: {system_error}"
        super().__init__(message)

class GDriveHelper:
    def __init__(self):
        self.logger = LoggerBase.setup_logger()
        self.gauth = self._login_with_service_account()
        self.drive = GoogleDrive(self.gauth)
        self.settings = get_settings()


    def _login_with_service_account(self):
        settings = get_settings()
        login_settings = {
            "client_config_backend": "service",
            "oauth_scope": settings.google_drive_oauth_scopes,
            "service_config": {
                "client_json_file_path":settings.google_service_account_credentials_path
            }
        }
        try:
            gauth = GoogleAuth(settings=login_settings)
            gauth.ServiceAuth()
            return gauth
        except Exception as e:
            self.logger.error(f"Failed to authenticate with Google Drive service account. Error: {e}")
            raise Exception(f"Authentication failed: {e}") from e

    async def check_gdrive_file_exists(self, gfile_id: str) -> bool:
        self.logger.debug("FLOW: In Check GDrive File Exists (check_gdrive_file_exists)")
        async def do_error(err_msg):
            await self.tracker.handle_error(
                status=WorkflowEnum.TRANSCRIPTION_FAILED,
                error_message=f"Could not find the gfile with id {gfile_id}: {err_msg}",
                operation="check_gdrive_file_exists",
                store=False,
                raise_exception=True
            )
        try:
            # Attempt to retrieve the file's metadata
            file = self.drive.CreateFile({'id': gfile_id})
            file.FetchMetadata()
            return True
        except HttpError as error:
            if error.resp.status == 404:
                return False
            else:
                await do_error(f"An error occurred: {error}")

    def create_gdrive_file(self, folder_id: str, filename='not specified', mimeType='text/plain'):
        file_metadata = {
            'title': filename,
            'parents': [{'id': folder_id}],
            'mimeType': mimeType
        }

        try:
            gfile = self.drive.CreateFile(file_metadata)
            gfile.Upload()  # Creates the file in Google Drive
        except Exception as e:
            self.logger.error(f"Error uploading {filename} to Google Drive. Error: {e}")
            raise GDriveFileOperationError(operation='create', detail=filename, system_error=e)
        #return gfile['id']
        return gfile

    def delete_gdrive_file(self, file_id: str):
        try:
            file = self.drive.CreateFile({'id': file_id})
            file.Delete()
        except Exception as e:
            self.logger.error(f"Error deleting Google Drive file: {e}")
            raise GDriveFileOperationError(operation='delete', detail=file_id, system_error=e)

    @async_error_handler()
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
    async def upload_transcript_to_gdrive(self, mp3_gdriveInput: GDriveInput, transcript_text: TranscriptText) -> None:
            mp3_filename = await self.get_filename(mp3_gdriveInput)
            # Since we have the gdrive_id for the mp3 file, let us set it because perhaps the caller didn't start at the beginning of the workflow.
            # This way, we can update the status.
            self.tracker.mp3_gfile_id = mp3_gdriveInput.gdrive_id
            txt_filename = mp3_filename[:-4] + '.txt'
            local_transcript_dir = Path(self.settings.local_transcript_dir)
            local_transcript_file_path = local_transcript_dir / txt_filename
            async with aiofiles.open(str(local_transcript_file_path), "w") as temp_file:
                await temp_file.write(str(transcript_text))
            folder_gdrive_id = self.settings.gdrive_transcripts_folder_id
            # returns the gfile id of the transcription file. We will add this to the next update_status so we are tracking within the
            # mp3 file where the corresponding transcript file is located (by gfile id).
            transcription_gfile_id = await self.upload(GDriveInput(gdrive_id=folder_gdrive_id),local_transcript_file_path)
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

    async def download_from_gdrive(self, gdrive_input:GDriveInput, dir: str):
        loop = asyncio.get_running_loop()
        def _download():
            try:
                gfile = self.drive.CreateFile({'id': gdrive_input.gdrive_id})
                gfile.FetchMetadata(fields="title")
                filename = gfile['title']
                local_file_path = Path(dir) / filename
                gfile.GetContentFile(str(local_file_path))  # Downloads the file
            except Exception as e:
                raise e
            return local_file_path
        try:
            local_file_path = await loop.run_in_executor(None, _download)
            return local_file_path
        except Exception as e:
            await self.tracker.handle_error(status=WorkflowEnum.ERROR,error_message=f'f{e}',operation='download_from_gdrive', store=False,raise_exception=True)

    async def list_files_to_transcribe(self, gdrive_folder_id: str) -> list:
        loop = asyncio.get_running_loop()
        def _get_file_info():
            # Assuming get_gfile_state is properly defined as an async function
            try:
                gfiles_to_transcribe_list = []
                query = f"'{gdrive_folder_id}' in parents and trashed=false"
                file_list = self.drive.ListFile({'q': query}).GetList()
                for file in file_list:
                    description = file.get('description', None)
                    if description:
                        state = json.loads(description)['state']
                        if state != WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name:
                            gfiles_to_transcribe_list.append(file)
                return gfiles_to_transcribe_list
            except Exception as e:
                raise e
            return file
        try:
            gfiles_to_transcribe = await loop.run_in_executor(None, _get_file_info)
            return gfiles_to_transcribe
        except Exception as e:
            await self.tracker.handle_error(status=WorkflowEnum.ERROR,error_message='f{e}',operation='list_files_to_transcribe', store=False,raise_exception=True)




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
