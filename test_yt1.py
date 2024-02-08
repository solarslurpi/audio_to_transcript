import yt_dlp
import requests
from io import BytesIO

def download_audio_stream(youtube_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'simulate': True,
        'extract_flat': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=False)
        audio_url = info_dict.get('url', None)
        if not audio_url:
            print("Failed to retrieve audio URL")
            return None

    # Now, use requests to fetch the audio content into memory
    response = requests.get(audio_url, stream=True)
    if response.status_code == 200:
        audio_bytes = BytesIO(response.content)
        print("Downloaded audio into memory.")
        return audio_bytes
    else:
        print(f"Failed to download audio, status code: {response.status_code}")
        return None

def main():
    youtube_url = 'https://www.youtube.com/watch?v=hV5LxlQMnwM'  # Replace with actual URL
    audio_bytes = download_audio_stream(youtube_url)
    if audio_bytes:
        # Do something with the audio bytes, e.g., save them to a file or process them
        # Example: Save to a file
        with open("downloaded_audio.mp3", "wb") as audio_file:
            audio_file.write(audio_bytes.getbuffer())
        print("Audio saved to downloaded_audio.mp3")

if __name__ == "__main__":
    main()
