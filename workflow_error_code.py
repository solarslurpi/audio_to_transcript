class WorkflowError(Exception):
    """Base class for errors related to workflow operations."""
    def __init__(self, message="An error occurred during workflow operation.", system_error=None):
        if system_error:
            message += f" System Error: {system_error}"
        super().__init__(message)

class WorkflowOperationError(WorkflowError):
    """Specific errors during workflow file operations."""
    def __init__(self, operation=None, detail=None, system_error=None):
        message = "A transcription operation error occurred."
        if operation:
            message = f"Failed to {operation} during transcription operation."
        if detail:
            message += f" Detail: {detail}."
        super().__init__(message, system_error=system_error)


async def handle_error(status=None, error_message: str=None, operation: str=None):
    from logger_code import LoggerBase
    from workflow_tracker_code import WorkflowTracker
    from workflow_states_code import WorkflowStates
    logger = LoggerBase.setup_logger()
    tracker = WorkflowTracker()
    logger.error(error_message)
    if status:
        tracker.workflow_status.status = status
    else:
        tracker.workflow_status.status = WorkflowStates.ERROR
    tracker.workflow_status.description = error_message
    await tracker.update_status()
    raise WorkflowOperationError(operation=operation, system_error=error_message)