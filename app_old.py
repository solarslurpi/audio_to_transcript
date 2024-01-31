from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel
from audio_to_transcript import AudioToTranscript
import uvicorn
import os
import shutil
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from shared import create_task_id, update_task_progress, get_task_status, progress_store

app = FastAPI()



class YTTranscriptionRequest(BaseModel):
    youtube_url: str = None
    transcript_folder: str


@app.get("/")
def read_root():
    return {"message": "Welcome to the Audio to Transcript API"}
@app.post("/transcribe/youtube")
def transcribe_youtube(request: YTTranscriptionRequest):
    if not request.youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    transcriber = AudioToTranscript()  # Initialize the transcriber
    mp3_filename = transcriber.download_youtube_audio(request.youtube_url, request.transcript_folder)
    transcript = transcriber.transcribe(mp3_filename, request.transcript_folder)
    return Response(content=transcript, media_type="text/plain")


@app.post("/transcribe/mp3")
async def transcribe_mp3(file: UploadFile = File(...)):
    task_id = create_task_id()
    update_task_progress(f"Initializing mp3 transcription. Task id: {task_id}")
    transcriber = AudioToTranscript(task_id=task_id)  # Initialize the transcriber

    # Create a temporary file path
    temp_file_path = f"./temp_files/{file.filename}"

    # Ensure the directory exists
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
    
    try:
        # Save the uploaded file to the temporary file path
        with open(temp_file_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)
        loop = asyncio.get_event_loop()
        progress_store[task_id] = {"status": "Starting to process mp3."}
        with ThreadPoolExecutor() as executor:
        # Use the actual file path for processing
            future = loop.run_in_executor(executor, transcriber.transcribe, task_id, temp_file_path)
            transcript = await future  # Await the result without blocking the event loop
        
        # Clean up the temporary file
        os.remove(temp_file_path)
    except Exception as e:
        # Clean up and raise an exception if anything goes wrong
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))
    
    return Response(content=transcript, media_type="text/plain")

@app.post("/get_task_id")
async def initiate_transcription(file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    progress_store[task_id] = {"status": "Transcription initiated"}
    
    # Code to start the transcription process (possibly as a background task)

    return {"task_id": task_id}

@app.get("/status/{task_id}")
def get_status(task_id: str):
    status = get_task_status(task_id)
    if status is not None:
        return status
    raise HTTPException(status_code=404, detail="Task not found")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
