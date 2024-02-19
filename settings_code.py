
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv
from typing import List


load_dotenv()

# Matches the variables in .env
class Settings(BaseSettings):
    gdrive_mp3_folder_id: str 
    gdrive_transcripts_folder_id: str
    monitor_frequency_in_secs: int
    audio_quality_default: str
    compute_type_default: str
    tracker_json_file_path : str
    google_service_account_credentials_path: str 
    google_drive_oauth_scopes: List[str]
    transcription_url: str
    

# Dependency that retrieves the settings
def get_settings() -> Settings:
    return Settings()