
import hashlib
import logging
from enum import Enum, auto
from abc import ABC, abstractmethod
from pydrive2.auth import GoogleAuth

class TranscriptionTracker(ABC):


    def __init__(self):
        pass # Assumes we have been authenticated by GDrive by the caller.

    @abstractmethod
    def is_duplicate(self, file_info):
        pass

    def add_file(self, file):
        '''
        Add a file to the tracker.  If the file is already in the tracker...
        '''
        file_info = self._generate_file_info(file)
        if not self.is_duplicate(file_info):
            self.store_file_info(file_info)
            return file_info
        else:
            return None

    @abstractmethod
    def get_file_info_list(self):
        pass

    @abstractmethod
    def update_status(self, file_id, status):
        pass

    @abstractmethod
    def remove_file(self, file_id):
        pass

    def _generate_file_info(self, file):
        try:
            return {
                'name': file['title'],
                'id': file['id'],
                'status': TranscriptionTracker.WorkflowStatus.NEW
            }
        except Exception as e:
            logging.error(f"Error generating file info for {file['title']}: {e}")
            return None

    @abstractmethod
    def store_file_info(self, file_info):
        pass
    
    @staticmethod
    def compute_hash(file_path):
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
    

    @staticmethod
    def login_with_service_account():
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
                    "service_config": {
                        "client_json_file_path": "service-account-creds.json",
                    }
                }
        # Create instance of GoogleAuth
        gauth = GoogleAuth(settings=settings)
        # Authenticate
        gauth.ServiceAuth()
        return gauth





