import asyncio

from gdrive_helper_code import GDriveHelper
from audio_transcriber_code import AudioTranscriber
from workflow_states_code import WorkflowEnum
from workflow_error_code import handle_error
from logger_code import LoggerBase
from workflow_tracker_code import WorkflowTracker

async def main(delete_after_upload=False):
    logger = LoggerBase.setup_logging('AudioTranscriber Manager')
    gdrive_helper = GDriveHelper()
    audio_transcriber = AudioTranscriber()

    files_to_process = await gdrive_helper.list_files_in_folder('folder_id')

    for file in files_to_process:
        status = await workflow_tracker.get_file_status(file['id'])
        if status == WorkflowEnum.TRANSCRIPT_UPLOAD_COMPLETE.name and delete_after_upload:
            await gdrive_helper.delete_file(file['id'])
        elif status.needs_transcription():
            try:
                transcription_result = await audio_transcriber.transcribe_file(file)
                await gdrive_helper.upload_transcription_result(transcription_result)
                await workflow_tracker.update_file_status(file['id'], WorkflowEnum.TRANSCRIPT_UPLOAD_COMPLETE.name)
                if delete_after_upload:
                    await gdrive_helper.delete_file(file['id'])
            except Exception as e:
                await handle_error(e)
                continue

if __name__ == "__main__":
    asyncio.run(main(delete_after_upload=True))
