
from workflowstatus_code import WorkflowStatus
import logging
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
from logger_code import LoggerBase

# Create a subclass of logging.Handler and override the emit method to call the update_task_status function whenever a logging message is processed.
class TaskStatusLoggingHandler(logging.Handler):
    def __init__(self, task_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.update_status_function = TranscriptionTracker.update_task_status

    def emit(self, record):
        log_entry = self.format(record)
        self.update_status_function(self.task_id, message=log_entry)

class TranscriptionTracker(ABC):
    logger = LoggerBase.setup_logger()
    GDRIVE_FOLDER_ID = '1472rYLfk_V7ONqSEKAzr2JtqWyotHB_U'


    def __init__(self):
        self.update_event = asyncio.Event()
        self.status_dict = {}



    @abstractmethod
    def is_duplicate(self, file_info):
        pass

    def add_file(self, file):
        '''
        Add a file to the tracker.  If the file is already in the tracker...
        '''
        file_info = self._generate_file_info(file)
        if not self.is_duplicate(file_info):
            self.store_file_info(file_info)
            return file_info
        else:
            return None
    def update_task_status(self, task_id: str, workflow_status: WorkflowStatus = None, message: str = ''):
        if workflow_status:
            status_message = workflow_status.format_description(task_id=task_id)  # Ensure your WorkflowStatus enum supports .format
            self.status_dict[task_id] = {"status": workflow_status.name, "description": status_message}
        if message:
            self.status_dict[task_id]["description"] += "-" + message
        self.update_event.set()
        self.logger.info(f"Status Updated: {self.status_dict[task_id]}")

    def create_task_id(self):
        now = datetime.now()
        midnight = datetime.combine(now.date(), datetime.min.time())
        seconds_since_midnight = (now - midnight).seconds

        # Format the seconds to ensure it is a 5-digit number. This will only work correctly up to 99999 seconds (27.7 hours)
        task_id = f"{seconds_since_midnight:05d}"
        # Set up the handler once.
        self.attach_update_status_to_transformers_logger(task_id)
        return task_id
    
    @abstractmethod
    def get_task_list(self):
        pass

    def attach_update_status_to_transformers_logger(self,task_id:str):
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
    


    @abstractmethod
    def remove_file(self, file_id):
        pass

    def _generate_file_info(self, file):
        try:
            return {
                'name': file['title'],
                'id': file['id'],
                'status': TranscriptionTracker.WorkflowStatus.NEW
            }
        except Exception as e:
            logging.error(f"Error generating file info for {file['title']}: {e}")
            return None

    @abstractmethod
    def store_task_info(self, file_info:dict):
        pass
    
    @abstractmethod
    def update_task_info(self, task_id:str, work_status:WorkflowStatus):
        pass







