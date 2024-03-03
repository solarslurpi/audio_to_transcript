import asyncio
from uuid import uuid4
from enum import Enum
import os
from datetime import datetime
from dotenv import load_dotenv
from settings_code import get_settings
from logger_code import LoggerBase

# Assuming WorkflowStatus, LoggerBase, and other necessary imports are defined elsewhere
load_dotenv()
settings = get_settings()
        
class GDriveID(str, Enum):
    MP3_GDriveID = settings.gdrive_mp3_folder_id
    Transcription_GDriveID = settings.gdrive_transcripts_folder_id

class TaskUnit(str, Enum):
    YOUTUBE_DOWNLOAD = 'youtube_download'
    TRANSCRIPTION = 'transcription'

class TaskStatus:
    def __init__(self, current_task, mp3_gdrive_id=None, transcription_gdrive_id=None):
        self.task_id = str(uuid4())
        self.current_task = current_task
        self.mp3_gdrive_id = mp3_gdrive_id or GDriveID.MP3_GDriveID
        self.transcription_gdrive_id = transcription_gdrive_id or GDriveID.Transcription_GDriveID
        self.mp3_gdrive_filename = None
        self.transcription_gdrive_filename = None
        self.transcription_audio_quality = None
        self.transcription_compute_type = None
        self.workflow_status = WorkflowStatus.UNKNOWN
        self.description = None
        self.youtube_url = None
        self.last_modified = datetime.now()

class StatusManager:
    def __init__(self, event_tracker):
        self.logger = LoggerBase.setup_logger()
        self.event_tracker = event_tracker
        self.statuses = {}

    async def update_task_status(self, task_status: TaskStatus, status: WorkflowStatus, message: str = ''):
        task_status.workflow_status = status
        task_status.description = status.format_description(task_id=task_status.task_id) + "-" + message
        self.statuses[task_status.task_id] = task_status
        self.logger.info(f"Status Updated: {task_status.description}")
        await self.notify_status_change(task_status.task_id)

    async def notify_status_change(self, task_id: str):
        self.event_tracker.set()
        await asyncio.sleep(0.1)
        self.event_tracker.clear()

class TaskStatusManager(StatusManager):
    def __init__(self, event_tracker, store):
        super().__init__(event_tracker)
        self.store = store

    async def start_task_tracking(self, current_task: TaskUnit):
        task_status = TaskStatus(current_task=current_task.value)
        await self.update_task_status(task_status, WorkflowStatus.IDTRACKED, "Task tracking started")
        return task_status

    async def create_task_id(self, task_status: TaskStatus):
        # Example: Create a GDrive file and update task_status with the file ID
        pass

# Example usage
async def main():
    event_tracker = asyncio.Event()
    task_manager = TaskStatusManager(event_tracker, store={})
    task_status = await task_manager.start_task_tracking(TaskUnit.YOUTUBE_DOWNLOAD)
    await task_manager.create_task_id(task_status)

if __name__ == "__main__":
    asyncio.run(main())