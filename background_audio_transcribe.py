from file_transcription_tracker import FileTranscriptionTracker
from shared import setup_logger, login_with_service_account
from pydrive2.drive import GoogleDrive
import os
import requests
from sseclient import SSEClient

BASE_URL = "http://127.0.0.1:8000"
logger = setup_logger()




def transcribe_mp3(file_path, model_name="medium", compute_type="float16"):
    url = f"{BASE_URL}/transcribe/mp3"
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'audio/mpeg')}
            data = {'model_name': model_name, 'compute_type': compute_type}
            response = requests.post(url, files=files, data=data)
            # THe response contains the all important task id! 
            if response.status_code == 200:
                logger.info(f"Transcription initiated: {response.json()}")
                return response.json()
            else:
                logger.error(f"Transcription initiation failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Failed to initiate transcription for {file_path}: {e}")


def process_files_ready_for_transcription(transcription_tracker, drive):
        logger.debug(f"Processing files ready for transcription...")
        file_info_list = transcription_tracker.get_file_info_list(transcription_tracker.json_file)

        for file_info in file_info_list:
            current_status = transcription_tracker.WorkflowStatus[file_info.get('status')].value
            logger.debug(f"Current status for {file_info.get('name')} is {current_status}")
            if current_status < transcription_tracker.WorkflowStatus.TRANSCRIBING.value:
                gdrive_mp3 = download_file(drive, file_info)
                # Transcribe the downloaded file
                transcription_response = transcribe_mp3(gdrive_mp3)
                logger.debug(f"Transcription response: {transcription_response}")


transcription_tracker = FileTranscriptionTracker()

gauth = login_with_service_account()
drive = GoogleDrive(gauth)
process_files_ready_for_transcription(transcription_tracker, drive)
