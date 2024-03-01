from enum import Enum

from pydantic import BaseModel, field_validator


class WorkflowEnum(Enum):
    START = ("start", "Workflow initiated")
    TRANSCRIPTION_STARTING = ("transcription_starting", "Transcription process starting")
    LOADING_MODEL = ("loading whisper model","loading whisper model")
    TRANSCRIBING = ("transcribing","transcribing")
    TRANSCRIPTION_FAILED = ("transcription_failed", "Transcription failed")
    TRANSCRIPTION_COMPLETE = ("transcription_complete", "Transcription completed successfully")
    TRANSCRIPTION_UPLOAD_STARTING = ("transcription upload starting", "Transcription file upload starting")
    TRANSCRIPTION_UPLOAD_COMPLETE = ("transcription upload complete", "Transcription file uploaded")
    ERROR = ("error", "An error occurred in the workflow")
    UNKNOWN = ("unknown", "unknown")

    @classmethod
    def match_value(cls, value):
        # Using next with a generator expression to simplify the loop
        # and using the __members__.items() to iterate through enum members
        return next((member for name, member in cls.__members__.items() if member.value[0] == value), None)

class WorkflowStates(BaseModel):

    status: WorkflowEnum

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if not isinstance(v, WorkflowEnum):
            raise ValueError("status must be a member of the WorkflowEnums")
        return v

    @classmethod
    def validate_state(cls,v):
        # If v is already an instance of WorkflowEnum, return it directly
        if isinstance(v, WorkflowEnum):
            return v
        matched_member = WorkflowEnum.match_value(v)
        if matched_member:
            return matched_member
        raise ValueError(f"No match for: {v}")
