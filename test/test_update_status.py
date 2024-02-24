import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from workflow_tracker_code import WorkflowTracker
from workflow_states_code import WorkflowStates

@pytest.mark.asyncio
@patch('workflow_tracker_code.WorkflowTracker._notify_status_change', new_callable=AsyncMock)
@patch('workflow_tracker_code.WorkflowTracker._update_transcription_status_in_mp3_gfile', new_callable=AsyncMock)
async def test_update_status_success(mock_update_gfile, mock_notify_change):
    """
    Test the successful path of WorkflowTracker.update_status.
    This test ensures that when provided with valid state, comment, and GDrive ID,
    the method updates the workflow_status_model accordingly and calls the necessary
    methods to reflect these changes.
    """
    tracker = WorkflowTracker.get_instance()
    state = WorkflowStates.DOWNLOAD_COMPLETE
    comment = "Download complete for workflow ID {id}."
    gdrive_id = "some-gdrive-id"
    
    await tracker.update_status(state=state, comment=comment, transcript_gdriveid=gdrive_id, store=True)
    
    assert tracker.workflow_status_model.status == state
    assert tracker.workflow_status_model.comment == comment
    assert tracker.workflow_status_model.transcript_gdrive_id == gdrive_id
    mock_update_gfile.assert_awaited_once()
    mock_notify_change.assert_awaited_once()

@pytest.mark.asyncio
@patch('workflow_tracker_code.WorkflowTracker._notify_status_change', new_callable=AsyncMock)
@patch('workflow_tracker_code.WorkflowTracker._update_transcription_status_in_mp3_gfile', new_callable=AsyncMock)
async def test_update_status_failure(mock_update_gfile, mock_notify_change):
    """
    Test the failure path of WorkflowTracker.update_status by providing an invalid state.
    This test checks that the system does not update the workflow_status_model for an invalid state
    and logs an appropriate warning. It also ensures that _update_transcription_status_in_mp3_gfile
    and _notify_status_change are not called.
    """
    tracker = WorkflowTracker.get_instance()
    invalid_state = "INVALID_STATE"
    comment = "Invalid state test"
    gdrive_id = "some-invalid-gdrive-id"

    # Initial state before update_status is called
    initial_status = tracker.workflow_status_model.status

    await tracker.update_status(state=invalid_state, comment=comment, transcript_gdriveid=gdrive_id, store=True)

    # Assert the state, comment, and gdrive_id remain unchanged
    assert tracker.workflow_status_model.status == initial_status, "Status should not update for an invalid state"
    assert tracker.workflow_status_model.comment != comment, "Comment should not update for an invalid state"
    assert tracker.workflow_status_model.transcript_gdrive_id != gdrive_id, "GDrive ID should not update for an invalid state"

    # Assert that no update or notify methods were called
    mock_update_gfile.assert_not_called()
    mock_notify_change.assert_not_called()

@pytest.mark.asyncio
@patch('workflow_tracker_code.WorkflowTracker._notify_status_change', new_callable=AsyncMock)
@patch('workflow_tracker_code.WorkflowTracker._update_transcription_status_in_mp3_gfile', new_callable=AsyncMock)
async def test_update_status_concurrency(mock_update_gfile, mock_notify_change):
    """
    Test to ensure that concurrent calls to update_status are handled correctly.
    """
    tracker = WorkflowTracker.get_instance()
    states = [state.name for state in WorkflowStates]

    # Simulate concurrent updates by creating a list of tasks
    tasks = [
        asyncio.create_task(
            tracker.update_status(state=state, comment=f"Comment for {state}", transcript_gdriveid=f"gdrive-id-{state}", store=False)
        )
        for state in states
    ]

    # Wait until all tasks are completed
    await asyncio.gather(*tasks)

    # Additional assertions can be placed here to verify the final state
    # This example does not have a clear way to assert the final outcome due to the nature of concurrent updates
    # You would normally check for data integrity, no exceptions raised, or other indicators of correct handling.

    # Verify that _notify_status_change was called for each update
    assert mock_notify_change.call_count == len(states), "Each state update should trigger a notification."

    # Assuming store=False for all updates, _update_transcription_status_in_mp3_gfile should not be called
    mock_update_gfile.assert_not_called()

@pytest.mark.asyncio
@patch('workflow_tracker_code.WorkflowTracker._notify_status_change', new_callable=AsyncMock)
@patch('workflow_tracker_code.WorkflowTracker._update_transcription_status_in_mp3_gfile', new_callable=AsyncMock)
async def test_update_status_store_operation_error_handling(mock_update_gfile, mock_notify_change):
    """
    Test to ensure that update_status handles errors in the store operation (_update_transcription_status_in_mp3_gfile)
    gracefully by verifying that an exception is handled and does not propagate to the caller.
    """
    # Configure the mock to raise an exception when called
    mock_update_gfile.side_effect = Exception("Simulated storage error")

    tracker = WorkflowTracker.get_instance()
    state = WorkflowStates.DOWNLOAD_COMPLETE.name
    comment = "Download complete for workflow ID {id}."
    gdrive_id = "some-gdrive-id"

    # Wrap the call in a try-except to verify that no exception is raised to the caller
    try:
        await tracker.update_status(state=state, comment=comment, transcript_gdriveid=gdrive_id, store=True)
        exception_raised = False
    except Exception:
        exception_raised = True

    # Assert that no exception was raised to the caller
    assert not exception_raised, "update_status should handle store operation errors gracefully."

    # Verify that _update_transcription_status_in_mp3_gfile was called despite the error
    mock_update_gfile.assert_called_once()

    # Optionally, verify that _notify_status_change was still called, if that's the expected behavior
    mock_notify_change.assert_called_once()

@pytest.mark.asyncio
@patch('workflow_tracker_code.WorkflowTracker._notify_status_change', new_callable=AsyncMock)
@patch('workflow_tracker_code.WorkflowTracker._update_transcription_status_in_mp3_gfile', new_callable=AsyncMock)
async def test_update_status_edge_cases(mock_update_gfile, mock_notify_change):
    """
    Test the update_status method for handling edge case parameters,
    including empty strings and None values.
    """
    tracker = WorkflowTracker.get_instance()

    # Define a set of edge case parameter values to test
    edge_cases = [
        {"state": "", "comment": "", "transcript_gdriveid": "", "store": False},
        {"state": None, "comment": None, "transcript_gdriveid": None, "store": False},
        {"state": "DOWNLOAD_COMPLETE", "comment": "", "transcript_gdriveid": None, "store": True},
        # Add more edge cases as needed
    ]

    for case in edge_cases:
        # Reset mocks for each iteration
        mock_update_gfile.reset_mock()
        mock_notify_change.reset_mock()

        # Attempt to update status with edge case parameters
        await tracker.update_status(**case)
        if case["state"] in [None, ""]:
            mock_update_gfile.assert_not_called()
            mock_notify_change.assert_not_called()
        else:
            mock_notify_change.assert_called()


        # Additional assertions can be added here to verify the state of the tracker
        # after handling edge case parameters, if applicable.



