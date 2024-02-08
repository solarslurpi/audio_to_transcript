
import hashlib
import logging
from abc import ABC, abstractmethod


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
    







