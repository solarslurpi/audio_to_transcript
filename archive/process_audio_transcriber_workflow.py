import asyncio
from workflow_status_model import GDriveID
from typing import List
from env_settings_code import get_settings
from gdrive_helper_code import GDriveHelper

async def _fetch_gfiles_to_transcribe()-> List[GDriveID]:
    # Get the list of mp3 files in the mp3 gfile folder.
    mp3_gdrive_id = get_settings().gdrive_mp3_folder_id
    gh = GDriveHelper()
    gfile_list = await gh.list_files_to_transcribe(mp3_gdrive_id)
    print(gfile_list)

    pass

async def main():
    # Get the list of mp3 files in the mp3 gfile folder.
    # check the status of the files.
    # if state < TRANSCRIPTION_COMPLETE, add the file to a list of files to start the process on.
    # for each member in the list, transcribe using the code that has been written.
    # Stope
    await _fetch_gfiles_to_transcribe()



if __name__ == "__main__":
    asyncio.run(main())