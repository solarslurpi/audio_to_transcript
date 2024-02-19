
import asyncio
from threading import Lock
from datetime import datetime
from logger_code import LoggerBase
from workflow_status_model import TranscriptionStatus
from workflow_states_code import WorkflowStates

from workflow_error_code import WorkflowOperationError


class WorkflowTracker:
    """
    A singleton class designed to track and manage the statuses of tasks within a transcrition workflow across the application.
    This way, only one WorkflowStatus object is shared across the tasks.

    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance
    def __init__(self):
        if not hasattr(self, 'initialized'):  # Prevent re-initialization
            self.workflow_status = TranscriptionStatus(status=WorkflowStates.IDTRACKED)
            self.initialized = True
            self.logger = LoggerBase.setup_logger()
            self.event_tracker = asyncio.Event()

    async def update_status(self,store=True):
        try:
            # Get the singleton WorkflowSatus so we can send the SSE event and store it.

            self.workflow_status.last_modified = datetime.now()
            # Load existing status records.
            if store:
                from file_tracker_store_code import FileTrackerStore
                ft = FileTrackerStore()
                await ft.update_status_in_store()
        except Exception as e:
            self.logger.error(f"Failed to update task status: {e}")
            raise WorkflowOperationError(operation='update_task_status', detail=self.workflow_status, system_error=e)

        # Optionally, notify about the status update (can be implemented based on specific needs)
        await self.notify_status_change()

    async def notify_status_change(self):
        # Logic to notify subscribers via SSE about the status change
        self.event_tracker.set()
        await asyncio.sleep(0.1)  # Ensure the event is processed
        self.event_tracker.clear()



