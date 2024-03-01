from uuid import uuid4
from datetime import datetime
from typing import Optional
from enum import Enum
from threading import Lock
from pydantic import BaseModel,Field


from workflow_states_code import WorkflowStates  # Adjust this import as necessary

class WorkflowTrackerModel(BaseModel):
    status: WorkflowStates = None
    mp3_gdrive_id: str = None
    mp3_gdrive_filename: Optional[str] = None
    comment: Optional[str] = None
    transcript_gdrive_id: str = None
    transcript_gdrive_filename: Optional[str] = None
    transcript_audio_quality: Optional[str] = None
    transcript_compute_type: Optional[str] = None

class WorkflowTracker:
    _model = WorkflowTrackerModel()

    @classmethod
    def update(cls, **kwargs):
    # EG: WorkflowTracker.update(status=WorkflowEnum.TRANSCRIPTION_COMPLETE, comment="Job startedSuccess!,
        for key, value in kwargs.items():
            if hasattr(cls._model, key):
                setattr(cls._model, key, value)

    @classmethod
    def get(cls, field_name):
        if hasattr(cls._model, field_name):
            return getattr(cls._model, field_name, None)
        else:
            # Optional: handle the case where the field name is not valid
            return None  # Or consider raising an error


    @classmethod
    def __call__(cls, **kwargs):
        cls.update(**kwargs)
        return cls._model

    @classmethod
    def get_model(cls):
        return cls._model

    @classmethod
    def get_model_dump(cls):
        return cls._model.model_dump()
