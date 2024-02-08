import glob
import re
import os
import time
# from faster_whisper import WhisperModel
from shared import update_task_status, setup_logger
from workflowstatus_code  import WorkflowStatus
from transformers import pipeline
import torch
import asyncio
# yt_dlp is a fork of youtube-dl that has stayed current with the latest YouTube isms.  Youtube-dl is no longer
# supported so use yt_dlp.  It is more feature rich and up-to-date.
import yt_dlp as youtube_dl


# Define a mapping of return codes to messages used by the YouTube download module.
ret_code_messages = {
    0: "Placeholder for filename.",
    100: "[yt_dlp.download] Update required for yt-dlp, please restart.",
    101: "[yt_dlp.download] Download cancelled due to limits such as --max-downloads.",
    2: "[yt_dlp.download] There was an error with the user-provided options.",
    1: "[yt_dlp.download] An unexpected error occurred.",
    -1: "Expected MP3 file - {} - not found after download and processing.",
    -2: "Exception occured. Error:{} "
}


class AudioToTranscript:
    def __init__(
        self, task_id='', model_name="openai/whisper-large-v2",  compute_type=torch.float16):
        self.task_id = task_id
        self.model_name = model_name
        self.torch_compute_type = compute_type
        self.logger = setup_logger()


    async def atranscribe(self, audio_file):

        def transcribe_with_pipe():
            return pipe(audio_file, chunk_length_s=30, batch_size=8, return_timestamps=False)
        def load_pipeline():
            update_task_status(self.task_id, WorkflowStatus.TRANSCRIBING, messasge= f"Loading model {self.model_name}",logger=self.logger)
            pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device='cuda:0',
                torch_dtype=self.torch_compute_type
            )
            update_task_status (self.task_id, "Model loaded.")
            return pipe
        loop = asyncio.get_running_loop()
        # Update task status - this should ideally be an async function
        await loop.run_in_executor(None, update_task_status, self.task_id, WorkflowStatus.TRANSCRIBING,message=f"Starting processing {self.task_id}, logger=self.logger")
        # Process the audio file - This can also be a blocking call
        pipe = await loop.run_in_executor(None, load_pipeline)
        await loop.run_in_executor(None, update_task_status, self.task_id, WorkflowStatus.TRANSCRIBING,logger=self.logger)
        full_transcript = await loop.run_in_executor(None, transcribe_with_pipe)
        return full_transcript['text']

    async def adownload_youtube_audio(self, youtube_url: str, download_folder: str) -> str:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(download_folder, f"{self.task_id}_temp.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "verbose": True,
        }
        def _download():

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                try:
                    ret_code = ydl.download([youtube_url])
                    if ret_code != 0:
                        error_message = ret_code_messages.get(ret_code, "An unknown error occurred.")
                        self.logger.error(error_message)
                        # Return the error code and message
                        return {"ret_code": ret_code, "message": error_message}
                    else:
                        info = ydl.extract_info(youtube_url, download=False)
                        original_filename = os.path.join(download_folder, f"{self.task_id}_temp.mp3")
                        new_filename = os.path.join(
                            download_folder, self._sanitize_title(info["title"]) + f"_{self.task_id}.mp3"
                        )
                        if os.path.exists(original_filename):
                            os.replace(original_filename, new_filename)
                            self.logger.debug(f"File successfully downloaded and processed: {new_filename}")
                            # YAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAY
                            # YIPEE! It all worked....
                            # YAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAYAY
                            message = f"{new_filename}"
                            self.logger.debug(f"The file, {new_filename} has been successfully downloaded")
                            return {"ret_code": 0, "message": message}
                        else:
                            error_message = ret_code_messages.get(ret_code, "An unknown error occurred.").format("original_filename")

                            self.logger.error(error_message)
                            return {"ret_code": ret_code, "message": error_message}
                except Exception as e:
                    ret_code = -2
                    error_message = ret_code_messages.get(ret_code, "An unknown error occurred.").format(e)
                    self.logger.error(error_message)
                    return {"ret_code": ret_code, "message": error_message}

        loop = asyncio.get_running_loop()
        ret_code_message = await loop.run_in_executor(None, _download)
        return ret_code_message


    def _progress_hook(self, d):
        if d['status'] == 'finished':
            update_task_status(self.task_id, "Download complete")
        elif d['status'] == 'downloading':
            update_task_status(self.task_id, WorkflowStatus.DOWNLOADING, message=f"Downloading: {d['filename']}, {d['_percent_str']}, {d['_eta_str']}",logger=self.logger)
        else:
            update_task_status(self.task_id, f"{d['status']}")

    def _sanitize_title(self, title: str) -> str:
        # Replace spaces with underscores and remove unwanted characters
        sanitized_title = title.replace(" ", "_")
        sanitized_title = re.sub(r"[^\w\s-]", "", sanitized_title)
        return sanitized_title




    # Archiving, keeping just atranscribe() for now.
    # def transcribe(self, audio_file):
    #     # file_size = os.path.getsize(audio_file)

    #     update_task_status( self.task_id, f"Loading Whisper model {self.model_name}")
    #         # Initialize the ASR pipeline
    #     pipe = pipeline("automatic-speech-recognition",
    #                 model=self.model_name,
    #                 device='cuda:0',
    #                 torch_dtype=torch.float16)
    #     update_task_status( self.task_id, f"Whisper model {self.model_name} has been loaded.")
    #     full_transcript = pipe(audio_file, chunk_length_s=30, 
    #     batch_size=8, 
    #     return_timestamps=False)
    #     return full_transcript['text']

    # def download_youtube_audio(self, youtube_url: str, download_folder: str) -> str:
    #     ydl_opts = {
    #         "format": "bestaudio/best",
    #         "outtmpl": os.path.join(download_folder, "temp.%(ext)s"),
    #         "postprocessors": [
    #             {
    #                 "key": "FFmpegExtractAudio",
    #                 "preferredcodec": "mp3",
    #                 "preferredquality": "192",
    #             }
    #         ],
    #         "verbose": True,
    #     }
    #     with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    #         ydl.download([youtube_url])
    #         info = ydl.extract_info(youtube_url, download=False)
    #         try:
    #             original_filename = os.path.join(download_folder, "temp.mp3")
    #             new_filename = os.path.join(
    #                 download_folder, self._sanitize_title(info["title"]) + f"{self.task_id}" + .mp3"
    #             )
    #             os.replace(original_filename, new_filename)

    #         except Exception as e:
    #             print(f"An error occurred: {e}")
    #     return new_filename



    def _set_audios_list(self, audio_file_or_dir):
        if os.path.isdir(audio_file_or_dir):
            return glob.glob(os.path.join(audio_file_or_dir, "*.mp3"))
        elif os.path.isfile(audio_file_or_dir):
            return [audio_file_or_dir]
        else:
            raise ValueError("Either the audio file or the directory does not exist.")

    def _process_audio_fastapi_file(self, task_id, audio_file, model):
        
        # Assume transcription_segments is a list where the first item is a generator
        transcription_segments = model.transcribe(audio_file, beam_size=5)
        segments_generator = transcription_segments[0]
        
        # Initialize an empty list to collect segments
        segments_text = []
        processed_segments = 0 # keep updating for status reporting.
        update_interval = 10  # Update progress every 10 segments, for example
        # Convert the generator into a list of text segments using a list comprehension
        for segment in segments_generator:
            segments_text.append(segment.text)
            processed_segments += 1
            if processed_segments % update_interval == 0:
                update_task_status( self.task_id, f"Processed {processed_segments} segments...")
        # Join all segments into one string
        full_transcript = "".join(segments_text)
        
        # Return the full transcript text
        return full_transcript


    def _process_audio_file(self, audio_file, transcript_folder, model, start_time):
        name_part = os.path.splitext(os.path.basename(audio_file))[0]
        transcript_file = os.path.join(transcript_folder, name_part + ".txt")
        transcript_file = transcript_file.replace("\\", "/")
        if not os.path.isfile(transcript_file):
            transcription_segments = model.transcribe(audio_file, beam_size=5)
            if self.progress_callback:
                progress_percentage = self._figure_percent_complete(start_time)
                self.progress_callback(
                    "Starting transcription of text segments...", progress_percentage
                )
            cnt = 0
            with open(transcript_file, "w") as file:
                segments_generator = transcription_segments[0]
                for segment in segments_generator:
                    file.write(segment.text)
                    cnt += 1
                    if cnt % 10 == 0:
                        if self.progress_callback:
                            progress_percentage = self._figure_percent_complete(
                                start_time
                            )
                            self.progress_callback(
                                f"Processed a total of {cnt} text segments...",
                                progress_percentage,
                            )
                self.progress_callback(
                    f"{transcript_file} of {cnt} text segments complete.", 100
                )

    def _figure_percent_complete(self, start_time) -> int:
        elapsed_time = time.monotonic() - start_time
        progress_percentage = (elapsed_time / TYPICAL_TRANSCRIPTION_TIME) * 100
        progress_percentage = int(
            min(progress_percentage, 100)
        )  # Ensure it does not exceed 100%
        return progress_percentage
