from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from env_settings_code import get_settings
from dotenv import load_dotenv
from enum import Enum
from workflow_states_code import WorkflowStates
from datetime import datetime

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



# class YouTubeDownloadStatusModel(WorkflowStatusModel):
#     youtube_url: Optional[str] = None
