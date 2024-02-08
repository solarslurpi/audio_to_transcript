from enum import Enum, auto

class WorkflowStatus(Enum):
    # This approach allows both the system and the user to see the same (numbers <-> description)
    NEW = (auto(), "The task has been created.")
    IDTRACKED = (auto(), "The task ID is being tracked.")
    DOWNLOADING = (auto(), "The file is currently being downloaded.")
    DOWNLOADED = (auto(), "The file has been successfully downloaded.")
    TRANSCRIBING = (auto(),"Transcription is in progress.")
    TRANSCRIBED = (auto(), "Transcribed", "Transcription has been completed.")
    ERROR = (auto(), "An error occurred during the workflow.")
    VALIDATING = (auto(), "The results are being validated.")
    COMPLETED = (auto(),  "The workflow task has been completed.")

    def __init__(self, _value, name, description):
            self._value_ = _value
            self.name = name
            self.description = description

    def as_dict(self):
        return {"code": self.value, "name": self.name, "description": self.description}
    


# Example usage
update_task_status(task_id, WorkflowStatus.TRANSCRIBING, "Loading model base")

