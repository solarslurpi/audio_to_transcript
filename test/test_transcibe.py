import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from workflow_states_code import WorkflowEnum
from audio_transcriber_code import AudioTranscriber
import torch

@pytest.fixture
def mp3_test_path():
    windows_file_path = r'C:\Users\happy\Documents\Projects\audio_to_transcript\test\test.mp3'
    return Path(windows_file_path)

@pytest.mark.asyncio
@patch("workflow_tracker_code.WorkflowTracker.handle_error", new_callable=AsyncMock)
async def test_transcribe_mp3_invalid_path(mock_handle_error):
    transcriber = AudioTranscriber()
    invalid_path = Path("/invalid/path/to/audio.mp3")

    await transcriber._transcribe_mp3(audio_file_path=invalid_path, audio_quality="medium", compute_type="float32")

    mock_handle_error.assert_awaited_once_with(
        status=WorkflowEnum.TRANSCRIPTION_FAILED,
        error_message=f"Audio file does not exist or is not a file: {invalid_path}",
        operation="_transcribe_mp3",
        store=True,
        raise_exception=True
    )
@pytest.mark.asyncio
async def test_transcribe_mp3_unsupported_audio_quality(mp3_test_path, caplog):
    transcriber = AudioTranscriber()
    valid_path = mp3_test_path
    unsupported_quality = "ultra_high"  # Example of unsupported audio quality

    await transcriber._transcribe_mp3(audio_file_path=valid_path, audio_quality=unsupported_quality, compute_type="float32")

    # Check for fallback to default audio quality in the warning log
    default_quality = transcriber.settings.audio_quality_default
    assert any(f"Unsupported audio quality '{unsupported_quality}'. Falling back to default: {default_quality}." in message for message in caplog.messages), "Warning for unsupported audio quality fallback not logged as expected."

@pytest.mark.asyncio
async def test_transcribe_mp3_unsupported_compute_type(mp3_test_path, caplog):
    transcriber = AudioTranscriber()
    valid_path = mp3_test_path  # Again, assuming this exists for the sake of the test
    unsupported_compute = "quantum"  # Example of unsupported compute type

    await transcriber._transcribe_mp3(audio_file_path=valid_path, audio_quality="medium", compute_type=unsupported_compute)

    # Check for fallback to default compute type in the warning log
    default_compute = transcriber.settings.compute_type_default
    assert any(f"Unsupported compute type '{unsupported_compute}'. Falling back to default: {default_compute}." in message for message in caplog.messages), "Warning for unsupported compute type fallback not logged as expected."


@pytest.mark.asyncio
@patch("audio_transcriber_code.AudioTranscriber._transcribe_pipeline")
async def test_transcribe_success(mock_transcribe_pipeline, mp3_test_path):
    # Setup
    transcriber = AudioTranscriber()
    mock_transcribe_pipeline.return_value = {'text': "Transcribed text"}
    audio_file_path = mp3_test_path
    audio_quality = "medium"
    compute_type = "float16"

    # Exercise
    transcription_text = await transcriber._transcribe_mp3(audio_file_path, audio_quality, compute_type)

    # Verify
    mock_transcribe_pipeline.assert_called_once()
    assert transcription_text == "Transcribed text", "Transcription text should match the expected output"

    # Clean up - None needed for this test

# @pytest.mark.asyncio
# @patch("audio_transcriber_code.AudioTranscriber._transcribe_pipeline")
# async def test_transcribe_failure(mock_transcribe_pipeline, mp3_test_path, mocker):
#     # Setup
#     transcriber = AudioTranscriber()
#     mock_transcribe_pipeline.side_effect = Exception("Transcription failed")
#     audio_file_path = mp3_test_path
#     audio_quality = "medium"
#     compute_type = "float16"

#     # Mock the error handling to avoid side effects
#     mocker.patch.object(transcriber.tracker, 'handle_error', new_callable=AsyncMock)

#     # Exercise and verify
#     with pytest.raises(Exception, match="Transcription failed"):
#         await transcriber._transcribe_mp3(audio_file_path, audio_quality, compute_type)

#     # Ensure error handling was invoked
#     transcriber.tracker.handle_error.assert_called_once()

@patch("audio_transcriber_code.AudioTranscriber._transcribe_pipeline")
@pytest.mark.asyncio
async def test_transcribe_failure(mock_transcribe_pipeline, mp3_test_path, mocker):
    # By mocking the _transcribe_pipeline() to throw an exception and then checking that handle_error was called with the expected parameters,
    # we are ensuring that the error handling pathways are functioning as intended.
    # Setup
    transcriber = AudioTranscriber()
    mock_transcribe_pipeline.side_effect = Exception("Transcription failed")

    # Mock the error handling to capture its invocation
    mock_handle_error = mocker.patch.object(transcriber.tracker, 'handle_error', new_callable=AsyncMock)

    # Attempt to transcribe, expecting no exception to be raised to this level
    await transcriber._transcribe_mp3(mp3_test_path, "medium", "float16")

    # Verify that handle_error was called as expected
    mock_handle_error.assert_awaited_once_with(
        status=WorkflowEnum.TRANSCRIPTION_FAILED,
        error_message="Transcription failed",
        operation="_transcribe_mp3",
        store=True,
        raise_exception=True
    )

@pytest.mark.asyncio
@patch("audio_transcriber_code.AudioTranscriber._transcribe_pipeline")
async def test_transcribe_mp3_success(mock_transcribe_pipeline, mp3_test_path):
    """
    Tests successful MP3 transcription simulation by mocking the transcription pipeline.

    Verifies that _transcribe_mp3 method correctly invokes the transcription pipeline with expected parameters (file path, model name, compute type)
    and processes its mock return value. Ensures integration and parameter passing within AudioTranscriber are functioning as intended,
    without actually performing any real transcription.

    Args:
    - mock_transcribe_pipeline: Mock of the transcription pipeline method.
    - mp3_test_path: Path to the test MP3 file.
    """
    # Setup
    transcriber = AudioTranscriber()
    mock_transcribe_pipeline.return_value = {'text': "Expected transcription text"}

    # Exercise
    result_text = await transcriber._transcribe_mp3(mp3_test_path, "medium", "float32")

    # Verify
    mock_transcribe_pipeline.assert_called_once_with(mp3_test_path, "openai/whisper-medium", torch.float32)
    assert result_text == "Expected transcription text", "The transcription text does not match the expected output."

@pytest.mark.asyncio
@patch("audio_transcriber_code.AudioTranscriber._transcribe_pipeline")
async def test_transcribe_mp3_handles_pipeline_exception(mock_transcribe_pipeline, mp3_test_path, mocker):
    """
    Tests that _transcribe_mp3 properly handles exceptions from the transcription pipeline,
    by verifying that it calls the error handling mechanism correctly when an exception occurs during transcription.
    This includes handling errors for file validation and transcription process separately.
    """
    # Setup: Instantiate the transcriber and mock the transcription pipeline to raise an exception
    transcriber = AudioTranscriber()
    mock_transcribe_pipeline.side_effect = Exception("Mock transcription failure")

    # Mock the error handler to capture its invocation without real side effects
    mock_handle_error = mocker.patch.object(transcriber.tracker, 'handle_error', new_callable=mocker.AsyncMock)

    # Input parameters for the _transcribe_mp3 method
    mp3_file_path = Path("/fake/path/to/audio.mp3")
    audio_quality = "medium"
    compute_type = "float32"

    # Exercise: Call the method under test, which is expected to handle the exception
    await transcriber._transcribe_mp3(mp3_file_path, audio_quality, compute_type)

    # Verify: Ensure the error handler was called correctly
    # Since `handle_error` can be called more than once, check for at least one call with expected parameters
    mock_handle_error.assert_any_await(
        status=WorkflowEnum.TRANSCRIPTION_FAILED,
        error_message="Mock transcription failure",
        operation="_transcribe_mp3",
        store=True,
        raise_exception=True
    )
    # Additionally, you might want to verify the total number of calls if that's relevant to your test
    assert mock_handle_error.await_count == 2, "handle_error should have been awaited twice."
