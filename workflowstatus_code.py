from enum import Enum

class WorkflowStatus(Enum):
    # WorkflowStatus.name = WorkflowStatus.value
    IDTRACKED = "The task ID {task_id} is being tracked."
    DOWNLOAD_STARTING = "The YouTube audio for task ID {task_id} is starting to be downloaded."
    DOWNLOADING = "The YouTube audio for task ID {task_id} is currently being downloaded."
    DOWNLOAD_FAILED = "The YouTube audio for task ID {task_id} download failed."
    DOWNLOAD_COMPLETE = "The YouTube audio for task ID {task_id} has been successfully downloaded."
    UPLOAD_COMPLETE = "The audio for task ID {task_id} has been successfully uploaded to Google Drive."
    LOADING_MODEL = "The T model used for task ID {task_id} is being loaded."
    TRANSCRIBING = "Transcription for task ID {task_id} is in progress."
    TRANSCRIPTION_COMPLETE = "Transcription for task ID {task_id} has been completed."
    ERROR = "An error occurred for task ID {task_id} during the workflow."
    VALIDATING = "The results are being validated."
    COMPLETED = "The workflow for task ID {task_id} has been completed."
    UNKNOWN = "The status of the task ID {task_id} is unknown."

    # The values in the enum include a placeholder for the task_id.
    def format_description(self, task_id="(not provided)"):
        """Format the description to include the task ID."""
        return self.value.format(task_id=task_id)

    def as_dict(self, task_id="(not provided)"):
        """Return a dictionary representation of the status with formatted description."""
        return {
            "name": self.name,
            "description": self.format_description(task_id=task_id)
        }
