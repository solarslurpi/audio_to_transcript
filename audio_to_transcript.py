import glob
import re
import os
import time
from faster_whisper import WhisperModel
from shared import update_task_status

# yt_dlp is a fork of youtube-dl that has stayed current with the latest YouTube isms.  Youtube-dl is no longer
# supported so use yt_dlp.  It is more feature rich and up-to-date.
import yt_dlp as youtube_dl
from common import MODEL_SIZES, COMPUTE_TYPES

TYPICAL_TRANSCRIPTION_TIME = (
    15 * 60
)  # Wild guess that the total amount of time it typically takes to audio transcribe is 10 minutes.


class AudioToTranscript:
    def __init__(
        self, task_id, model_name="large-v2", compute_type="int8", 
    ):
        self.task_id = task_id
        self.model_name = model_name
        if self.model_name not in MODEL_SIZES:
            raise ValueError(f"Model should be one of {MODEL_SIZES}")
        self.compute_type = compute_type
        if self.compute_type not in COMPUTE_TYPES:
            raise ValueError(f"Compute type should be one of {COMPUTE_TYPES}")

    def transcribe(self, audio_file):
        # file_size = os.path.getsize(audio_file)
        update_task_status( self.task_id, f"Loading Whisper model {self.model_name}")
        model = WhisperModel(
            self.model_name, compute_type=self.compute_type, device="cuda"
        ) 
        update_task_status( self.task_id, f"Whisper model {self.model_name} has been loaded.")
        full_transcript = self._process_audio_fastapi_file(self.task_id, audio_file, model)
        return full_transcript

    def download_youtube_audio(self, youtube_url: str, download_folder: str) -> str:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(download_folder, "temp.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "verbose": True,
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
            info = ydl.extract_info(youtube_url, download=False)
            try:
                original_filename = os.path.join(download_folder, "temp.mp3")
                new_filename = os.path.join(
                    download_folder, self._sanitize_title(info["title"]) + ".mp3"
                )
                os.replace(original_filename, new_filename)

            except Exception as e:
                print(f"An error occurred: {e}")
        return new_filename

    def _sanitize_title(self, title: str) -> str:
        # Replace spaces with underscores
        sanitized_title = title.replace(" ", "_")
        # Remove unwanted characters using regular expression
        sanitized_title = re.sub(r"[^\w\s-]", "", sanitized_title)
        return sanitized_title

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
        segments_text = [segment.text for segment in segments_generator]
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
