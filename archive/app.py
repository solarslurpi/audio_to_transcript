import asyncio
import uvicorn
import httpx

from fastapi import FastAPI,BackgroundTasks, Request, HTTPException
from pydantic import ValidationError
from sse_starlette.sse import EventSourceResponse

import gradio as gr



from pydantic_models import YouTubeUrl
from logger_code import LoggerBase

logger = LoggerBase.setup_logger('yt_download_app')


async def start_process(yt_url: str):
    try:
        if not validate_yt_url(yt_url):
            return "Please check the YouTube URL. Unable to validate the url."
        message_json = await start_download_process(yt_url) # The endpoint uses background tasks so will return fairly quickly. Once returned, we start up the SSE path.
        # TO DO next testable unit test.
        return message_json['message']

    except Exception as e:
        # Handle exceptions
        return {"error": str(e)}


async def start_download_process(yt_url: str) -> str:
    form_data = {"yt_url": yt_url}
    async with httpx.AsyncClient() as client:
        response = await client.post("http://127.0.0.1:8000/yt_download", data=form_data)
    # Check the response status
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to start the process")
    return response.json


def start_SSE_events():
    logger.debug("In start_SSE_events")

def process_YouTubeUrl():
    logger.debug("in process_YouTubeUrl")

app = FastAPI()
event_tracker = asyncio.Event()

# @app.get("/status_stream")
# async def status_stream(request: Request, event_state: str):
#     async def event_generator():
#         # Generate and send events to the client
#         while True:
#             # Wait for an update event
#             await event_tracker.wait()
#             # Clear the event to wait for the next update
#             event_tracker.clear()
#             # Check if there's an update for the specific task_id
#             yield f"{event_state}\n\n"
#             # Introduce a slight delay to prevent tight looping in case of rapid updates
#     return EventSourceResponse(event_generator())

@app.post("/yt_download")
async def download_youtube_audio(
     background_tasks: BackgroundTasks,
     yt_url: YouTubeUrl
 ):
    # background_tasks.add_task(start_SSE_events)
    # background_tasks.add_task(process_YouTubeUrl)
    # Start SSE events happening

#     try:
#         task_id = await _perform_task(
#             background_tasks,
#             YouTubeTransfer(tracker).download_youtube_audio_to_gdrive,
#             yt_url,
#             current_task="youtube_download"
#         )
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Error in processing the request: {e}")
    return {"message": "Starting Process"}



yt_downloader = gr.Interface(
    fn=start_process,
    inputs=gr.Textbox(label="Enter YouTube video URL", placeholder="e.g.: https://www.youtube.com/watch?v=39h5Kj1fzU0"),
    outputs=[gr.Textbox(label="Progress Update")],
    allow_flagging="never",
)

gr.mount_gradio_app(app, yt_downloader, path="/")

if __name__ == "__main__":

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
