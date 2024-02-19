# gdrive_manager.py
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os
from settings_code import get_settings
from logger_code import LoggerBase
import asyncio

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


    def _login_with_service_account(self):
        settings = get_settings()
        settings = {
            "client_config_backend": "service",
            "oauth_scope": settings.google_drive_oauth_scopes,
            "service_config": {
                "client_json_file_path":settings.google_service_account_credentials_path
            }
        }
        try:
            gauth = GoogleAuth(settings=settings)
            gauth.ServiceAuth()
            return gauth
        except Exception as e:
            self.logger.error(f"Failed to authenticate with Google Drive service account. Error: {e}")
            raise Exception(f"Authentication failed: {e}") from e

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
        return gfile['id']

    def delete_gdrive_file(self, file_id: str):
        try:
            file = self.drive.CreateFile({'id': file_id})
            file.Delete()
        except Exception as e:
            self.logger.error(f"Error deleting Google Drive file: {e}")
            raise GDriveFileOperationError(operation='delete', detail=file_id, system_error=e)

    async def upload_to_gdrive(self, folder_GdriveID: str, file_path: str):
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

            # Run the synchronous upload function in an executor
            await loop.run_in_executor(None, _upload)

    async def download_from_gdrive(self, file_id: str, dir: str):
        loop = asyncio.get_running_loop()
        def _download():
            try:
                gfile = self.drive.CreateFile({'id': file_id})
                gfile.FetchMetadata(fields="title")
                filename = gfile['title']
                destination_path = os.path.join(dir, filename)
                gfile.GetContentFile(destination_path)  # Downloads the file
            except Exception as e:
                self.logger.error(f"Error downloading file from Google Drive: {e}")
                raise GDriveFileOperationError(operation='download', detail=file_id, system_error=e)
            return destination_path
        destination_path = await loop.run_in_executor(None, _download)
        return destination_path            
        
    async def list_files_in_folder(self,gdrive_folder_id: str) -> list:
        loop = asyncio.get_running_loop()
        def _list_files():
            try:
                query = f"'{gdrive_folder_id}' in parents and trashed=false"
                file_list = self.drive.ListFile({'q': query}).GetList()
                return {file['id']: file['title'] for file in file_list}
            except Exception as e:
                raise GDriveFileOperationError(operation='list_files', detail=gdrive_folder_id, system_error=str(e))
        file_list = await loop.run_in_executor(None, _list_files)
        return file_list
    async def get_gdrive_filename(self, gdrive_id:str) -> str:
        loop = asyncio.get_running_loop()
        def _get_filename():
            try:
                # Create a GoogleDriveFile instance with the provided file ID
                file = self.drive.CreateFile({'id': gdrive_id})
                # Fetch metadata for the file
                file.FetchMetadata(fields='title')
                # The title field contains the filename
                filename = file['title']
                return filename
            except Exception as e:
                self.logger.error(f"Error retrieving file metadata for file ID {gdrive_id}: {e}")
                raise GDriveFileOperationError(operation='retrieving filename', detail=f"could not retrieve the title (filename) metadata from the gdrive id: {gdrive_id}", system_error=e)
                # Run the synchronous upload function in an executor
        filename = await loop.run_in_executor(None, _get_filename)
        return filename
    
    async def validate_gdrive_access(self, folder_id:str) -> bool:
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self.drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false", 'maxResults': 1}).GetList())
            return True
        except Exception as e:
            raise GDriveFileOperationError(operation='validate', detail=folder_id, system_error=e)
            

