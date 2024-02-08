import yt_dlp as youtube_dl
import os

def progress_hook(d):
    if d['status'] == 'downloading':
        print(f"Downloading: {d['_percent_str']} of {d['_total_bytes_str']}")
    elif d['status'] == 'finished':
        print("Download complete")

def download_youtube_audio(youtube_url, download_folder):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(download_folder, 'temp.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'progress_hooks': [progress_hook],
    }
    
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

def main():
    # Example YouTube video URL
    youtube_url = 'https://www.youtube.com/watch?v=hV5LxlQMnwM'
    # Specify your download folder path here
    download_folder = './downloads'
    os.makedirs(download_folder, exist_ok=True)

    download_youtube_audio(youtube_url, download_folder)

if __name__ == "__main__":
    main()
