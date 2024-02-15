
from workflowstatus_code import WorkflowStatus
import logging
from abc import ABC, abstractmethod
import asyncio
from logger_code import LoggerBase
from pydrive2.drive import GoogleDrive
from pydrive2.auth import GoogleAuth
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Optional
from enum import Enum
import os
from dotenv import load_dotenv


load_dotenv()

class Audio_Quality(str, Enum):
    
class GDriveID(str,Enum):
    MP3_GDriveID = os.getenv('MP3_GDRIVE_ID'),
    Transcription_GDriveID = os.getenv('TRANSCRIPTION_GDRIVE_ID')

class TaskUnit(str,Enum):
    YOUTUBE_DOWNLOAD = 'youtube_download'
    TRANSCRIPTION = 'transcription'

class TaskStatus(BaseModel):
    last_modified: datetime = Field(default_factory=datetime.now)
    mp3_gdrive_id: GDriveID = Field(default=GDriveID.MP3_GDriveID)
    transcription_gdrive_id: GDriveID = Field(default=GDriveID.Transcription_GDriveID)
    mp3_gdrive_filename: Optional[str] = None
    transcription_gdrive_filename: Optional[str] = None
    transcription_audio_quality: Optional[str] = None
    transcription_compute_type: Optional[str] = None
    workflow_status: Optional[str] = None  # Adjust according to WorkflowStatus definition
    description: Optional[str] = None
    youtube_url: Optional[str] = None
    current_id: Optional[str] = None
    current_task: Optional[str] = None

    class ConfigDict:
        # use_enum_values = True
        # In order to serialize, we need a custom encoder for WorkflowStatus so that we return the name.
        json_encoders = {
            WorkflowStatus: lambda v: v.name,  
        }


    @field_validator('current_task')
    @classmethod
    def task_type_must_be_valid(cls, v):
        if v not in (TaskUnit.YOUTUBE_DOWNLOAD, TaskUnit.TRANSCRIPTION):
            raise ValueError("current_id must be either 'youtube_download' or 'transcription'")
        return v


# Create a subclass of logging.Handler and override the emit method to call the update_task_status function whenever a logging message is processed.
class TaskStatusLoggingHandler(logging.Handler):
    def __init__(self, task_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_status_function = TranscriptionTracker.update_task_status

    def emit(self, record):
        log_entry = self.format(record)
        self.update_status_function(self.task_id, message=log_entry)

class TranscriptionTracker(ABC):
    logger = LoggerBase.setup_logger()
    #GDRIVE_FOLDER_ID = '1472rYLfk_V7ONqSEKAzr2JtqWyotHB_U'


    def __init__(self):
        self.update_event = asyncio.Event()
        self.task_status = None
        
    def start_task_tracking(self, current_task: str):
        '''
        This starts the tracking of the workflow.  It is called at the beginning of the endpoint.  This way, we can have a better chance at 
        keeping track of where the processing of downloading youtube or transcribeing mp3 has left off.  We don't assign a task id yet.
        we assign what task we are tracking.
        '''
        # The task tracking starts by letting us know what task we are tracking.  The whole point is to initialize a task_status.
        try:
            self.task_status = TaskStatus()
            self.task_status.current_task = current_task
            self.logger.debug(f"TaskStatus created successfully.  Current task: {self.task_status.current_task}")
            return self.task_status
        except ValidationError as e:
            self.logger.error(f"Validation error: {e}")
            raise ValidationError(e)



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
    def update_task_status(self, message: str=''):
        # After initializing task tracking, update_task_status will be called at certain points in the code to update a store letting us know if the task was successfully completed.  . Before calling, the parameters that are to be updated 
        # need to be filled into the task_status object.  The task_status object is used to keep track of the status of the task.
        # There are two updates that are made.  One is to the SSE stream if the client has chosen to listen to that endpoing.  The
        # other is to the file_transcription_tracker.json file.  The file_transcription_tracker.json file is used to keep track
        # of which files have completed processing and which have notg.
        if self.task_status.workflow_status:
            self.task_status.description = self.task_status.workflow_status.format_description(task_id=self.task_status.current_id)  + "-" + message
            self.update_event.set()
            self.logger.info(f"Status Updated: {self.task_status}")

    def create_task_id(self):
        # The self.task_status.current_id is set to the GFile folder id that has been assigned to the task. At this time, there are two tasks: 1. download mp3 from YouTube video's audio 2. Transcribing and mp3
        # into a text file.
        if not self.task_status:
            self.logger.error("TaskStatus has not been initialized.  Please call start_task_tracking() first.")
            return None
        try:
            # The google file will hold either an mp3 if the task is to download a YouTube audio or a text file containing the transcription if the task is to transcribe an mp3.
            gfile = self.create_gdrive_file()
            self.logger.debug(f"GDrive file created successfully.  The Google Drive ID is: {gfile['id']}")
        except Exception as e:
                self.logger.error(f"Error: {e}")
                raise Exception(e)
        self.task_status.workflow_status = WorkflowStatus.IDTRACKED
        self.task_status.description = f"Starting the {self.task_status.current_task} task."
        self.task_status.current_id = gfile['id']
        # Determine which task we are doing.
        if self.task_status.current_task == TaskUnit.YOUTUBE_DOWNLOAD.value:
            self.task_status.mp3_gdrive_id = gfile['id']
        else:
            self.task_status.transcription_gdrive_id = gfile['id']
        self.update_task_status()


    def create_gdrive_file(self, filename='not specified'):
        def _get_gdrive_folder_id(current_task):
            if current_task == TaskUnit.YOUTUBE_DOWNLOAD.value:
                return GDriveID.MP3_GDriveID.value
            elif current_task == TaskUnit.TRANSCRIPTION.value:
                return GDriveID.Transcription_GDriveID.value
            else:
                self.logger.error("Invalid current task")
                raise ValueError("Invalid current task")

        try:
            gauth = self.login_with_service_account()
            drive = GoogleDrive(gauth)
            folder_id = _get_gdrive_folder_id(self.task_status.current_task)
            file_metadata = {
                'title': filename,
                'parents': [{'id': folder_id}],
                'mimeType': 'text/plain'
            }
            gfile = drive.CreateFile(file_metadata)
            gfile.Upload() # Create the file so we can get the ID of the file.

        except Exception as e:
            self.logger.error(f"Error: {e}.")
            self.update_task_status(self.task_id, WorkflowStatus.ERROR, message=f"{e}")
            raise Exception(e)
        return gfile

    def login_with_service_account(self):
        """
        Google Drive service with a service account.
        note: for the service account to work, you need to share the folder or
        files with the service account email.

        :return: google auth
        """
        # Define the settings dict to use a service account
        # We also can use all options available for the settings dict like
        # oauth_scope,save_credentials,etc.
        settings = {
                    "client_config_backend": "service",
                    "oauth_scope": ["https://www.googleapis.com/auth/drive"],
                    "service_config": {
                        "client_json_file_path": "service-account-creds.json",
                    }
                }
        # Create instance of GoogleAuth
        gauth = GoogleAuth(settings=settings)
        # Authenticate
        gauth.ServiceAuth()
        return gauth
    
    def delete_gdrive_file(self):
        gauth = self.login_with_service_account()
        drive = GoogleDrive(gauth)
        try:
            file = drive.CreateFile({'id': self.task_status.current_id})
            file.Delete()
            self.logger.debug(f"GDrive file deleted successfully.  The Google Drive ID is: {self.task_status.current_id}")
        except Exception as e:
            self.logger.error(f"{e}")
            return False
        return True

    async def upload_to_gdrive(self, downloaded_file_path: str):
    # Perform authentication; this might be moved to a more central location in your application
        gauth = self.login_with_service_account()
        drive = GoogleDrive(gauth)

        # Ensure `downloaded_file_path` is set to the path of the file to upload
        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
            self.logger.error("No file to upload or file does not exist.")
            self.task_status.workflow_status = WorkflowStatus.ERROR
            self.update_task_status(message="No file to upload or file does not exist.")
            return

        # Define the upload operation as a synchronous function
        def upload_operation():
            try:
                gfile = drive.CreateFile({'id':self.task_status.current_id})
                if gfile:
                    gfile.SetContentFile(downloaded_file_path)
                    file_name = os.path.basename(downloaded_file_path)
                    gfile["title"] = file_name
                    gfile.Upload()
                    # Close the file content stream if it's open
                    if hasattr(gfile, 'content') and gfile.content:
                        gfile.content.close()

                    # Optionally, remove the local file after upload
                    os.remove(downloaded_file_path)

                    self.logger.info(f"Uploaded {downloaded_file_path} to Google Drive.")
                    self.task_status.workflow_status = WorkflowStatus.UPLOAD_COMPLETE
                    self.update_task_status()
                else:
                    self.logger.error(f"Error- could not find a google file with the GDrive ID of {self.task_status.current_id} to Google Drive.")
                    return False
            except Exception as e:
                self.logger.error(f"Error uploading {downloaded_file_path} to Google Drive: {e}")
                self.task_status.workflow_status = WorkflowStatus.ERROR
                self.update_task_status( message=f"Error uploading {downloaded_file_path} to Google Drive: {e}")
        upload_operation()
    

    async def download_from_gdrive(self, gdrive_id: str=None, destination_dir: str=None):
        if not gdrive_id:
            self.handle_error_message("The Google Drive ID must not be empty.")
        if not destination_dir:
            self.handle_error_message("The destination directory must not be empty.")
        if not os.path.isdir(destination_dir):  
            self.handle_error_message(f"The destination directory does not exist: {destination_dir}")

        def download_operation():
            try:
                gauth = GoogleAuth()
                # Assuming login_with_service_account is a method that configures and returns a GoogleAuth instance
                gauth = self.login_with_service_account()  
                drive = GoogleDrive(gauth)
                gfile = drive.CreateFile({'id': gdrive_id})  # Initialize GoogleDriveFile instance with the file ID
                gfile.FetchMetadata(fields='title')  # Fetch metadata to get the title (filename)
                
                destination_path = os.path.join(destination_dir, gfile['title'])
                gfile.GetContentFile(destination_path)  # Download file using the original filename
                
                self.logger.info(f"Downloaded file with GDrive ID {gdrive_id} to {destination_path}")
                return destination_path
            except Exception as e:
                self.tracker.send_error_message(error_msg)
                error_msg = f"Error downloading file from Google Drive: {e}"
                self.logger.error(error_msg)
                self.task_status.workflow_status = WorkflowStatus.ERROR
                self.update_task_status(message=error_msg)
                raise

        # Execute the synchronous PyDrive2 operation in an executor to not block the async loop
        destination_path = await asyncio.get_event_loop().run_in_executor(None, download_operation)
        return destination_path

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
    
    def handle_error_message(self, error_message: str = ''):
        self.logger.error(error_message)
        self.workflow_status = WorkflowStatus.ERROR
        self.update_task_status(message=error_message)
        raise 

    @abstractmethod
    def update_store(self):
        # Store the task_status
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









