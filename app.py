from typing import Optional
from pydantic import BaseModel, validator
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, Response, Form
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import uvicorn
import aiofiles
import os
import json
from audio_to_transcript import AudioToTranscript
from shared import create_task_id, get_task_status, update_task_status, setup_logger, status_dict, update_event, MODEL_NAMES_DICT, COMPUTE_TYPE_MAP
from workflowstatus_code import WorkflowStatus
# Add any other imports you might need for your custom logic or utility functions

logger = setup_logger()

class TranscriptionOptions(BaseModel):
    model_name: str = "medium"  
    compute_type: Optional[str] = "float16"

    @validator('model_name')
    def validate_model_name(cls, v):
        if v is not None and v not in MODEL_NAMES_DICT.keys():
            raise ValueError(f'{v} is not a valid model name.')
        return MODEL_NAMES_DICT[v]

    @validator('compute_type')
    def validate_compute_type(cls, v):
        if v is not None and v not in COMPUTE_TYPE_MAP.keys():
            raise ValueError(f'{v} is not a valid compute type.')
        return COMPUTE_TYPE_MAP[v]

app = FastAPI()

tasks_info = {}  # Global dictionary to store task information


TRANSCRIPTION_DIR = "static"
# Make sure the directory to hold the transcriptions exists.
os.makedirs(TRANSCRIPTION_DIR, exist_ok=True)
# Mount the 'static' directory
app.mount(f"/{TRANSCRIPTION_DIR}", StaticFiles(directory=TRANSCRIPTION_DIR), name=TRANSCRIPTION_DIR)

@app.get("/")
async def root():
    return {"message": "Hello from Tim!"}

@app.post("/transcribe/mp3")
async def transcribe_mp3(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    model_name: str = Form("medium"),  # Default value as the default form value
    compute_type: Optional[str] = Form("float16")  # Default value as the default form value
):
    task_id = create_task_id() 
    logger.debug(f"Created task_id: {task_id}")
    update_task_status(task_id, WorkflowStatus.NEW_TASK_TRANSCRIPTION,message=f"New Task id for transcribing mp3 file {file.name} is {task_id}")
    transcription_request = TranscriptionOptions(model_name=model_name, compute_type=compute_type)
    if not file:
         message = "No file was uploaded. Please check your inputs."
         logger.debug(message)
         return {"task_id": task_id, "message": message}
    # Generate a unique task ID
     # Generate a unique task ID
    # Store model_name and filename in the global dictionary
    tasks_info[task_id] = {"model_name": model_name, "filename": file.filename}

    temp_file_path = f"./temp_files/{file.filename}"
    # TODO: At some point we need to clean up the temp directory.
    logger.debug(f"temp_file_path for saving the mp3 file into a temporary directory: {temp_file_path}")
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

    # Save the file in the temporary directory
    # with open(temp_file_path, "wb") as temp_file:
    #     shutil.copyfileobj(file.file, temp_file)
    # Save the file in the temporary directory using aiofiles
    async with aiofiles.open(temp_file_path, 'wb') as out_file:
        content = await file.read()  # Read file content in chunks
        await out_file.write(content)  # Write to the file asynchronously
    # Add the transcription task to the background
    background_tasks.add_task(transcribe_and_cleanup, task_id, temp_file_path, transcription_request.model_name, transcription_request.compute_type)

    return {"task_id": task_id, "message": "Transcription starting..."}

@app.post("/youtube/download")
async def download_youtube_audio(
    background_tasks: BackgroundTasks, 
    yt_url: str = Form(...)
):
    """Endpoint to download YouTube audio as MP3 and upload to Google Drive."""
    # To get the GDRIVE_FOLDER_ID, go to the folder in the GDrive web interface and click on the folder.
    # The URL will look like this: https://drive.google.com/drive/folders/1234567890.  Where the numbers are the
    # GDRIVE_FOLDER_ID string.
    GDRIVE_FOLDER_ID = '1472rYLfk_V7ONqSEKAzr2JtqWyotHB_U'
    logger.debug(f"GDRIVE_FOLDER_ID: {GDRIVE_FOLDER_ID}")
    task_id = create_task_id()
    logger.debug(f"Created task_id: {task_id}")
    # Log the initiation of a new YouTube download task
    update_task_status(task_id, WorkflowStatus.NEW_TASK_DOWNLOAD,message=f"New Task id for downloading the YouTube audio from the url {yt_url} is {task_id}")

    # Initialize an instance of AudioToTranscript to handle the download
    yt_downloader = AudioToTranscript(task_id=task_id)
    
    # Add the download task to run in the background
    background_tasks.add_task(
        yt_downloader.download_youtube_audio_to_gdrive, 
        yt_url, 
        GDRIVE_FOLDER_ID, 
        update_task_status_callback=update_task_status
    )

    return {"task_id": task_id, "message": "YouTube audio download initiated. Check status for updates."}


async def download_and_transcribe(yt_url, task_id, model_name, compute_type):
    # Initialize the transcription class
    transcriber = AudioToTranscript(task_id=task_id, model_name=model_name, compute_type=compute_type)
    # Download the audio from YouTube
    download_folder = "temp_files"
    ret_code_message = await transcriber.adownload_youtube_audio(yt_url, download_folder)
    if ret_code_message['ret_code']!= 0:
        update_task_status(task_id, ret_code_message['message'])
        return

    mp3_filepath = ret_code_message['message']
    # Update tasks_info with the filename after download
    tasks_info[task_id]["filename"] = os.path.basename(mp3_filepath)

    # Proceed with transcription using the shared logic
    await transcribe_and_cleanup(task_id, mp3_filepath, model_name, compute_type)

async def transcribe_and_cleanup(task_id: str, file_path: str, model_name: str, compute_type: str):
    # Initialize the transcription class with a callback for status updates
    transcriber = AudioToTranscript(task_id=task_id, model_name=model_name, compute_type=compute_type)

    # Perform the transcription with progress updates
    transcription_text = await transcriber.atranscribe(file_path)
    transcription_path = _generate_transcript_path(task_id, tasks_info[task_id]["model_name"], tasks_info[task_id]["filename"])
# Save the transcription result to the file asynchronously
    async with aiofiles.open(transcription_path, "w") as output_file:
        await output_file.write(transcription_text)


    # Update status to indicate completion
    update_task_status(task_id, "Transcription completed.",filename=transcription_path)

    # Clean up the temporary audio file
    if os.path.exists(file_path):
        os.remove(file_path)

    status = get_task_status(task_id)
    if status is not None:
        return status
    print("Task status not found.")

# Endpoint to establish an SSE connection and start sending updates
@app.get("/status/{task_id}/stream")
async def status_stream(request: Request, task_id: str):
    async def event_generator():
        # Generate and send events to the client
        while True:
            # Wait for an update event
            await update_event.wait()
            # Clear the event to wait for the next update
            update_event.clear()
            # Check if there's an update for the specific task_id
            if task_id in status_dict:
                # Send the updated status to the client
                yield f"data: {json.dumps(status_dict[task_id])}\n\n"
            # Introduce a slight delay to prevent tight looping in case of rapid updates
    return EventSourceResponse(event_generator())

@app.get("/download/{task_id}")

async def download_file(task_id: str):

    transcription_path = _generate_transcript_path(task_id, tasks_info[task_id]["model_name"],tasks_info[task_id]["filename"])

    if os.path.exists(transcription_path):
        return Response(
            content=open(transcription_path, "rb").read(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={transcription_path.split('/')[-1]}",
            },
        )
    return {"error": "File not found"}

def _generate_transcript_path(task_id, model_name, filename):

    # Sanitize the filename to ensure it's safe for use in a file path
    # This is a basic form of sanitization. Depending on your needs, you might need more thorough sanitization.
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
    base_filename = os.path.basename(safe_filename)  # Ensure we only get the file name, not any directory path
    # Remove the file extension from base_filename
    filename_without_extension = os.path.splitext(base_filename)[0]
    # Construct the path
    transcript_filename = f"{filename_without_extension}_{model_name}_{task_id}.txt"
    transcript_path = os.path.join(TRANSCRIPTION_DIR, transcript_filename)
    return transcript_path

if __name__ == "__main__":


    uvicorn.run(app, host="127.0.0.1", port=8000)