import requests

from shared import  setup_logger, BASE_URL,listen_for_status_updates

logger = setup_logger()

def main():
    yt_download_endpoint = f"{BASE_URL}/youtube/download"
    # Example YouTube video URL
    youtube_url = 'https://www.youtube.com/watch?v=hV5LxlQMnwM'

    data = {
        'yt_url': youtube_url,
    }
    # Specify your download folder path here
    with requests.Session() as session:
        response = session.post(yt_download_endpoint, data=data, stream=True)
        if response.ok:
            task_id = response.json().get('task_id')
            listen_for_status_updates(task_id,logger)



if __name__ == "__main__":
    main()
