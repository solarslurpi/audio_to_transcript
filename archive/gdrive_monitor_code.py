import asyncio
from gdrive_helper_code import GDriveHelper
from logger_code import LoggerBase
from settings_code import get_settings
from dotenv import load_dotenv
import requests

class GDriveMonitor:
    def __init__(self, mp3_folder_id, transcription_folder_id):
        self.mp3_folder_id = mp3_folder_id
        self.transcription_folder_id = transcription_folder_id
        self.gdrive_helper = GDriveHelper()
        self.logger = LoggerBase.setup_logger()
        self.last_state = {}
        load_dotenv()
        settings = get_settings()
        self.monitor_frequency_in_secs = settings.monitor_frequency_in_secs

    async def monitor_changes(self):
        while True:
            try:
                current_file_list = await asyncio.to_thread(self.gdrive_helper.list_files_in_folder, self.mp3_folder_id)
                added = [file_id for file_id in current_file_list if file_id not in self.last_state]
                if added:
                    for file_id in added:
                        await self.initiate_transcription(file_id, current_file_list[file_id])
                    self.last_state = current_file_list
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                raise
            await asyncio.sleep(self.monitor_frequency_in_secs)

    async def initiate_transcription(self, file_id, file_title):
        try:
            response = requests.post("http://your_transcription_service_url/transcribe/mp3", json={"gdrive_id": file_id})
            if response.status_code == 200:
                self.logger.info(f"Transcription initiated for {file_title} (ID: {file_id})")
            else:
                self.logger.error(f"Failed to initiate transcription for {file_title} (ID: {file_id})")
        except Exception as e:
            self.logger.error(f"Error initiating transcription for {file_title} (ID: {file_id}): {e}")
            raise

async def main():
    mp3_folder_id = 'your_mp3_google_drive_folder_id_here'
    transcription_folder_id = 'your_transcription_google_drive_folder_id_here'
    monitor = GDriveMonitor(mp3_folder_id, transcription_folder_id)
    await monitor.monitor_changes()

if __name__ == '__main__':
    asyncio.run(main())
