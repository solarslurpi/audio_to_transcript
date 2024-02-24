import asyncio
from typing import Optional
from enum import Enum
from threading import Lock
from logger_code import LoggerBase  # Adjust this import as necessary
from workflow_status_model import WorkflowStatusModel  # Adjust this import as necessary
from workflow_states_code import WorkflowStates  # Adjust this import as necessary

from workflow_error_code import WorkflowOperationError  # Adjust this import as necessary

class WorkflowTracker:
    """
    A singleton class designed to track and manage the statuses of tasks within a transcription workflow across the application.
    This ensures that only one WorkflowStatus object is shared across the tasks.
    """
    _instance = None
    _lock = Lock()
    logger = LoggerBase.setup_logger('WorkflowTracker')

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


    def make_status_dict(self, id: str, state: str, comment: Optional[str] = None):
        return {
            "transcriptionId": id,
            "comment": comment,
            "state": state
        }

    async def update_status(self, state: Enum = None, comment: Optional[str] = None, transcript_gdriveid: Optional[str] = None, store: bool = False):
        async def _validate_state():
            if not isinstance(state, WorkflowStates):
                return False
            return True
        
        is_valid = await _validate_state()
        if not is_valid:
            self.logger.debug(f"Check of a valid stated: {state.name} did not pass.  returning")
            return  # Exit the method early if the state is not valid
        self.logger.debug(f"Check of a valid state passed in: {state.name} passed.")
        # Proceed with updating the status only if the state is valid
        self.workflow_status_model.status = state.name
        self.workflow_status_model.comment = comment
        self.workflow_status_model.transcript_gdrive_id = transcript_gdriveid


        if store:
            try:
                await self._update_transcription_status_in_mp3_gfile()
            except Exception as e:
                await self.handle_error(
                status=WorkflowStates.TRANSCRIPTION_FAILED, 
                error_message=f"Could not update the mp3 gfile's metadata.  Error: {e}",
                operation="update_status", 
                store=False,
                raise_exception=False,
                update_status = False
            )
        await self._notify_status_change()

    async def handle_error(self, status:Enum=None, error_message: str=None, operation: str=None,store=False,raise_exception=False,update_status=True):
        # Default to WorkflowStates.ERROR if no status is provided
        error_status = WorkflowStates.ERROR if not status else status
        detailed_error_message = f"Error during {operation}: {error_message}" if operation else error_message
        if update_status:
            await self.update_status(state=error_status, comment=detailed_error_message,store=store)
        # If raise_exception is True, raise a custom exception after logging and updating the status
        if raise_exception:
            exception_message = detailed_error_message if detailed_error_message else "An error occurred."
            raise Exception(exception_message)

    async def _notify_status_change(self):
        # self.event_tracker.set()
        # await asyncio.sleep(0.1)  # Simulation of an asynchronous operation
        # self.event_tracker.clear()
        # self.logger.info(f"Status changed to {self.workflow_status.status}")
        pass


    async def _update_transcription_status_in_mp3_gfile(self):
        from gdrive_helper_code import GDriveHelper  # Adjust this import as necessary
        try:
            transcription_info_dict = self.make_status_dict(
                id=self.workflow_status_model.transcript_gdrive_id or '',
                state=self.workflow_status_model.status,
                comment=self.workflow_status_model.comment
            )
            # Assuming `update_transcription_gfile` is an async method within `GDriveHelper`
            gh =  GDriveHelper()
            await gh.update_transcription_status_in_gfile(self.workflow_status_model.mp3_gdrive_id, transcription_info_dict)
            self.logger.info("Transcription info stored successfully.")
        except Exception as e:
            error_msg = f"Failed to store transcription info: {e}"
            self.logger.error(error_msg)
            raise WorkflowOperationError(operation='store_transcription_info', detail=error_msg, system_error=str(e))
        return transcription_info_dict
