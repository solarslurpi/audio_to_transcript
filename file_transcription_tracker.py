import json
from transcription_tracker_code import TranscriptionTracker
from workflowstatus_code import WorkflowStatus
import os
import threading





# class CustomEncoder(json.JSONEncoder):

#     def default(self, obj):
#         if isinstance(obj, Enum):
#             return obj.name  # when there is an enum in the object, return the value.
#         # Call the superclass method for other types.
#         return json.JSONEncoder.default(self, obj)
    
class FileTranscriptionTracker(TranscriptionTracker):

    def __init__(self):
        # Initialize the parent class   
        super().__init__()
        self.JSON_FILE = "file_transcription_tracker.json"
        self._ensure_file_exists()
        self.file_lock = threading.Lock()

    def _ensure_file_exists(self):
        if not os.path.exists(self.JSON_FILE):
            with open(self.JSON_FILE, 'w') as file:
                pass # File is created and immediately closed.
    def update_task_status(self, message: str = '',store=True):
        super().update_task_status( message)
        if store:
            self.update_store()        

    def is_duplicate(self, file_info):
        file_infos_list = self.get_file_info_list(self.JSON_FILE)
        return any(file_info == existing_file_info for existing_file_info in file_infos_list)

    def update_store(self):
        with self.file_lock:
            # First thing, did an error occur? If so delete the gfile that was created when the task was started.
            if self.task_status.workflow_status == WorkflowStatus.ERROR:
                self.delete_gdrive_file()
                return False
            with open(self.JSON_FILE, 'r') as file:
                try:
                    task_status_list = json.load(file)
                except json.JSONDecodeError:
                    task_status_list = []
            #Pydantic 2 uses model_dump() to serialize the object into a dictionary. The mode
            # param is necessary so that non-serializable objects like Enums can be interpreted
            # as either their name or value (see the Pydantic definition of TaskStatus)
            # model_dump_json() serializes an object into a json string.

            task_status_dict = self.task_status.model_dump(mode="json")
            # Check to see if the current id is in the list of task statuses.  If it is, update the task status.  If not, add it to the list.
            index_to_update = next((i for i, task_status in enumerate(task_status_list) if task_status.get("current_id") == task_status_dict.get("current_id")), None)
            if index_to_update is not None:
                task_status_list[index_to_update] = task_status_dict
            else:
                task_status_list.append(task_status_dict)
            with open(self.JSON_FILE, 'w') as file:
                json.dump(task_status_list, file, indent=4)
        return True


    # TODO
    def remove_file(self,file_id):
        pass
        
