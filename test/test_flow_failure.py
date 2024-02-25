import pytest
from audio_transcriber_code import AudioTranscriber, GDriveInput
from unittest.mock import AsyncMock

@pytest.fixture
def mock_verify_and_prepare_mp3_failure(mocker, caplog):
    # FLOW: Start transcription workflow. - Fail to verify and prepare MP3
    mocker.patch.object(AudioTranscriber, '_verify_and_prepare_mp3', side_effect=Exception("Failed to load MP3"))
    mocker.patch.object(AudioTranscriber, 'start_transcription', new_callable=AsyncMock)

@pytest.mark.asyncio
async def test_load_mp3_failure(mock_verify_and_prepare_mp3_failure, caplog):
    transcriber = AudioTranscriber()
    with pytest.raises(Exception) as exc_info:
        await transcriber.transcribe(GDriveInput(gdrive_id="fake_id"), "medium", "float16")
    assert "Failed to load MP3" in str(exc_info.value)
    # Assert start_transcription was never called
    transcriber.start_transcription.assert_not_called()
    # Check for expected log message
    assert "Failed to verify and prepare MP3" in caplog.text
