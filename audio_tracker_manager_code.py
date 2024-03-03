import asyncio
import json

from gdrive_helper_code import GDriveHelper
from audio_transcriber_code import AudioTranscriber
from workflow_states_code import WorkflowEnum
from workflow_tracker_code import WorkflowTracker
from misc_utils import async_error_handler
from logger_code import LoggerBase
from env_settings_code import get_settings
from pydantic_models import GDriveInput

def init_WorkflowTracker_mp3(mp3_gdrive_id):
    WorkflowTracker.update(
    transcript_audio_quality= "medium",
    transcript_compute_type= "float16",

    input_mp3 = GDriveInput(gdrive_id=mp3_gdrive_id)

    )

@async_error_handler(error_message = 'Errored attempting to manage mp3 audio file transcription.')
async def main(delete_after_upload=False):
    logger = LoggerBase.setup_logger('AudioTranscriber Manager')
    gh = GDriveHelper()
    settings = get_settings()
    folder_id = settings.gdrive_mp3_folder_id
    files_to_process = await gh.list_files_to_transcribe(folder_id)
    logger.info(f"Number of Files to process: {len(files_to_process)}")

    for file in files_to_process:
        gdrive_input = GDriveInput(gdrive_id=file['id'])
        status_model = await gh.get_status_model(gdrive_input)
        logger.warning(f"\n---------\n {status_model.model_dump_json(indent=4)}")
        if status_model.status == WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name and delete_after_upload:
            await gh.delete_file(file['id'])
        elif status_model.status != WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name:
            # Transcribe mp3
            WorkflowTracker.update(
                status = status_model.status,
                input_mp3 = gdrive_input,
                transcript_audio_quality = status_model.transcript_audio_quality,
                transcript_compute_type = status_model.transcript_compute_type
            )
            transcriber = AudioTranscriber()
            await transcriber.transcribe()
        #     transcription_result = await audio_transcriber.transcribe()
        #     transcriber = AudioTranscriber()
        #     init_WorkflowTracker_mp3()
        #     await gdrive_helper.upload_transcription_result(transcription_result)
        #         await workflow_tracker.update_file_status(file['id'], WorkflowEnum.TRANSCRIPT_UPLOAD_COMPLETE.name)
        #         if delete_after_upload:
        #             await gdrive_helper.delete_file(file['id'])
        #     except Exception as e:
        #         await handle_error(e)
        #         continue

if __name__ == "__main__":
    asyncio.run(main(delete_after_upload=False))
