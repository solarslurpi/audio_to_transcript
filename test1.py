from audio_transcriber_code import AudioTranscriber
from pydantic_models import TranscriptionOptionsWithUpload

options = TranscriptionOptionsWithUpload(
        audio_quality = "medium",
        compute_type = "float16",
        input_file = '1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5'
    )
at = AudioTranscriber()
transcription_text = at.transcribe(options)