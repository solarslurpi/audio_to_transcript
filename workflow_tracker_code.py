import asyncio
from typing import Optional
from enum import Enum
from threading import Lock
from logger_code import LoggerBase  # Adjust this import as necessary
from workflow_status_model import WorkflowStatusModel  # Adjust this import as necessary
from workflow_states_code import WorkflowStates  # Adjust this import as necessary

from workflow_error_code import WorkflowOperationError  # Adjust this import as necessary
import json
from functools import wraps
import inspect

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
            self.store_error = None

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

        # Append the count to the state name for uniqueness
        state_with_count = f"{state.name}-{self._state_counts[state.name]}"
        log_message = {"state": state.name, "comment":comment, "count": self._state_counts[state.name]}

        # Log the message with the state count appended
        self.logger.flow(json.dumps(log_message))


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

        if store or self.store_error:
            if not self._mp3_gfile_id:
                await self.handle_error(status=WorkflowStates.ERROR,error_message='Option was to store the status. However, the mp3_file_id property is not set.',operation="update_status")
            try:
                await self._update_transcription_status_in_mp3_gfile(self._mp3_gfile_id)
            except Exception as e:
                err_msg = f"Could not update the mp3 gfile's metadata.  Error: {e}"
                await self.handle_error(
                status=WorkflowStates.TRANSCRIPTION_FAILED, 
                error_message=err_msg,
                operation="update_status", 
                store=False,
                raise_exception=False,
                update_status = False # Perhaps poor design.  If set to true, will go into a non-stop recursion...
            )
        await self._notify_status_change()


    def async_error_handler(status=WorkflowStates.ERROR, error_message= None ,store=False, raise_exception=True, update_status=True):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except WorkflowException as we:
                    self = args[0]  # Assuming the first argument is always 'self'
                    caller_frame = inspect.stack()[1]
                    operation = caller_frame.function  # Dynamically get the name of the parent method.
                    await self.tracker.handle_error(
                        status=we.status, 
                        error_message=str(we) or "An error occurred", 
                        operation=operation, 
                        store=we.store, 
                        raise_exception=we.raise_exception, 
                        update_status=we.update_status
                    )
                except Exception as e:
                    self = args[0]  # Assuming the first argument is always 'self'
                    evolved_error_message =  str(e) if not error_message else error_message                   
                    caller_frame = inspect.stack()[1]
                    operation = caller_frame.function  # Dynamically get the name of the parent method. 
                    # We're transcribing, but there was a failure. We should have the mp3 gfile and we should store this state.
                    if args[1] == WorkflowStates.TRANSCRIPTION_FAILED.name:
                        store_state = True
                    else:
                        store_state = store
                    # Call the instance's handle_error method with the captured exception details
                    await self.tracker.handle_error(status=status, error_message=evolved_error_message, operation=operation, store=store_state, raise_exception=raise_exception, update_status=update_status)
                    # No need to re-raise, handle_error will decide based on raise_exception parameter
            return wrapper
        return decorator

    async def handle_error(self, status:Enum=None, error_message: str=None, operation: str=None,store=False,raise_exception=True,update_status=False):
        # Default to WorkflowStates.ERROR if no status is provided
        error_status = WorkflowStates.ERROR if not status else status
        detailed_error_message = f"Error during {operation}: {error_message}" if operation else error_message
        self.logger.error(detailed_error_message)
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


    async def _update_transcription_status_in_mp3_gfile(self,gfile_id:str):
        from gdrive_helper_code import GDriveHelper  
        
        try:
            transcription_info_dict = self.make_status_dict(
                id=self.workflow_status_model.transcript_gdrive_id or '',
                state=self.workflow_status_model.status,
                comment=self.workflow_status_model.comment
            )
            # Assuming `update_transcription_gfile` is an async method within `GDriveHelper`
            gh =  GDriveHelper()
            self.logger.debug(f"Flow: Updating transcription status on the gfile id: {gfile_id}")
            await gh.update_transcription_status_in_gfile(gfile_id, transcription_info_dict)
            self.logger.info("Transcription info stored successfully.")
        except Exception as e:
            error_msg = f"Failed to store transcription info: {e}"
            self.logger.error(error_msg)
            raise WorkflowOperationError(operation='store_transcription_info', detail=error_msg, system_error=str(e))
        return transcription_info_dict
