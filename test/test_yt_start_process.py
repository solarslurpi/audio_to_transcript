import pytest

import app

@pytest.fixture
def valid_yt_url():
    return "https://www.youtube.com/watch?v=39h5Kj1fzU0"

@pytest.fixture
def invalid_yt_url():
    return "https://invalidurl.com"

def test_validate_youtube_url_valid(valid_yt_url):
    assert app.validate_yt_url(valid_yt_url) is True

def test_validate_youtube_url_invalid(invalid_yt_url):
    assert  app.validate_yt_url(invalid_yt_url) is False

@pytest.mark.asyncio
async def test_validate_start_download_process(valid_yt_url):
   message = await app.start_download_process(valid_yt_url)
   print(message)
