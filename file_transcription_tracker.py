import json
from enum import Enum
from transcription_tracker_code import TranscriptionTracker
from workflowstatus_code import WorkflowStatus
import os
import logging
import threading




file_lock = threading.Lock()

class CustomEncoder(json.JSONEncoder):
    JSON_FILE = "file_transcription_tracker.json"
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name  # Use the enum member's name for serialization
        return json.JSONEncoder.default(self, obj)
class FileTranscriptionTracker(TranscriptionTracker):
    def __init__(self):
        # Initialize the parent class   
        super().__init__()
    
    def update_task_status(self, task_id: str, workflow_status: WorkflowStatus = None, message: str = ''):
        super().update_task_status(task_id, workflow_status, message)
        with file_lock:
            try:
                with open(self.JSON_FILE, 'r') as file:
                    file_infos_list = json.load(file)
                if not isinstance(file_infos_list, list):  # Ensure data is a list.  This is particulary important if the JSON file is new.
                    file_infos_list = []
            except (FileNotFoundError, json.JSONDecodeError):
                file_infos_list = []
            # Find the file info for the task_id
                file_info = next((file_info for file_info in file_infos_list if file_info["task_id"] == task_id), None)
                if file_info:
                    file_info['status'] = workflow_status.name
                    with open(self.JSON_FILE, 'w') as file:
                        json.dump(file_infos_list, file, indent=4, cls=CustomEncoder)
                    self.logger.debug(f"Found a file_info record.  Here is the file_info: {file_info}")
                else:
                    self.logger.debug(f"Did not find a file_info record for task_id: {task_id}")

    def is_duplicate(self, file_info):
        file_infos_list = self.get_file_info_list(self.JSON_FILE)
        return any(file_info == existing_file_info for existing_file_info in file_infos_list)

    def store_task_info(self,file_info=None):
        if not file_info:
            return False
        try:
            with open(JSON_FILE, 'r') as file:
                file_infos_list = json.load(file)
            if not isinstance(file_infos_list, list):  # Ensure data is a list.  This is particulary important if the JSON file is new.
                file_infos_list = []
        except (FileNotFoundError, json.JSONDecodeError):
            file_infos_list = []  
        # Add file info tracking.
        file_infos_list.append(file_info)
        with open(JSON_FILE, 'a') as file:
            json.dump(file_infos_list, file, cls=CustomEncoder)  
        return True

    def update_task_info(self, task_id, work_status: WorkflowStatus):
            global file_lock
            with file_lock:  # Ensure thread-safe operations
                try:
                    file_infos_list = self.get_task_list()
                    for index, value in enumerate(file_infos_list):
                        if value['task_id'] == task_id:
                            file_infos_list[index]['status'] = work_status.name
                            try:
                                with open(JSON_FILE, 'w') as file:
                                    json.dump(file_infos_list, file, cls=CustomEncoder)
                                return True
                            except IOError as e:
                                # Log the error or notify the user/system
                                self.logger.error(f"Failed to write to {JSON_FILE}: {e}")
                                return False
                            except TypeError as e:
                                # This handles serialization errors
                                self.logger.error(f"Error serializing data to JSON: {e}")
                                return False
                except Exception as e:
                    # This is a more general error catch, useful for unexpected errors
                    # You might want to log this or handle it in a specific way
                    self.logger.error(f"An error occurred: {e}")
                    return False
            return True

    # TODO
    def remove_file(self,file_id):
        pass
    
    # def remove_file(self, file_id):
    #     with open(self.json_file, 'r') as file:
    #         list_of_file_infos = self.get_file_info_list(self.json_file)
    #         found_key = False
    #         for index, value in enumerate(list_of_file_infos):
    #             if value['id'] == file_id:
    #                 found_index = index


    #             with open(self.json_file, 'w') as file:
    #                 json.dump(dicts_of_file_infos, file, indent=4)  
    #         return found_key
        

    def get_task_list(self):
        def _create_file_if_not_exists():
            if not os.path.exists(JSON_FILE):
                logging.debug(f"Creating the JSON file to hold task status: {JSON_FILE}.")
                # Create the file just by opening it for writing.
                with open(JSON_FILE, 'w') as file:
                        pass
            else:
                logging.debug(f"Task status JSON file exists: {JSON_FILE}")
        _create_file_if_not_exists(JSON_FILE)
        try:
            with open(JSON_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError):
            logging.debug("There are no mp3 files being tracked at the moment.")
            return []
        except Exception as e:
            logging.error(f"Error reading from JSON file: {e}")
            return None