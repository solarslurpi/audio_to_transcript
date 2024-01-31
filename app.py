from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, Response
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import uvicorn
import asyncio
import os
import shutil
import json
from audio_to_transcript import AudioToTranscript
from shared import create_task_id, get_task_status, update_task_status, status_dict
# Add any other imports you might need for your custom logic or utility functions

app = FastAPI()
TRANSCRIPTION_DIR = "static"
# Mount the 'static' directory
app.mount(f"/{TRANSCRIPTION_DIR}", StaticFiles(directory=TRANSCRIPTION_DIR), name=TRANSCRIPTION_DIR)
@app.post("/transcribe/mp3")
async def transcribe_mp3(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file:
         return {"error": "Should have received a file?..."}
    # Generate a unique task ID
    task_id = create_task_id()  # Generate a unique task ID
    # Need to store the task_id for status update...
    update_task_status(task_id, "Initializing mp3 transcription")
    temp_file_path = f"./temp_files/{file.filename}"
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

    # Save the file in the temporary directory
    with open(temp_file_path, "wb") as temp_file:
        shutil.copyfileobj(file.file, temp_file)

    # Add the transcription task to the background
    background_tasks.add_task(transcribe_and_cleanup, task_id, temp_file_path)

    return {"task_id": task_id, "message": "Transcription starting..."}


async def transcribe_and_cleanup(task_id: str, file_path: str):
    # Initialize the transcription class with a callback for status updates
    transcriber = AudioToTranscript(task_id=task_id)

    # Perform the transcription with progress updates
    transcription_result = transcriber.transcribe(file_path)
    output_filename = os.path.join(TRANSCRIPTION_DIR, f"{task_id}.txt")

    # Save the transcription result to the file
    with open(output_filename, "w") as output_file:
        output_file.write(transcription_result)

    # Update status to indicate completion
    update_task_status(task_id, "Transcription completed.",filename=output_filename)

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
            if task_id in status_dict:
                yield f"{json.dumps(status_dict[task_id])}\n\n"
            await asyncio.sleep(1)  # Interval between updates
    return EventSourceResponse(event_generator())

@app.get("/download/{filename}")

async def download_file(filename: str):

    file_path = os.path.join(TRANSCRIPTION_DIR, filename)
    if os.path.exists(file_path):
        return Response(
            content=open(file_path, "rb").read(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )
    return {"error": "File not found"}




if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
