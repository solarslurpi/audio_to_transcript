from enum import Enum, auto

class WorkflowStatus(Enum):
    IDTRACKED = (auto(), "The task ID {task_id} is being tracked.")
    DOWNLOADING = (auto(), "The YouTube audio for task ID {task_id} is currently being downloaded.")
    DOWNLOAD_FAILED = (auto(), "The YouTube audio for task ID {task_id} download failed.")
    DOWNLOAD_COMPLETE = (auto(), "The YouTube audio for task ID {task_id} has been successfully downloaded.")
    UPLOAD_COMPLETE = (auto(), "The YouTube audio for task ID {task_id} has been successfully uploaded to Google Drive.")
    TRANSCRIBING = (auto(), "Transcription for task ID {task_id} is in progress.")
    TRANSCRIBED = (auto(), "Transcription for task ID {task_id} has been completed.")
    ERROR = (auto(), "An error occurred for task ID {task_id} during the workflow.")
    VALIDATING = (auto(), "The results are being validated.")
    COMPLETED = (auto(), "The workflow for task ID {task_id} has been completed.")
    UNKNOWN = (auto(), "The status of the task ID {task_id} is unknown.")

    def __init__(self, _value, description):
        self._value_ = _value
        self.description = description

    def format_description(self, task_id="(not provided)"):
        """Format the description to include the task ID."""
        return self.description.format(task_id=task_id)

    def as_dict(self, task_id="(not provided)"):
        """Return a dictionary representation of the status with formatted description."""
        return {
            "code": self.value,
            "name": self.name,
            "description": self.format_description(task_id=task_id)
        }
