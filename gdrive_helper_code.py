# gdrive_manager.py
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os
from pathlib import Path
from workflow_states_code import WorkflowStates
from workflow_tracker_code import WorkflowTracker
from settings_code import get_settings
from logger_code import LoggerBase
import asyncio
import json
from googleapiclient.errors import HttpError
from typing import Optional


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

    async def get_filename(self,gfile_id:str) -> Optional[str]:
        try:
            file = self.drive.CreateFile({'id': gfile_id})
            file.FetchMetadata()
            return file['title']
        except Exception as e:
            return ''

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

    async def upload_to_gdrive(self, folder_GdriveID: str, file_path: str):
            '''
            
            args:
                folder_GdriveID represents the Google Drive ID for the folder where the
                file will be uploaded to. For example, if the code is uploading the
                transcript file, the folder_GdriveID is the GDrive ID of the Transcription folder.
            
            '''
            loop = asyncio.get_running_loop()
            
            def _upload():
                try:
                    gfile = self.drive.CreateFile({'parents': [{'id': folder_GdriveID}]})
                    gfile.SetContentFile(file_path)
                    gfile.Upload()
                    if hasattr(gfile, 'content') and gfile.content:
                        gfile.content.close()
                    os.remove(file_path)  # Optionally remove the local file after upload
                except Exception as e:
                    self.logger.error(f"Error uploading file to Google Drive: {e}")
                    raise GDriveFileOperationError(operation='upload', detail=file_path, system_error=e)
                return gfile['id']
            # Run the synchronous upload function in an executor
            self.tracker.work_flow_status.transcription_file_id = await loop.run_in_executor(None, _upload)


    async def download_from_gdrive(self, file_id: str, dir: str):
        loop = asyncio.get_running_loop()
        def _download():
            try:
                gfile = self.drive.CreateFile({'id': file_id})
                gfile.FetchMetadata(fields="title")
                filename = gfile['title']
                destination_path = Path(dir) / filename 
                gfile.GetContentFile(str(destination_path))  # Downloads the file
            except Exception as e:
                self.logger.error(f"Error downloading file from Google Drive: {e}")
                raise GDriveFileOperationError(operation='download', detail=file_id, system_error=e)
            return destination_path
        destination_path = await loop.run_in_executor(None, _download)
        return destination_path            
        

    async def update_transcription_status_in_gfile(self, gfile_id: str, transcription_info_dict:dict):
        loop = asyncio.get_running_loop()
        async def _update_transcription_gfile():
            try:
                file_to_update = self.drive.CreateFile({'id': gfile_id})
                # Take dictionary and make a json string with json.dumps()
                transcription_info_json = json.dumps(transcription_info_dict)
                # The transcription (workflow) status is placed as a json string within the gfile's description field.
                # This is not ideal, but using labels proved to be way too difficult?
                file_to_update['description'] = transcription_info_json
            except Exception as e:
                await self.tracker.handle_error(
                    status=WorkflowStates.ERROR, 
                    error_message=f"Could not update the transcription status on the gfile_id: {gfile_id}",
                    operation="update_transcription_status_in_gfile", 
                    store=False,
                    raise_exception=True
                )
            file_to_update.Upload()
        await loop.run_in_executor(None, _update_transcription_gfile)
    
    async def list_files_to_transcribe(self, gdrive_folder_id: str) -> list:
        loop = asyncio.get_running_loop()
        async def _get_file_info(file):
            # Assuming get_gfile_state is properly defined as an async function
            
            try:
                description = file.get('description', None)
                if description is None:
                    start_transcription_status_dict = {"id":file['id'], "comment":'', "state":WorkflowStates.START.name}
                    file = await self.update_transcription_gfile(start_transcription_status_dict)
                else:
                    state = json.loads(description)['state']
                    if state != WorkflowStates.TRANSCRIPTION_COMPLETE.name:
                        file = file
            except Exception as e:
                GDriveFileOperationError(operation='update_gfile_status', detail=f"Could not update the description field of the gfileid = {file['id']}", system_error=str(e))
            return file

        try:
            query = f"'{gdrive_folder_id}' in parents and trashed=false and mimeType='audio/mpeg'"
            file_list = await loop.run_in_executor(None, lambda: self.drive.ListFile({'q': query}).GetList())
            tasks = [_get_file_info(file) for file in file_list]
            files_with_info = await asyncio.gather(*tasks)
            return files_with_info
        except Exception as e:
            self.logger.error(f"Error listing files in folder {gdrive_folder_id}: {e}")
            raise GDriveFileOperationError(operation='list_files', detail=gdrive_folder_id, system_error=str(e))

# Ensure get_gfile_state and other functions called within _get_file_info are defined asynchronously.

        # def _get_filename():
        #     try:
        #         # Create a GoogleDriveFile instance with the provided file ID
        #         file = self.drive.CreateFile({'id': gdrive_id})
        #         # Fetch metadata for the file
        #         file.FetchMetadata(fields='title')
        #         # The title field contains the filename
        #         filename = file['title']
        #         return filename
        #     except Exception as e:
        #         self.logger.error(f"Error retrieving file metadata for file ID {gdrive_id}: {e}")
        #         raise GDriveFileOperationError(operation='retrieving filename', detail=f"could not retrieve the title (filename) metadata from the gdrive id: {gdrive_id}", system_error=e)
        #         # Run the synchronous upload function in an executor
        # filename = await loop.run_in_executor(None, _get_filename)
        # return filename
    
    async def validate_gdrive_access(self, folder_id:str) -> bool:
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self.drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false", 'maxResults': 1}).GetList())
            return True
        except Exception as e:
            raise GDriveFileOperationError(operation='validate', detail=folder_id, system_error=e)
            

