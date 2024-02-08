from file_transcription_tracker import FileTranscriptionTracker
from shared import setup_logger
from pydrive2.drive import GoogleDrive
import os
import requests
from sseclient import SSEClient

BASE_URL = "http://127.0.0.1:8000"
logger = setup_logger()

def listen_for_status_updates(task_id):
    # The URL for receiving status updates, replace <base_url> with the actual base URL
    status_url = f"{BASE_URL}/status/{task_id}/stream"
    
    # Create a session object to persist session across requests (optional)
    session = requests.Session()
    response = session.get(status_url, stream=True)
    
    # Create an SSEClient from the response
    client = SSEClient(response)
    for event in client.events():
        # Here, `event.data` contains the status message
        print(f"Received event: {event.data}")
        # Process the event.data as needed
def transcribe_mp3(file_path,model_name="medium", compute_type="float16"):
    url = f"{BASE_URL}/transcribe/mp3" 
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.split('/')[-1], f, 'audio/mpeg')}
        data = {'model_name': model_name, 'compute_type': compute_type}
        response = requests.post(url, files=files, data=data)
        print(response)
def download_file(drive, file_info):
    # Initialize a file object and specify the ID of the file to download
    directory = "./temp_mp3s"
    if not os.path.exists(directory):
        os.makedirs(directory)    
    download_path = f"{directory}/{file_info.get('name')}"
    file = drive.CreateFile({'id': file_info['id']})
    # Download the file to a local file specified by local_path
    file.GetContentFile(download_path)
    return download_path
def process_files_ready_for_transcription(transcription_tracker, drive):
        file_info_list = transcription_tracker.get_file_info_list(transcription_tracker.json_file)

        for file_info in file_info_list:
            current_status = transcription_tracker.WorkflowStatus[file_info.get('status')].value
            if current_status < transcription_tracker.WorkflowStatus.TRANSCRIBING.value:
                downloaded_mp3 = download_file(drive, file_info)
                # Transcribe the downloaded file
                transcription_response = transcribe_mp3(downloaded_mp3)
                logger.debug(f"Transcription response: {transcription_response}")


transcription_tracker = FileTranscriptionTracker()

gauth = transcription_tracker.login_with_service_account()
drive = GoogleDrive(gauth)
process_files_ready_for_transcription(transcription_tracker, drive)
