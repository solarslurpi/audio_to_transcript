from typing import Optional, Union
from pydantic import BaseModel, field_validator
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import uvicorn
import os
from audio_transcriber_code import AudioTranscriber
from pydantic_models import   GDriveInput
from workflow_tracker_code import AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP
from youtube_transfer import YouTubeTransfer
from logger_code import LoggerBase
from workflow_tracker_code import WorkflowTracker
from env_settings_code import Settings, get_settings
# from gdrive_helper_code import GDriveHelper
# from workflow_monitor_code import WorkflowMonitor

logger = LoggerBase.setup_logger()

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
    audio_quality: Optional[str] =  Settings().audio_quality_default,
    compute_type: Optional[str] = Settings().compute_type_default

    @field_validator('audio_quality')
    @classmethod
    def validate_audio_quality(cls, v):
        if v is not None and v not in AUDIO_QUALITY_MAP.keys():
            raise ValueError(f'{v} is not a valid model name.')
        return AUDIO_QUALITY_MAP[v]

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



@app.get("/view-settings")
async def view_settings(settings: Settings = Depends(get_settings)):
    return {
        "gdrive_mp3_folder_id": settings.gdrive_mp3_folder_id,
        "gdrive_transcripts_folder_id": settings.gdrive_transcripts_folder_id,
        "monitor_frequency_in_secs": settings.monitor_frequency_in_secs,
        "audio_quality_default": settings.audio_quality_default,
        "compute_type_default": settings.compute_type_default,
    }


@app.get("/")
async def root():
    return {"message": "Hello from Tim!"}

@app.post("/transcribe/mp3")
async def transcribe_mp3(
    background_tasks: BackgroundTasks,
    input_file: Union[UploadFile, GDriveInput] = Depends(process_input),
    audio_quality: Optional[str] = Form(Settings().audio_quality_default),
    compute_type: Optional[str] = Form(Settings().compute_type_default),
):
    try:
        background_tasks.add_task(AudioTranscriber().transcribe, input_file, audio_quality, compute_type)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in processing the request: {e}")
    wft = WorkflowTracker()
    return {"workflow_id": wft.workflow_status.id, "message": "Transcription task started. Check status for updates."}

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
            await tracker.event_tracker.wait()
            # Clear the event to wait for the next update
            tracker.event_tracker.clear()
            # Check if there's an update for the specific task_id
            yield f"{tracker.task_status.model_dump()}\n\n"
            # Introduce a slight delay to prevent tight looping in case of rapid updates
    return EventSourceResponse(event_generator())

# Define the common logic in a separate function
async def _perform_task(background_tasks: BackgroundTasks, task_func, *args, **kwargs):
    try:

        background_tasks.add_task(task_func, *args)
        state = "After adding task to background_tasks"
        return tracker.task_status.current_id
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred at state '{state}': {e}"
        )

# @app.post("/monitor/start")
# async def monitor_start(
#     background_tasks: BackgroundTasks,
#     gdrive_id_mp3: Optional[str] = Form(None),  # Marked as explicitly optional
#     gdrive_id_transcripts: Optional[str] = Form(None),  # Marked as explicitly optional
#     monitoring_frequency: Optional[int] = Form(None),  # Marked as explicitly optional
#     settings: Settings = Depends(get_settings)  # Get settings instance
# ):
#     # Use provided form data or fall back to settings if the form field is None
#     logger.debug("Starting code in monitor_start")
#     gdrive_id_mp3 = gdrive_id_mp3 if gdrive_id_mp3 is not None else settings.gdrive_mp3_folder_id
#     gdrive_id_transcripts = gdrive_id_transcripts if gdrive_id_transcripts is not None else settings.gdrive_transcripts_folder_id
#     monitoring_frequency = monitoring_frequency if monitoring_frequency is not None else settings.monitor_frequency_in_secs
#     ##################################
#     # vaidate access to GDrive folders
#     ##################################
#     try:
#         gdrive_helper = GDriveHelper()
#         if not await gdrive_helper.validate_gdrive_access(gdrive_id_mp3) or not await gdrive_helper.validate_gdrive_access(gdrive_id_transcripts):
#             raise HTTPException(status_code=400, detail="One or more GDrive folders are not accessible.")
#     except Exception as e:
#         logger.error(f"Error in validating access to GDrive folders: {e}")
#         raise HTTPException(status_code=400, detail=f"Error in validating access to GDrive folders: {e}")
#     logger.debug("Completed code in validating access to GDrive folers.")
#     ##################################
#     # manage_transcription_workflow
#     ##################################
#     try:
#         monitor = WorkflowMonitor()
#         logger.debug("Starting code in manage_transcription_workflow")
#         await monitor.manage_transcription_workflow()
#         logger.debug("Completed code in manage_transcription_workflow")
#     except Exception as e:
#         logger.error(f"Error in call to manage_transcription_workflow: {e}")
#         raise HTTPException(status_code=400, detail=f"Error in call to manage_transcription_workflow:  {e}")

#     # Logic to schedule or initiate the monitoring task
#     return {
#         "message": "Monitoring started",
#         "GDrive MP3 Folder ID": gdrive_id_mp3,
#         "GDrive Transcripts Folder ID": gdrive_id_transcripts,
#         "Monitoring Frequency": monitoring_frequency
#     }


if __name__ == "__main__":


    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)