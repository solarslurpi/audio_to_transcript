import pytest
from workflow_tracker_code import WorkflowTracker

def test_workflow_tracker_singleton_instance():
    """
    Test to ensure that the WorkflowTracker.get_instance() method correctly initializes
    and returns the singleton instance of the WorkflowTracker class. This test checks
    that the 'workflow_status_model' attribute is properly initialized, indicating
    that the __init__ method has been called.
    """
    # Retrieve the singleton instance
    tracker_instance = WorkflowTracker.get_instance()
    # Check that the instance is indeed an instance of WorkflowTracker
    assert isinstance(tracker_instance, WorkflowTracker), "get_instance() did not return a WorkflowTracker instance."

    # Check that the 'workflow_status_model' attribute is initialized
    assert hasattr(tracker_instance, 'workflow_status_model'), "workflow_status_model is not initialized in WorkflowTracker instance."

    # Optionally, check that calling get_instance() again returns the same instance
    another_tracker_instance = WorkflowTracker.get_instance()
    assert tracker_instance is another_tracker_instance, "get_instance() returned different instances for a supposed singleton."
