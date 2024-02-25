from enum import Enum

class WorkflowStates(Enum):
    START = "start"
    DOWNLOAD_STARTING = "download_starting"
    DOWNLOADING = "downloading"
    DOWNLOAD_FAILED = "download_failed"
    DOWNLOAD_COMPLETE = "download_complete"
    UPLOAD_COMPLETE = "upload_complete"
    TRANSCRIPTION_STARTING = "transcription_starting"
    TRANSCRIPTION_FAILED = "transcription_failed"
    LOADING_MODEL = "loading_model"
    TRANSCRIPTION_UPLOAD_COMPLETE = "transcription upload complete"
    TRANSCRIBING = "transcribing"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    ERROR = "error"
    VALIDATING = "validating"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


    # The values in the enum include a placeholder for the id.
    # I was including a tracker id in the value but the id doesn't really help the caller.  It is totally internal.
    # def format_description(self, id="(not provided)"):
    #     """Format the description to include the workflow ID."""
    #     return self.value.format(id=id)

    def as_dict(self):
        """Return a dictionary representation of the status with formatted description."""
        return {
            "name": self.name,
            "description": self.value
        }
    