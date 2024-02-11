

# from faster_whisper import WhisperModel
from file_transcription_tracker import FileTranscriptionTracker


from workflowstatus_code  import WorkflowStatus
from transformers import pipeline
import torch
import asyncio






class AudioToTranscript:
    def __init__(
        self, task_id='', model_name="openai/whisper-large-v2",  compute_type=torch.float16):
        self.task_id = task_id
        self.model_name = model_name
        self.torch_compute_type = compute_type
        self.tracker = FileTranscriptionTracker()
        self.downloaded_file_path = None # See _process_hook()


    async def atranscribe(self, audio_file):

        def transcribe_with_pipe():
            return pipe(audio_file, chunk_length_s=30, batch_size=8, return_timestamps=False)
        def load_pipeline():
            self.tracker.update_task_status(self.task_id, WorkflowStatus.TRANSCRIBING, messasge= f"Loading model {self.model_name}")
            pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device='cuda:0',
                torch_dtype=self.torch_compute_type
            )
            self.tracker.update_task_status (self.task_id, message="Model loaded.")
            return pipe
        loop = asyncio.get_running_loop()
        # Update task status - this should ideally be an async function
        # await loop.run_in_executor(None, self.update_task_status, self.task_id, WorkflowStatus.TRANSCRIBING,message=f"Starting processing {self.task_id}")
        # # Process the audio file - This can also be a blocking call
        # pipe = await loop.run_in_executor(None, load_pipeline)
        # await loop.run_in_executor(None, update_task_status, self.task_id, WorkflowStatus.TRANSCRIBING,logger=self.logger)
        # full_transcript = await loop.run_in_executor(None, transcribe_with_pipe)
        # return full_transcript['text']



 





