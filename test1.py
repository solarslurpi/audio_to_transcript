from enum import Enum

class WorkflowStates(Enum):
    TRANSCRIPTION_FAILED = "The transcription failed."



# Validate if 'state' is a member of 'WorkflowStates'
if isinstance(state, WorkflowStates):
    print(f"{state.name} is a valid member of WorkflowStates.")
else:
    print(f"{state.name} is not a valid member of WorkflowStates.")
