from fastapi import FastAPI, Form, BackgroundTasks
import uvicorn
from audio_to_transcript import AudioToTranscript
from shared import create_task_id, update_task_status, WorkflowStatus

app = FastAPI()

# Directory where transcriptions will be stored
TRANSCRIPTION_DIR = "static"
# Your Google Drive folder ID where MP3 files will be saved
GDRIVE_FOLDER_ID = "your_gdrive_folder_id_for_mp3_files"

@app.get("/")
async def root():
    """Root endpoint to check service availability."""
    return {"message": "Hello from Tim's transcription service!"}

@app.post("/youtube/download")
async def download_youtube_audio(
    background_tasks: BackgroundTasks, 
    yt_url: str = Form(...)
):
    """Endpoint to download YouTube audio as MP3 and upload to Google Drive."""
    task_id = create_task_id()
    
    # Log the initiation of a new YouTube download task
    update_task_status(task_id, WorkflowStatus.NEW_TASK_DOWNLOAD)

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

# Ensure the TRANSCRIPTION_DIR exists
@app.on_event("startup")
async def startup_event():
    os.makedirs(TRANSCRIPTION_DIR, exist_ok=True)
    app.mount(f"/{TRANSCRIPTION_DIR}", StaticFiles(directory=TRANSCRIPTION_DIR), name=TRANSCRIPTION_DIR)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
