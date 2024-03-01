import asyncio
from typing import Optional
from enum import Enum
from threading import Lock


import json

from logger_code import LoggerBase  # Adjust this import as necessary
from workflow_status_model import WorkflowStatusModel  # Adjust this import as necessary
from workflow_states_code import WorkflowStates  # Adjust this import as necessary
from gdrive_helper_code import GDriveHelper
from workflow_error_code import async_error_handler, handle_error




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
            self.workflow_status_model = WorkflowStatusModel()
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

    @async_error_handler(status=WorkflowStates.ERROR)
    async def update_status(
    self,
    state: Enum = None,
    comment: Optional[str] = None,
    transcript_gdriveid: Optional[str] = None,
    store: Optional[bool] = None,
    ):
        async def _validate_state():
            if not isinstance(state, WorkflowStates):
                return False
            return True

        is_valid = await _validate_state()
        msg = "A call was made to update_status. "
        if not is_valid:
            self.logger.debug(msg + f"Check of a valid state: {state.name} did not pass.  Returning.")
            return  # Exit the method early if the state is not valid
        self.logger.debug(msg + f"Check of a valid state passed in: {state.name}.")
        self._log_flow_state(state, comment)
        # Proceed with updating the status only if the state is valid
        self.workflow_status_model.status = state.name
        self.workflow_status_model.comment = comment
        self.workflow_status_model.transcript_gdrive_id = transcript_gdriveid

        if store:
            if not self._mp3_gfile_id:
                await handle_error(status=WorkflowStates.ERROR,error_message='Option was to store the status. However, the mp3_file_id property is not set.',operation="update_status",raise_exception=False)
            await self.gh.update_transcription_status_in_mp3_gfile(self._mp3_gfile_id)
        await self._notify_status_change()

    async def _notify_status_change(self):
        # self.event_tracker.set()
        # await asyncio.sleep(0.1)  # Simulation of an asynchronous operation
        # self.event_tracker.clear()
        # self.logger.info(f"Status changed to {self.workflow_status.status}")
        pass

    @async_error_handler(status=WorkflowStates.ERROR)
    async def update_transcription_status_in_mp3_gfile(self, gfile_input: GDriveInput, transcription_info_dict:dict) -> None:
        loop = asyncio.get_running_loop()
        def _update_transcription_status():
            gfile_id = gfile_input.gdrive_id
            from gdrive_helper_code import GDriveHelper
            file_to_update = self.drive.CreateFile({'id': gfile_id})
            # Take dictionary and make a json string with json.dumps()
            transcription_info_json = json.dumps(transcription_info_dict)
            # The transcription (workflow) status is placed as a json string within the gfile's description field.
            # This is not ideal, but using labels proved to be way too difficult?
            file_to_update['description'] = transcription_info_json
            file_to_update.Upload()
        await loop.run_in_executor(None, _update_transcription_status)