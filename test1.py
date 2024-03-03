import asyncio
import json

from typing import Union
from gdrive_helper_code import GDriveHelper
from env_settings_code import get_settings

gh = GDriveHelper()
async def main(delete_after_upload=False):

    settings = get_settings()
    folder_id = settings.gdrive_mp3_folder_id
    files_to_process = await gh.list_files_to_transcribe(folder_id)
    for file in files_to_process:
        status_model = await gh.get_status_model(file['id'])
        print(status_model.model_dump_json(indent=4))


if __name__ == "__main__":
    asyncio.run(main(delete_after_upload=False))