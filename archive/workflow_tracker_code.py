import asyncio
from typing import Optional
from enum import Enum
from threading import Lock


import json

from logger_code import LoggerBase  # Adjust this import as necessary
from workflow_states_code import WorkflowStates  # Adjust this import as necessary
from gdrive_helper_code import GDriveHelper
from workflow_error_code import async_error_handler
from pydantic_models import GDriveInput

class WorkflowException(Exception):
    def __init__(self, status=WorkflowStates.ERROR, error_message=None, store=False, raise_exception=True, update_status=True):
        super().__init__(error_message)
        self.status = status
        self.store = store
        self.raise_exception = raise_exception
        self.update_status = update_status

class WorkflowTracker:
    """
    A singleton class designed to track and manage the statuses of tasks within a transcription workflow across the application.
    This ensures that only one WorkflowStatus object is shared across the tasks.
    """
    _instance = None
    _lock = Lock()


    @classmethod
    # Always ask for the singleton with get_instance.
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    # Assume __init__ takes no arguments besides 'self'
                    instance.__init__()  # Initialize the instance.
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.event_tracker = asyncio.Event()
            self.logger = LoggerBase.setup_logger('WorkflowTracker')
            self._mp3_gfile_id = None
            self._mp3_gfile_name = None
            # Initialize a dictionary to track counts of logged states
            self._state_counts = {}
            self.gh = GDriveHelper

    @property
    def mp3_gfile_id(self):
        return self._mp3_gfile_id

    # Property decorator for setter
    @mp3_gfile_id.setter
    def mp3_gfile_id(self, value):
        self._mp3_gfile_id = value


    @property
    def mp3_gfile_name(self):
        return self._mp3_gfile_name

    # Property decorator for setter
    @mp3_gfile_name.setter
    def mp3_gfile_name(self, value):
        self._mp3_gfile_name = value

    def make_status_dict(self, id: str, state: str, comment: Optional[str] = None):
        return {
            "transcriptionId": id,
            "comment": comment,
            "state": state
        }



    def _log_flow_state(self, state: WorkflowStates, comment: str):
        # Increment the count for the given state, starting at 1 if it's the first time
        if state.name in self._state_counts:
            self._state_counts[state.name] += 1
        else:
            self._state_counts[state.name] = 1

        log_message = {"state": state.name, "comment":comment, "count": self._state_counts[state.name]}

        # Log the message with the state count appended
        self.logger.flow(json.dumps(log_message))
