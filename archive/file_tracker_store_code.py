
import json
from tracker_store_code import TrackerStore, TrackerIOError
from settings_code import get_settings
from workflow_tracker_code import WorkflowTracker
from workflow_status_model import TranscriptionStatus
from asyncio import Lock
    
class FileTrackerStore(TrackerStore):

    def __init__(self):
        # Initialize the parent class   
        super().__init__()
        try:
            settings = get_settings()
            self.tracking_file = settings.tracker_json_file_path
        except Exception as e:
            self.logger.error(f'Error getting settings: {e}')
            raise TrackerIOError(operation='getting settings', system_error=e)
        self.tracker = WorkflowTracker()
        self.lock = Lock()
    
    def load_status_list(self) -> list[TranscriptionStatus]:
        status_list = []
        # Get the transaction status records.
        with open(self.tracking_file, 'r') as file:
            try:
                json_contents = json.load(file)
                # Translate each task_list entry in the store to a TrackerStatus object.
                for json_obj in json_contents:
                    workflow_status = TranscriptionStatus(**json_obj)
                    status_list.append(workflow_status)
            except json.JSONDecodeError: # This can happen if the file is empty.As well as other reasons...
                status_list = [] 
        return status_list

    async def update_status_in_store(self):
        # open the tracking file and see if there are any entries.
        # If there are entries, do any of the entries contain the current ID?
        # If so, update that record by replacing the fields and then rewriting in it's place
        # if the file is empty, then make a call to add_status.
        async with self.lock:
            try:

                with open(self.tracking_file, 'r') as file:
                    json_contents = json.load(file)
            except json.JSONDecodeError: # This can happen if the file is empty.As well as other reasons...
                    json_contents = []
            try:
                id_found = False
                for json_obj in json_contents:
                    if json_obj['id'] == self.tracker.workflow_status.id:
                        id_found = True
                        with open(self.tracking_file, 'w') as file:
                            json.dump(json_contents, file, indent=4)
                        break
                if not id_found:
                    try:
                        await self._add_status_to_store()
                    except Exception as e:
                        self.logger.error(f"Error updating workflow status in store: {e}")
                        raise TrackerIOError(operation='update_task_status', detail=self.tracker, system_error=e)
            except Exception as e:
                self.logger.error(f"Error updating task status in store: {e}")
                raise TrackerIOError(operation='update_task_status', detail=self.tracker, system_error=e)

    async def _add_status_to_store(self):
        # The caller has a file lock, so do not put one here.
        try:
            with open(self.tracking_file, 'r') as file:
                json_contents = json.load(file)
        except json.JSONDecodeError: # This can happen if the file is empty.As well as other reasons...
                json_contents = []  
        try:
            json_contents.append(self.tracker.workflow_status.dict())
            with open(self.tracking_file, 'w') as file:
                json.dump(json_contents, file, indent=4)
        except Exception as e:
            self.logger.error(f"Error adding task status to store: {e}")
            raise TrackerIOError(operation='add_task_status', detail=self.tracker.workflow_status, system_error=e)