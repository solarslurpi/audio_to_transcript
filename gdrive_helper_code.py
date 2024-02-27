# gdrive_manager.py
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pathlib import Path
from workflow_states_code import WorkflowStates
from workflow_tracker_code import WorkflowTracker
from env_settings_code import get_settings
from logger_code import LoggerBase
import asyncio
import json
from googleapiclient.errors import HttpError
from typing import Optional
import aiofiles
from pydantic import BaseModel

class GDriveInput(BaseModel):
    gdrive_id: str

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
        self.tracker = WorkflowTracker.get_instance()
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
                status=WorkflowStates.TRANSCRIPTION_FAILED, 
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

    async def upload_mp3_to_gdrive(self, mp3_file_path:Path):
        folder_gdrive_id = self.settings.gdrive_mp3_folder_id
        # Returns the gfile id of the mp3 file.
        return await self.upload(folder_gdrive_id, mp3_file_path)
    
    async def upload_transcript_to_gdrive(self, transcript_text: str):
        try:
            mp3_filename = self.tracker.mp3_gfile_name
            if not mp3_filename:
                await self.tracker.handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED,error_message="The mp3 filename is None, which means we don't have a name for our transcription document.", operation='upload_transcript_to_gdrive', store=True,raise_exception=True)
            if mp3_filename.endswith('.mp3'):
                txt_filename = mp3_filename[:-4] + '.txt'
            local_transcript_dir = Path(self.settings.local_transcript_dir)
            local_transcript_file_path = local_transcript_dir / txt_filename
            async with aiofiles.open(str(local_transcript_file_path), "w") as temp_file:
                await temp_file.write(transcript_text)
            folder_gdrive_id = self.settings.gdrive_transcripts_folder_id
            # returns the gfile id of the transcription file.
            transcription_gfile_id = await self.upload(folder_gdrive_id,local_transcript_file_path)
            store = False if not self.tracker.mp3_gfile_id else True
            await self.tracker.update_status(state=WorkflowStates.TRANSCRIPTION_UPLOAD_COMPLETE, comment='Adding the transcription gfile tracker id', transcript_gdriveid= transcription_gfile_id, store=store)
        except Exception as e:
            await self.tracker.handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED,error_message=f'Something is not right when trying to upload the transcript...{e}.',operation='GDriveHelper.upload_transcript_to_gdrive', store=True,raise_exception=True)
    
    async def upload(self, folder_gdrive_id:str, file_path: Path):
        try:
            gfile = self.drive.CreateFile({'parents': [{'id': folder_gdrive_id}]})
            gfile.SetContentFile(str(file_path))
            gfile.Upload()
            if hasattr(gfile, 'content') and gfile.content:
                gfile.content.close()
            #  TODO: Can remove the local transcript...
        except Exception as e:
            err_msg = f"Could not upload the file {file_path.name} to GDrive folder ID: {folder_gdrive_id}. {e}",
            await self.tracker.handle_error(status=WorkflowStates.ERROR,error_message=err_msg,operation="upload",raise_exception=True)
        return gfile['id']

    async def download_from_gdrive(self, file_id: str, dir: str):
        loop = asyncio.get_running_loop()
        def _download():
            try:
                gfile = self.drive.CreateFile({'id': file_id})
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
            await self.tracker.handle_error(status=WorkflowStates.ERROR,error_message=f'f{e}',operation='download_from_gdrive', store=False,raise_exception=True)
    
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
                        if state != WorkflowStates.TRANSCRIPTION_UPLOAD_COMPLETE.name:
                            gfiles_to_transcribe_list.append(file)
                return gfiles_to_transcribe_list
            except Exception as e:
                raise e
            return file
        try:
            gfiles_to_transcribe = await loop.run_in_executor(None, _get_file_info)
            return gfiles_to_transcribe 
        except Exception as e:
            await self.tracker.handle_error(status=WorkflowStates.ERROR,error_message='f{e}',operation='list_files_to_transcribe', store=False,raise_exception=True)
                
    async def update_transcription_status_in_gfile(self, gfile_id: str, transcription_info_dict:dict):
        loop = asyncio.get_running_loop()
        def _update_transcription_status():
            try:
                file_to_update = self.drive.CreateFile({'id': gfile_id})
                # Take dictionary and make a json string with json.dumps()
                transcription_info_json = json.dumps(transcription_info_dict)
                # The transcription (workflow) status is placed as a json string within the gfile's description field.
                # This is not ideal, but using labels proved to be way too difficult?
                file_to_update['description'] = transcription_info_json
                file_to_update.Upload()
            except Exception as e:
                raise e
        try:        
            await loop.run_in_executor(None, _update_transcription_status)
        except Exception as e:
            err_msg = f"Could not update the transcription status on the gfile_id: {gfile_id}",
            await self.tracker.handle_error(

                status=WorkflowStates.ERROR, 
                error_message=err_msg,
                operation="update_transcription_status_in_gfile", 
                store=False,
                raise_exception=True
            )
    
    async def get_filename(self,gfile_id:str) -> str:
        loop = asyncio.get_running_loop()
        def _get_filename():
            try:
                file = self.drive.CreateFile({'id': gfile_id})
                # Fetch the filename from the metadata
                file.FetchMetadata(fields='title')
                filename = file['title']
                return filename
            except Exception as e:
                raise e
        try:
            filename = await loop.run_in_executor(None, _get_filename)
        except Exception as e:
            err_msg = f"Error retrieving file metadata for file ID {gfile_id}: {e}"
            await self.tracker.handle_error(
                status=WorkflowStates.ERROR, 
                error_message=err_msg,
                operation="GDriveHelper.get_filename", 
                store=False,
                raise_exception=True
            )            
            return filename
        
    async def fetch_transcription_status_dict(self,gfile_id:str):
        loop = asyncio.get_running_loop()
        def _fetch_transcription_status_dict():
            try:
                gfile = self.drive.CreateFile({'id': gfile_id})
                gfile.FetchMetadata(fields="description")
                transcription_status_json = gfile['description']
                if transcription_status_json:
                    return json.loads(transcription_status_json)
                else:
                    return None
            except Exception as e:
                raise e
        try:
            transcription_status_json = await loop.run_in_executor(None, _fetch_transcription_status_dict)  
            self.logger.debug(f"The transcription status dict is {transcription_status_json} given gfile_id: {gfile_id}")       
            return transcription_status_json
        except Exception as e:
            await self.tracker.handle_error(status=WorkflowStates.ERROR,error_message=f'Could not fetch the transcription status from the description field of the gfile: {gfile_id}. Error: {e}',  operation='GDriveHelper.fetch_transcription_status_dict', store=False,raise_exception=True)
            

            
