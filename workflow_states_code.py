from enum import Enum

class WorkflowStates(Enum):
    START = ("start", "Workflow initiated")
    TRANSCRIPTION_STARTING = ("transcription_starting", "Transcription process starting")
    LOADING_MODEL = ("loading whisper model","loading whisper model")
    TRANSCRIBING = ("transcribing","transcribing")
    TRANSCRIPTION_FAILED = ("transcription_failed", "Transcription failed")
    TRANSCRIPTION_COMPLETE = ("transcription_complete", "Transcription completed successfully")
    TRANSCRIPTION_UPLOAD_COMPLETE = ("transcription upload complete", "Transcription file uploaded")
    ERROR = ("error", "An error occurred in the workflow")
    # Add other states as needed...

    @property
    def state_identifier(self):
        return self.value[0]

    @property
    def description(self):
        return self.value[1]

    def to_log_message(self, detail="", **kwargs):
        """Convert an enum state to a log message dictionary with a human-readable description."""
        base_message = {
            "flow_state": self.state_identifier,
            "description": self.description
        }

        if detail:
            base_message["detail"] = detail.format(**kwargs)
        
        return base_message

    def as_dict(self):
        """Return a dictionary representation of the status with formatted description."""
        return {
            "name": self.name,
            "description": self.value[1]
        }

