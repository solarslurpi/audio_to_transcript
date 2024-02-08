from enum import Enum, auto

class WorkflowStatus(Enum):
    NEW_TASK_TRANSCRIPTION = auto(), "A task id for transcription has been created."
    NEW_TASK_DOWNLOAD = auto(), "A task id for downloading a YouTube video has been created."
    IDTRACKED = auto(), "The task ID is being tracked."
    DOWNLOADING = auto(), "The YouTube audio is currently being downloaded."
    DOWNLOAD_FAILED = auto(), "The YouTube audio download failed."
    DOWNLOAD_COMPLETE = auto(), "The YouTube audio has been successfully downloaded."
    TRANSCRIBING = auto(), "Transcription is in progress."
    TRANSCRIBED = auto(), "Transcription has been completed."
    ERROR = auto(), "An error occurred during the workflow."
    VALIDATING = auto(), "The results are being validated."
    COMPLETED = auto(), "The workflow task has been completed."
    UNKNOWN = auto(), "The status of the task is unknown."

# define the value-description pairs as tuples, and the custom __new__ method handles the creation of new enum members. 
    def __new__(cls, value, description):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        return obj

    def as_dict(self):
        return {"code": self.value, "name": self.name, "description": self.description}
