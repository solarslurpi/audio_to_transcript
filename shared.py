


import torch

import re



BASE_URL = "http://127.0.0.1:8000"


TRANSCRIBE_ENDPOINT = f"{BASE_URL}/transcribe/mp3"
# Initialize an empty dictionary to act as the progress store



LOCAL_MP3_DIRECTORY = "./temp_mp3s"







    


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


