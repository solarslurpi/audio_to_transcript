from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import json
from pprint import pprint

class GDriveID(str,Enum):
    MP3_GDriveID = '1472rYLfk_V7ONqSEKAzr2JtqWyotHB_U',
    Transcription_GDriveID = "1ZyUDWlSQbnQSaoI9WTKxeqegUiREuQv6"

class TaskUnit(str,Enum):
    YOUTUBE_DOWNLOAD = 'youtube_download'
    TRANSCRIPTION = 'transcription'

class TaskStatus(BaseModel):
    # last_modified: datetime = Field(default_factory=datetime.now)
    # mp3_gdrive_id: GDriveID = Field(default=GDriveID.MP3_GDriveID)
    # transcription_gdrive_id: GDriveID = Field(default=GDriveID.Transcription_GDriveID)
    # mp3_gdrive_filename: Optional[str] = None
    # transcription_gdrive_filename: Optional[str] = None
    # transcription_audio_quality: Optional[str] = None
    # transcription_compute_type: Optional[str] = None
    # workflow_status: Optional[str] = None  # Adjust according to WorkflowStatus definition
    # description: Optional[str] = None
    # youtube_url: Optional[str] = None
    # current_id: Optional[str] = None
    current_task: Optional[str] = None

    class ConfigDict:
        use_enum_values = True
        # In order to serialize, we need a custom encoder for WorkflowStatus so that we return the name.


    @field_validator('current_task')
    @classmethod
    def task_type_must_be_valid(cls, v):
        if v not in (TaskUnit.YOUTUBE_DOWNLOAD, TaskUnit.TRANSCRIPTION):
            raise ValueError("current_task must be either 'youtube_download' or 'transcription'")
        return v
    
m = TaskStatus(current_task='youtube_download')
l = json.dumps(m)
l = m.model_dump()
pprint(l)

# l = json.dumps(m)