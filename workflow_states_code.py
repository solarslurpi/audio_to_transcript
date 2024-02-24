from enum import Enum

class WorkflowStates(Enum):
    # WorkflowStatus.name = WorkflowStatus.value
    START = "The workflow ID {id} is being tracked."
    DOWNLOAD_STARTING = "The YouTube audio for workflow ID {id} is starting to be downloaded."
    DOWNLOADING = "The YouTube audio for workflow ID {id} is currently being downloaded."
    DOWNLOAD_FAILED = "The YouTube audio for workflow ID {id} download failed."
    DOWNLOAD_COMPLETE = "The YouTube audio for workflow ID {id} has been successfully downloaded."
    UPLOAD_COMPLETE = "The audio for workflow ID {id} has been successfully uploaded to Google Drive."
    TRANSCRIPTION_STARTING = "The transcription for workflow ID {id} is starting."
    TRANSCRIPTION_FAILED = "The transcription for workflow ID {id} failed."
    LOADING_MODEL = "loading_model"
    TRANSCRIBING = "Transcription for workflow ID {id} is in progress."
    TRANSCRIPTION_COMPLETE = "Transcription for workflow ID {id} has been completed."
    ERROR = "An error occurred for workflow ID {id} during the workflow."
    VALIDATING = "The results are being validated."
    COMPLETED = "The workflow for workflow ID {id} has been completed."
    UNKNOWN = "The status of the workflow ID {id} is unknown."

    # The values in the enum include a placeholder for the id.
    def format_description(self, id="(not provided)"):
        """Format the description to include the workflow ID."""
        return self.value.format(id=id)

    def as_dict(self, id="(not provided)"):
        """Return a dictionary representation of the status with formatted description."""
        return {
            "name": self.name,
            "description": self.format_description(id=id)
        }
    