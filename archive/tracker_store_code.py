
from abc import ABC, abstractmethod
from logger_code import LoggerBase

class TrackerStoreError(Exception):
    """Base class for Tracker tracking errors with a default error message."""
    def __init__(self, message=None, system_error=None):
        if message is None:
            message = "An error occurred with Google Drive operation."
        if system_error:
            message += f" Error: {system_error}"
        super().__init__(message)

class TrackerIOError(TrackerStoreError):
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


class TrackerStore(ABC):
    def __init__(self):
        self.logger = LoggerBase.setup_logger()
        
    @abstractmethod 
    def load_status_list(self):
        pass

    @abstractmethod
    def _add_status_to_store(self):
        pass

    @abstractmethod
    def update_status_in_store(self):
        pass









