
import json
import asyncio


from typing import Optional

from workflow_states_code import WorkflowStates, WorkflowEnum
from workflow_error_code import async_error_handler,handle_error
from logger_code import LoggerBase
from workflow_tracker_code import WorkflowTracker

error_state = WorkflowStates(status=WorkflowEnum.ERROR)

@async_error_handler(status=error_state)
async def update_status(workflow_tracker: WorkflowTracker, store=False):
# state: WorkflowStates,
# comment: Optional[str] = None,
# transcript_gdrive_id: Optional[str] = None,
# store: Optional[bool] = False,
# ):
    # TODO: Validate the workflow_tracker input.  I still get confused as to why Pydantic
    # doesn't validate input attributes???
    # WorkflowStates.validate_state(state)
    logger = LoggerBase.setup_logger('update_status')

    # async def _validate_state():
    #     if not isinstance(state, WorkflowStates):
    #         return False
    #     return True

    async def _notify_status_change():
        # self.event_tracker.set()
        # await asyncio.sleep(0.1)  # Simulation of an asynchronous operation
        # self.event_tracker.clear()
        # self.logger.info(f"Status changed to {self.workflow_status.status}")
        pass

    def _statusRepeatCounter():
        # This dictionary will hold the count of each status update attempt
        counts = {}
        # closure to maintain the counts.
        def counter(status):
            # Increment the count for the given status
            if status in counts:
                counts[status] += 1
            else:
                counts[status] = 1
            # Optionally, you can return the current count for the given status
            return counts[status]

        return counter
    # This function uses the closure for tracking status repeats
    def _update_status_repeat(state):
        # Call the counter with the current status to increment its count
        status_repeat_counter = _statusRepeatCounter()
        count = status_repeat_counter(state)
        state_str = state.name
        log_message = {"state": state_str, "comment":comment, "count": count}
        # Log the message with the state count appended
        logger.flow(json.dumps(log_message))

    async def _update_transcription_status_in_mp3_gfile(transcription_info_dict:dict) -> None:
        loop = asyncio.get_running_loop()
        def _update_transcription_status():
            from gdrive_helper_code import GDriveHelper

            gfile_id = WorkflowTracker.get('mp3_gfile_id')
            gh = GDriveHelper()
            file_to_update = gh.CreateFile({'id': gfile_id})
            transcription_info_json = WorkflowTracker.get_model_dump()
            # The transcription (workflow) status is placed as a json string within the gfile's description field.
            # This is not ideal, but using labels proved to be way too difficult?
            file_to_update['description'] = transcription_info_json
            file_to_update.Upload()
        await loop.run_in_executor(None, _update_transcription_status)

    state = workflow_tracker.get('status')
    _update_status_repeat(workflow_tracker.get('status'))

    WorkflowTracker.update(status=WorkflowEnum.TRANSCRIPTION_COMPLETE,transcript_gdrive_id=transcript_gdrive_id)

    if store:
        if not WorkflowTracker.get('mp3_gfile_id'):
            await handle_error(status=WorkflowStates.ERROR,error_message='Option was to store the status. However, the mp3_file_id property is not set.',operation="update_status",raise_exception=False)
        await _update_transcription_status_in_mp3_gfile(workflow_tracker)
    await _notify_status_change()
