import asyncio
import logging
import torch
from datetime import datetime
import re
from workflowstatus_code import WorkflowStatus


# Initialize an empty dictionary to act as the progress store
status_dict = {}
# Global event to signal updates
update_event = asyncio.Event()

MODEL_NAMES_DICT = {
    "tiny": "openai/whisper-tiny",
    "tiny.en": "openai/whisper-tiny.en",
    "base": "openai/whisper-base",
    "base.en": "openai/whisper-base.en",
    "small": "openai/whisper-small",
    "small.en": "openai/whisper-small.en",
    "medium": "openai/whisper-medium",
    "medium.en": "openai/whisper-medium.en",
    "large": "openai/whisper-large",
    "large-v2": "openai/whisper-large-v2",
}

COMPUTE_TYPE_MAP = {
    "default": torch.get_default_dtype(),
    # "int8": torch.int8,
    # "int16": torch.int16,
    "float16": torch.float16,
    "float32": torch.float32,
}

# Create a subclass of logging.Handler and override the emit method to call the update_task_status function whenever a logging message is processed.
class TaskStatusLoggingHandler(logging.Handler):
    def __init__(self, task_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.update_status_function = update_task_status

    def emit(self, record):
        log_entry = self.format(record)
        self.update_status_function(self.task_id, log_entry)


def attach_update_status_to_transformers_logger(task_id):
    # Get the logger for the 'transformers' library
    # This will give us transcription status updates on % done.
    transformers_logger = logging.getLogger('transformers')
    
    # Optionally, set the logging level if you want to capture logs at a specific level
    transformers_logger.setLevel(logging.INFO)   
    # Create and add the custom handler
    custom_handler = TaskStatusLoggingHandler(task_id)
    custom_handler.setLevel(logging.INFO)  # Adjust as needed
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    custom_handler.setFormatter(formatter)
    
    # Attach the custom handler to the transformers logger
    transformers_logger.addHandler(custom_handler)

    # To prevent log messages from propagating to the root logger and being printed to the console
    transformers_logger.propagate = False
    
def create_task_id():
    now = datetime.now()
    midnight = datetime.combine(now.date(), datetime.min.time())
    seconds_since_midnight = (now - midnight).seconds

    # Format the seconds to ensure it is a 5-digit number. This will only work correctly up to 99999 seconds (27.7 hours)
    task_id = f"{seconds_since_midnight:05d}"
    # Set up the handler once.
    attach_update_status_to_transformers_logger(task_id)
    return task_id


def update_task_status(task_id, status: WorkflowStatus, message=None, filename=None):
    BASE_URL = 'http://localhost:8000/static/'
    if task_id:
        status_info = {
            "status": status.name,  # Static part: ENUM name
            "description": message if message else status.value,  # Dynamic part: additional message or default description
        }
        if filename:
            download_url = f"{BASE_URL}{filename}"
            status_info["url"] = download_url

        # Assuming status_dict is a shared/global structure for tracking task statuses
        status_dict[task_id] = status_info
        print(f"Task {task_id} updated to {status_info}")

        # Here, instead of setting an event, directly call the function to broadcast this update via SSE
        broadcast_sse_update(task_id)
    else:
        raise ValueError(f"Invalid task ID {task_id}")
    
def update_task_status(task_id, status, filename=None):
    BASE_URL = 'http://localhost:8000/static/'
    if task_id:
        if filename:
            download_url = f"{BASE_URL}{filename}"
            status_dict[task_id] = {"status": status, "url": download_url}
        else:
            print("-"*40)
            print(f"str length of status: {len(status)} status: {status}")
            print("-"*40)
            new_status = extract_downloading_info(status)
            if new_status:
                print("-"*40)
                print(f"NEW status: {new_status}")
                print("-"*40)
                status = new_status
            status_dict[task_id] = {"status": status}
            print(f"Task {task_id} updated to {status}")
        update_event.set()
    else:
        raise ValueError(f"Invalid task ID {task_id}")


def get_task_status(task_id):
    """Retrieve the status of a task."""
    if task_id in status_dict:
        return status_dict[task_id]
    else:
        return None  # or raise an exception, depending on your error handling strategy




def extract_downloading_info(log_string):
    # Adjusted pattern to match both digit and "--" based ETA
    pattern = r"(\d+\.\d+)%.*?((?:\d+:\d+)|(?:--:--:--))"
    
    # Search for the pattern in the log string
    match = re.search(pattern, log_string, re.DOTALL)
    
    # If a match is found, extract the percentage downloaded and ETA
    if match:
        percent_downloaded = match.group(1)
        eta = match.group(2)
        return f"Downloading: {percent_downloaded}% ETA: {eta}"
    # Return None if the string does not include both the % downloaded and ETA
    return None

# Test with the provided string
# log_string_with_both = 'Downloading: temp_files\\09744_temp.webm, \x1b[0;94m  0.0%\x1b[0m, \x1b[0;33m--:--:--\x1b[0m'
# print(extract_downloading_info(log_string_with_both))


