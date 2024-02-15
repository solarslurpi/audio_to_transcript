from typing import Optional, Union
from pydantic import BaseModel, field_validator
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import uvicorn
import os
from audio_to_transcript import AudioToTranscript, AUDIO_QUALITY_DICT, COMPUTE_TYPE_MAP
from youtube_transfer import YouTubeTransfer
from logger_code import LoggerBase
from file_transcription_tracker import FileTranscriptionTracker
from audio_to_transcript import GDriveInput
from dotenv import load_dotenv

# Add any other imports you might need for your custom logic or utility functions

logger = LoggerBase.setup_logger()
tracker = FileTranscriptionTracker()

AUDIO_QUALITY_DEFAULT = os.getenv('AUDIO_QUALITY_DEFAULT')
COMPUTE_TYPE_DEFAULT = os.getenv ("COMPUTE_TYPE_DEFAULT")

load_dotenv()

app = FastAPI()

# Dependency to process the input and decide whether it's a file upload or a Google Drive ID
async def process_input(
    file: Optional[UploadFile] = File(None), 
    gdrive_id: Optional[str] = Form(None),
) -> Union[UploadFile, GDriveInput]:
    if file and gdrive_id:
        raise HTTPException(status_code=400, detail="Please submit either a file or a gdrive_id, not both.")
    if not file and not gdrive_id:
        raise HTTPException(status_code=400, detail="Please submit either a file or a gdrive_id.")
    return file if file else GDriveInput(gdrive_id=gdrive_id)

class TranscriptionOptions(BaseModel):
    audio_quality: Optional[str] =  AUDIO_QUALITY_DEFAULT,
    compute_type: Optional[str] = COMPUTE_TYPE_DEFAULT

    @field_validator('audio_quality')
    @classmethod
    def validate_audio_quality(cls, v):
        if v is not None and v not in AUDIO_QUALITY_DICT.keys():
            raise ValueError(f'{v} is not a valid model name.')
        return AUDIO_QUALITY_DICT[v]

    @field_validator('compute_type')
    @classmethod
    def validate_compute_type(cls, v):
        if v is not None and v not in COMPUTE_TYPE_MAP.keys():
            raise ValueError(f'{v} is not a valid compute type.')
        return COMPUTE_TYPE_MAP[v]

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
    input_file: Union[UploadFile, GDriveInput] = Depends(process_input),
    audio_quality: Optional[str] = Form(AUDIO_QUALITY_DEFAULT),
    compute_type: Optional[str] = Form(COMPUTE_TYPE_DEFAULT)
):
    try:
        task_id = await _perform_task(
            background_tasks, 
            AudioToTranscript(tracker).transcribe, 
            input_file, 
            audio_quality, 
            compute_type, 
            current_task="transcription"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in processing the request: {e}")
    return {"task_id": task_id, "message": "Transcription task started. Check status for updates."}

@app.post("/youtube/download")
async def download_youtube_audio(
    background_tasks: BackgroundTasks, 
    yt_url: str = Form(...)
):
    try:
        task_id = await _perform_task(
            background_tasks, 
            YouTubeTransfer(tracker).download_youtube_audio_to_gdrive, 
            yt_url, 
            current_task="youtube_download"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in processing the request: {e}")
    return {"task_id": task_id, "message": "YouTube audio download initiated. Check status for updates."}



# Endpoint to establish an SSE connection and start sending updates
@app.get("/status/{task_id}/stream")
async def status_stream(request: Request, task_id: str):
    async def event_generator():
        # Generate and send events to the client
        while True:
            # Wait for an update event
            await tracker.update_event.wait()
            # Clear the event to wait for the next update
            tracker.update_event.clear()
            # Check if there's an update for the specific task_id
            yield f"{tracker.task_status.model_dump()}\n\n"
            # Introduce a slight delay to prevent tight looping in case of rapid updates
    return EventSourceResponse(event_generator())

# Define the common logic in a separate function
async def _perform_task(background_tasks: BackgroundTasks, task_func, *args, **kwargs):
    try:
        state = "Before start_task_tracking"
        tracker.start_task_tracking(current_task=kwargs.get("current_task", "unknown"))
        state = "After start_task_tracking"
        tracker.create_task_id()    
        state = "After create_task_id"
        state = "After initializing the task object"
        
        background_tasks.add_task(task_func, *args)
        state = "After adding task to background_tasks"
        return tracker.task_status.current_id
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred at state '{state}': {e}"
        )

if __name__ == "__main__":


    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)