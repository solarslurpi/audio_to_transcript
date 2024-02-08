import asyncio
import logging
import colorlog
import torch
from datetime import datetime
import re
from workflowstatus_code import WorkflowStatus
from logging import Logger


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

def setup_logger():
    """Set up the logger with colorized output"""
    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the logging level

 # Define log format
    log_format = (
        "%(log_color)s[%(levelname)s]%(reset)s "
        "%(log_color)s%(module)s:%(lineno)d%(reset)s - "
        "%(message_log_color)s%(message)s"
    )
    colors = {
        'DEBUG': 'green',
        'INFO': 'yellow',
        'WARNING': 'purple',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }

    # Create a stream handler (console output)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)  # Set the logging level for the handler

    # Apply the colorlog ColoredFormatter to the handler
    formatter = colorlog.ColoredFormatter(log_format, log_colors=colors, reset=True,
                                          secondary_log_colors={
                                              'message': colors
                                          })

    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger

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


def update_task_status(task_id:dict, status: WorkflowStatus, message:str=None, filename:str=None, logger:Logger=None):
    if not task_id or not isinstance(status, WorkflowStatus):
        raise ValueError("Invalid task ID or status")

    # Prepare the status information
    status_info = {
        "status": status.name,
        "description": status.description
    }

    # If an additional message is provided, append it to the description
    if message:
        status_info["description"] += " - " + message

    # If a filename is provided, add the download URL to the status info
    if filename:
        BASE_URL = 'http://localhost:8000/static/'  # Assuming BASE_URL is defined here or imported
        download_url = f"{BASE_URL}/download/{task_id}"


    # Update the global status dictionary
    status_dict[task_id] = status_info

    if logger:
        logger.debug(f"Task {task_id} updated: {status_info}")

    # Signal that an update has occurred to trigger any listening event streams
    update_event.set()






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


