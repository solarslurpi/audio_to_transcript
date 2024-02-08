import json
from enum import Enum
from transcription_tracker_code import TranscriptionTracker
from workflowstatus_code import WorkflowStatus
import os
import logging

JSON_FILE = "file_transcription_tracker.json"

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name  # Use the enum member's name for serialization
        return json.JSONEncoder.default(self, obj)
class FileTranscriptionTracker(TranscriptionTracker):
    def __init__(self, json_file=JSON_FILE):
        # Initialize the parent class   
        super().__init__()
        self.json_file = json_file
    
    def is_duplicate(self, file_info):
        file_infos_list = self.get_file_info_list(self.json_file)
        return any(file_info == existing_file_info for existing_file_info in file_infos_list)

    def store_file_info(self, file_info):
        self.update_file_status(file_info, WorkflowStatus.IDTRACKED)
        try:
            with open(self.json_file, 'r') as file:
                file_infos_list = json.load(file)
            if not isinstance(file_infos_list, list):  # Ensure data is a list
                file_infos_list = []
        except (FileNotFoundError, json.JSONDecodeError):
            file_infos_list = []  
        # Add file info tracking.
        file_infos_list.append(file_info)
        with open(self.json_file, 'a') as file:
            json.dump(file_infos_list, file, cls=CustomEncoder)  
    
    def remove_file(self, file_id):
        with open(self.json_file, 'r') as file:
            list_of_file_infos = self.get_file_info_list(self.json_file)
            found_key = False
            for index, value in enumerate(list_of_file_infos):
                if value['id'] == file_id:
                    found_index = index


                with open(self.json_file, 'w') as file:
                    json.dump(dicts_of_file_infos, file, indent=4)  
            return found_key
        
    def update__status(self, file_info, status):
        file_info['status'] = status
        # TODO = might be more once we add in transcribing...... and perhaps be an abstract method...?

    def get_file_info_list(self,json_file, create_file_if_not_exists=True):
        def _create_file_if_not_exists(json_file, create_file_if_not_exists=True):
            if not os.path.exists(json_file):
                logging.debug(f"JSON file not found: {json_file}.")
                if not create_file_if_not_exists:
                    logging.debug("Returning None.")
                    return None
                # Open the file in write mode, which creates the file if it does not exist
                else:
                    with open(json_file, 'w') as file:
                        pass
            else:
                logging.debug(f"File already exists: {json_file}")
        _create_file_if_not_exists(json_file)
        try:
            with open(json_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError) as e:
            logging.debug("There are no mp3 files being tracked at the moment.")
            return []
        except Exception as e:
            logging.error(f"Error reading from JSON file: {e}")
            return None