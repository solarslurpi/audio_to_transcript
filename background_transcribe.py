

import asyncio
import httpx
import os
import json
from pydrive2.drive import GoogleDrive
from shared import setup_logger, login_with_service_account, BASE_URL, LOCAL_MP3_DIRECTORY, MODEL_NAME, COMPUTE_TYPE, GDRIVE_FOLDER_ID, TRANSCRIBE_ENDPOINT
from file_transcription_tracker import FileTranscriptionTracker
from workflowstatus_code import WorkflowStatus

# Initialize logging
logger = setup_logger()

# Google Drive folder ID where MP3 files are stored


# Initialize Google Drive
gauth = login_with_service_account()
drive = GoogleDrive(gauth)


def scan_for_transcription_ready_mp3s():
    """Scan Google Drive for MP3 files that are new or not yet transcribed, and update tracking."""
    transcription_tracker = FileTranscriptionTracker()  # Initialize the transcription tracker
    query = f"'{GDRIVE_FOLDER_ID}' in parents"
    # query = f"'{GDRIVE_FOLDER_ID}' in parents and trashed=false and mimeType='audio/mpeg'"  # Define query for MP3 files
    file_list = drive.ListFile({'q': query}).GetList()  # Fetch MP3 files from Google Drive
    tracked_files_list = transcription_tracker.get_file_info_list()  # Get currently tracked files

    file_infos_for_transcription = []  # Initialize list for file_infos of files ready for transcription

    for file in file_list:
        file_info = {
            'name': file['title'], 
            'id': file['id'], 
            'status': WorkflowStatus.IDTRACKED.name  # Use enum for status
        }  # Set up file info

        # Check if file is new
        if not any(f['id'] == file_info['id'] for f in tracked_files_list):
            transcription_tracker.add_file(file_info)  # Add new file to the tracker
            logger.info(f"New MP3 file detected and tracked: {file_info['name']}")
            file_infos_for_transcription.append(file_info)  # Append new file_info for transcription
        else:
            # Check existing files for status less than DOWNLOAD_COMPLETE
            existing_file_info = next((f for f in tracked_files_list if f['id'] == file_info['id']), None)
            if existing_file_info and WorkflowStatus[existing_file_info['status']].value < WorkflowStatus.DOWNLOAD_COMPLETE.value:
                # No need to append the id again, just append the existing file_info ready for transcription
                file_infos_for_transcription.append(existing_file_info)  # Append file_info ready for transcription
                logger.info(f"Existing MP3 file ready for transcription: {existing_file_info['name']}")

    # Return list of file_infos ready for transcription
    return file_infos_for_transcription


async def download_file_from_gdrive(file_info:dict) -> str:
    """Download a file from Google Drive given its file ID."""
    gauth = login_with_service_account()
    drive = GoogleDrive(gauth)

    # Download the file
    gfile = drive.CreateFile({'id': file_info['id']})
    local_file_path = f"{LOCAL_MP3_DIRECTORY}/{file_info.get('name')}"
    gfile.GetContentFile(local_file_path)
    return local_file_path

async def send_transcription_request(file_info: dict):
    """Send an asynchronous multipart/form-data request to transcribe a file and handle SSE for updates."""
    local_file_path = await download_file_from_gdrive(file_info)

    # Prepare multipart/form-data content
    files = {
        'file': (file_info.get('name'), open(local_file_path, 'rb')),
        'model_name': (None, MODEL_NAME),
        'compute_type': (None, COMPUTE_TYPE),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(TRANSCRIBE_ENDPOINT, files=files)
        response_data = response.json()
        task_id = response_data.get("task_id")

    files['file'][1].close()
    os.remove(local_file_path)

    # Start listening to SSE for the task_id
    await listen_for_sse_events(task_id)
async def listen_for_sse_events(task_id: str):
    status_url = f"{BASE_URL}/status/{task_id}/stream"

    async with httpx.AsyncClient() as client:
        async with client.stream("GET", status_url) as response:
            event_data = ""
            async for chunk in response.aiter_raw():
                event_data += chunk.decode()
                if "\n\n" in event_data:  # End of an event
                    # Process complete SSE messages
                    for event in event_data.strip().split("\n\n"):
                        if event.startswith("data: "):
                            data = json.loads(event.replace("data: ", ""))
                            logger.debug(f"Received event: {data}")
                            # Process the event data as needed, e.g., update tracker or handle transcription status
                    event_data = ""  # Reset for the next event

async def transcribe_files(file_infos_for_transcription_list:list):
    """Asynchronously transcribes files and uploads them to Google Drive."""
    # We are looping through each file(_info) that is ready for transcription
    # send_transcription_request() is async. But here we are not awaiting?
    # or does the asyncio.as_completed() handle this?
    transcription_tasks = [send_transcription_request(file_info) for file_info in file_infos_for_transcription_list]

    for i, task in enumerate(asyncio.as_completed(transcription_tasks)):
        response = await task


            



async def main():
    # Assuming ids_for_transcription is populated from the previous function
    file_infos_for_transcription_list = scan_for_transcription_ready_mp3s()
    await transcribe_files(file_infos_for_transcription_list)

if __name__ == "__main__":
    asyncio.run(main())
