from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from settings_code import get_settings
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

class WorkflowStatusModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    last_modified: datetime = Field(default_factory=datetime.now)
    status: WorkflowStates = None
    mp3_gdrive_id: str = None
    mp3_gdrive_filename: Optional[str] = None
    comment: Optional[str] = None
    transcript_gdrive_id: str = None
    transcript_gdrive_filename: Optional[str] = None
    transcript_audio_quality: Optional[str] = None
    transcript_compute_type: Optional[str] = None
    # description: Optional[str] = None
    def dict(self, **kwargs):
        d = super().model_dump(**kwargs)
        d['last_modified'] = self.last_modified.isoformat()
        d['status'] = self.status.name
        return d

class YouTubeDownloadStatusModel(WorkflowStatusModel):
    youtube_url: Optional[str] = None

