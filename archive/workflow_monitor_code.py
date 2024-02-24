import asyncio
import httpx
from dotenv import load_dotenv
import json

from logger_code import LoggerBase
from settings_code import get_settings
from gdrive_helper_code import GDriveHelper
from file_tracker_store_code import FileTrackerStore
from workflow_status_model import GDriveID
from workflow_tracker_code import WorkflowTracker
from workflow_states_code import WorkflowStates
from workflow_error_code import handle_error 


# Load environment variables and settings
load_dotenv()




class WorkflowMonitor:
    def __init__(self):
        self.gh = GDriveHelper()
        self.logger = LoggerBase.setup_logger()
        self.tracker = WorkflowTracker()
        self.settings = get_settings()



    async def manage_transcription_workflow(self):
        mp3_files_list = await self.fetch_mp3_files_to_transcribe()
        self.transcribe_mp3s(mp3_files_list)
        # mp3_ids_in_status, mp3_ids_not_in_status = await self.determine_tracked_and_untracked_mp3s(mp3_files_list, task_status_list)
        # Run process_untracked_mp3s and process_reconciliation concurrently
        # await asyncio.gather(
        #     self.process_untracked_mp3s(mp3_ids_not_in_status),
        #     self.process_reconciliation(mp3_ids_in_status, task_status_list)
        # )
        # await self.process_untracked_mp3s(mp3_ids_not_in_status)

    async def fetch_mp3_files_to_transcribe(self):
        # Go to the mp3 file folder on GDrive
        self.logger.debug("Fetching mp3 files to transcribe.")
        mp3_folder_gdriveID = self.settings.gdrive_mp3_folder_id
        mp3_files_to_transcribe = await self.gh.list_files_to_transcribe(mp3_folder_gdriveID)
        # mp3_files_to_transcribe = await self.gh.list_files_to_transcribe(mp3_file_list)
        self.logger.debug(f"{len(mp3_files_to_transcribe)} mp3 files to transcribe.")
        return mp3_files_to_transcribe

    #     for mp3_file in mp3_file_list:
    #         try:
                
    #             file_status_dict = json.loads(mp3_file['description'])
    #         except json.JSONDecodeError: 
    #             # Add the file_status_dict to the gfile's description property.
    #             pass
    #         except Exception as e:
    #             pass # TODO: HANDLE EXCEPTION
    # async def fetch_mp3_and_task_list(self):
    #     self.logger.debug("Fetching mp3 and task list")
    #     mp3_file_list = await self.gh.list_files_in_folder(GDriveID.MP3_GDriveID.value)
    #     self.logger.debug(f"mp3_file_list: {mp3_file_list}")
    #     # Wrap the synchronous call in an executor to prevent blocking the event loop
    #     loop = asyncio.get_running_loop()
    #     self.logger.debug("About to call load_status_list.")
    #     task_status_list = await loop.run_in_executor(None, self.store.load_status_list)
    #     self.logger.debug(f"load_status_list returned: {task_status_list}")
    #     return mp3_file_list, task_status_list

    async def determine_tracked_and_untracked_mp3s(self, mp3_file_list, task_status_list):
        mp3_ids_in_status = {self.tracker.workflow_status.mp3_gdrive_id for status in task_status_list}
        self.logger.debug(f"mp3_ids_in_status: {mp3_ids_in_status}")
        mp3_ids_not_in_status = set(mp3_file_list.keys()) - mp3_ids_in_status
        self.logger.debug(f"mp3_ids_not_in_status: {mp3_ids_not_in_status  }")
        return mp3_ids_in_status, mp3_ids_not_in_status
    
    async def transcribe_mp3s(self,mp3_files_list):
        # Create a status entry in the transaction tracking store
        async def update_status_entry(mp3_id):
            try:
                self.tracker.workflow_status.status = WorkflowStates.TRANSCRIPTION_STARTING
                self.tracker.workflow_status.mp3_gdrive_id = mp3_id
                self.tracker.workflow_status.mp3_gdrive_filename= await self.gh.get_gdrive_filename(mp3_id)
                self.logger.debug(f"filename: {self.tracker.workflow_status.mp3_gdrive_filename}")
                await self.tracker.update_status()
            except Exception as e:
                await handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, message=f"Failed to get the mp3 filename based on GDrive ID: {e}", store=True)

        # Transcribe the mp3 file
        async def transcribe_mp3(mp3_id):
            data = {"gdrive_id": mp3_id}
            try:
                self.logger.debug("Sending a POST to the /transcribe/mp3 endppoint")
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.settings.transcription_url, data=data)
                self.logger.debug(f"response: {response}")
                if response.status_code != 200:
                    await handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, message=f"Transcription failed: {response.text}", store=True)
                else:
                    self.tracker.workflow_status.status = WorkflowStates.TRANSCRIPTION_STARTING
                    await self.tracker.update_status()
            except httpx.HTTPError as http_err:
                    await handle_error(status=WorkflowStates.TRANSCRIPTION_FAILED, message=f"Transcription failed: {http_err}", store=True)
            except Exception as e:
                await handle_error(operation="<unknown operation>", detail=mp3_id, system_error=str(e))  
        for mp3_gfile in mp3_files_list:
            self.logger.debug(f"before update_status_entry, : {mp3_gfile}")
            await update_status_entry(mp3_gfile)
            self.logger.debug("before transcribe_mp3")
            await transcribe_mp3(mp3_gfile['id'])
            self.logger.debug(f"**> TRANSCRiPtioN for mp3_id: {mp3_id} is complete.")

    async def process_reconciliation(self, mp3_ids_in_status, task_status_list):
        pass # TODO

    # Placeholder for additional methods like processing untracked files or reconciling task statuses

# async def main():
#     monitor = WorkflowMonitor()
#     await monitor.check_status()

# if __name__ == "__main__":
#     asyncio.run(main())
