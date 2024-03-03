
from workflow_tracker_code import WorkflowTracker
from workflow_states_code import WorkflowEnum

def test_update_success():
    # Update the WorkflowTracker
    WorkflowTracker.update(
        status=WorkflowEnum.START,
        comment="Starting transcription",
        mp3_gdrive_id="12345"
    )

    # Retrieve the updated model
    updated_model = WorkflowTracker.get_model()

    # Assertions to ensure the update was successful
    assert updated_model.status == WorkflowEnum.START
    assert updated_model.comment == "Starting transcription"
    assert updated_model.mp3_gdrive_id == "12345"

    # Print the model for visual confirmation (optional)
    print(updated_model.model_dump())
    print(updated_model.status)
