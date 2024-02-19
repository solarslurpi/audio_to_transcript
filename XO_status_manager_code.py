import asyncio
from uuid import uuid4
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

from workflow_states_code import WorkflowStatus
from logger_code import LoggerBase
from settings_code import get_settings
from gdrive_helper_code import GDriveHelper
from file_transcription_tracker import FileTranscriptionTracker

# Load environment variables and settings
load_dotenv()
settings = get_settings()

class GDriveID(str, Enum):
    MP3_GDriveID = settings.gdrive_mp3_folder_id
    Transcription_GDriveID = settings.gdrive_transcripts_folder_id

class TaskUnit(str, Enum):
    YOUTUBE_DOWNLOAD = 'youtube_download'
    TRANSCRIPTION = 'transcription'
    MONITOR = 'monitor'

class TaskStatus(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_status: WorkflowStatus = WorkflowStatus.UNKNOWN
    description: Optional[str] = None
    last_modified: datetime = Field(default_factory=datetime.now)

class YouTubeDownloadStatus(TaskStatus):
    youtube_url: Optional[str] = None
    mp3_gdrive_id: GDriveID = GDriveID.MP3_GDriveID
    mp3_gdrive_filename: Optional[str] = None

class TranscriptionStatus(YouTubeDownloadStatus):
    transcription_gdrive_id: GDriveID = GDriveID.Transcription_GDriveID
    transcription_gdrive_filename: Optional[str] = None
    transcription_audio_quality: Optional[str] = None
    transcription_compute_type: Optional[str] = None

class MonitorStatus(TaskStatus):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = LoggerBase.setup_logger()
        self.event_tracker = asyncio.Event()
        self.statuses = {}  # Dictionary to track task statuses

    async def update_task_status(self, task_id: str, new_status: WorkflowStatus, message: str = '', store: bool = True):
        # Check if task_id exists in statuses, update it, or add it if not exists
        if task_id not in self.statuses:
            self.statuses[task_id] = TaskStatus(task_id=task_id, workflow_status=new_status, description=message)
        else:
            task_status = self.statuses[task_id]
            task_status.workflow_status = new_status
            task_status.description = new_status.format_description(task_id=task_id) + " - " + message
            task_status.last_modified = datetime.now()

        self.logger.info(f"Task {task_id} status updated to {new_status.name}: {message}")

        if store:
            await self.update_store(task_id)

        # Optionally, notify about the status update (can be implemented based on specific needs)
        await self.notify_status_change(task_id)

    async def update_store(self, task_id: str):
        # Implement logic to persist the updated status to a database, file system, etc.
        # This might involve serializing self.statuses[task_id] and saving it
        self.logger.info(f"Task {task_id} status persisted to storage")

    async def notify_status_change(self, task_id: str):
        # Logic to notify subscribers via SSE about the status change
        self.event_tracker.set()
        await asyncio.sleep(0.1)  # Ensure the event is processed
        self.event_tracker.clear()

    async def check_status(self):
        # No input required because the status check is designed
        # to be based on the state of the system (files in GDRive
        # and the WorkflowStatus entries in the store).
        async def fetch_mp3_and_task_list(gh):
            try:
                
                # Access GDrive to get a list of all mp3 files in the folder
                mp3_file_list = await gh.list_files_in_folder(GDriveID.MP3_GDriveID)
                # Access the store to get a list of tracked tasks
                store = FileTranscriptionTracker()
                task_status_list = store.load_task_status_list()
            except Exception as e:
                raise # TODO: Handle exceptions
            return mp3_file_list, task_status_list
        async def determine_tracked_and_untracked_mp3s(gh, mp3_file_list, task_status_list):
            # Reconcile the task_status_list with the mp3_file_list
            try:
                mp3_ids_in_status = set()
                mp3_ids_not_in_status = set()
                for status in task_status_list:
                    if status.mp3_gdrive_id in mp3_file_list:
                        mp3_ids_in_status.add(status.mp3_gdrive_id)
                    else:
                        mp3_ids_not_in_status.add(status.mp3_gdrive_id)
  
            except Exception as e:
                raise # TODO: Handle exceptions
            return mp3_ids_in_status, mp3_ids_not_in_status


        gh = GDriveHelper()
        mp3_files_list, task_status_list = await fetch_mp3_and_task_list(gh)
        mp3_ids_in_status, mp3_ids_not_in_status = await determine_tracked_and_untracked_mp3s(gh, mp3_files_list, task_status_list)






            # reconcile the task_status_list with the mp3_file_list. The task_status_list
            # has e.g.: { "mp3_gdrive_id": "string-gdrive-id",... as an entry.
            # Which mp3 ids in mp3_file_list match the ids within the task_status_list?
            # Which do not?
            # For those that are in the list, what is the status?  If it shows TRANSCRIPTION_COMPLETE, check that the transcription is in the Transcription
            # GDrive folder.  If the transcription is not there, update that TRANSCRIPTION_COMPLETE perhaps with a monitor status of TRANSCRIPTION_DELETED or TRANSCRIPTION_MOVEDF< whatever make the most sense to identify a transcription was made, but it is no longer in the transcription file and we have the mp3.  We could have a .env option or user entered option on monitoring to determine given this state, if we should regenerate the transcription or not.
            # Once the mp3 files with entries in the transcription store that is now in memory within the task_status_list, and the status is updated, now we can address mp3 files that are not tracked and begin the process of both tracking and transcribing the mp3 file.






async def main():
    # Example usage
    pass

if __name__ == "__main__":
    asyncio.run(main())
