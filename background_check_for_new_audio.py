import asyncio

from pydrive2.drive import GoogleDrive
from shared import setup_logger
from file_transcription_tracker import FileTranscriptionTracker
# Path to your service account credential file



async def main():
    transcription_tracker = FileTranscriptionTracker()
    setup_logger()
    gauth = transcription_tracker.login_with_service_account()
    drive = GoogleDrive(gauth)
    

