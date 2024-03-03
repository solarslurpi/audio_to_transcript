import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from audio_to_transcript import AudioToTranscript
import os


# Function to update progress in the UI
def progress_update(message, progress_percentage):
    progress_var.set(f"{message} Progress: {progress_percentage}%")


# Function to handle transcription based on the UI inputs
def start_transcription():
    youtube_url = entry_youtube_url.get()
    mp3_file_path = file_path.get()
    transcript_folder = folder_path.get()

    # Validate if the transcript folder exists
    try:
        if not os.path.exists(transcript_folder):
            os.makedirs(transcript_folder)
    except OSError as error:
        messagebox.showerror(
            "Error", f"Error creating directory '{transcript_folder}': {error}"
        )
        return

    # Create an instance of AudioToTranscript
    audio_transcriber = AudioToTranscript(progress_callback=progress_update)

    try:
        # Check if YouTube URL is provided and download the audio
        if youtube_url:
            progress_update("Downloading audio from YouTube URL", 0)
            mp3_filename = audio_transcriber.download_youtube_audio(
                youtube_url, transcript_folder
            )
            audio_transcriber.transcribe(mp3_filename, transcript_folder)
        # Check if MP3 file is provided
        elif mp3_file_path:
            progress_update("Transcribing MP3 file", 0)
            audio_transcriber.transcribe(mp3_file_path, transcript_folder)
        else:
            messagebox.showwarning(
                "Warning", "Please enter a YouTube URL or select an MP3 file."
            )
    except Exception as e:
        messagebox.showerror("Error", str(e))


def select_file():
    filename = filedialog.askopenfilename(filetypes=[("MP3 Files", "*.mp3")])
    file_path.set(filename)


def select_folder():
    directory = filedialog.askdirectory()
    folder_path.set(directory)


def create_ui():
    # Create the main application window
    window = tk.Tk()
    window.title("Audio to Transcript Converter")

    global entry_youtube_url, file_path, folder_path, progress_var
    entry_youtube_url = tk.Entry(window, width=50)
    file_path = tk.StringVar()
    folder_path = tk.StringVar()
    progress_var = tk.StringVar()

    # Placing the widgets on the window
    tk.Label(window, text="YouTube Video or Playlist URL").pack(
        fill="x", padx=10, pady=2
    )
    entry_youtube_url.pack(fill="x", padx=10, pady=2)
    tk.Button(window, text="Or select mp3 file", command=select_file).pack(
        fill="x", padx=10, pady=2
    )
    tk.Button(window, text="Select transcript location", command=select_folder).pack(
        fill="x", padx=10, pady=2
    )
    tk.Button(
        window,
        text="Start",
        command=lambda: threading.Thread(target=start_transcription).start(),
    ).pack(padx=10, pady=5)
    tk.Label(window, text="Progress").pack(fill="x", padx=10, pady=2)
    tk.Label(window, textvariable=progress_var).pack(fill="x", padx=10, pady=2)

    # Start the event loop
    window.mainloop()


if __name__ == "__main__":
    create_ui()
