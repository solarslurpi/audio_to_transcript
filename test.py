from workflow_status_model import TranscriptionStatus
import json




transcription_status = TranscriptionStatus()
print(transcription_status.dict())
with open("test.json", 'w') as file:
    json.dump(transcription_status.dict(), file, indent=4)

