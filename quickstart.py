from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import requests
import time
# UGH!! I couldn't get this to work for a bit...wasted time...stupid:
# In "Authorized redirect URIs" field it must be "http://localhost:8080/" with a slash at end. 
# In "Authorized JavaScript origins" it must be "http://localhost:8080" without a slash.
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication.
drive = GoogleDrive(gauth)



def list_changes(access_token, page_token):
    url = 'https://www.googleapis.com/drive/v3/changes'
    params = {
        'pageToken': page_token,
        'spaces': 'drive'
    }
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        changes = response.json()
        for change in changes.get('changes', []):
            if 'file' in change:
                print(f"Change detected: {change['file'].get('name')} (ID: {change['file'].get('id')})")
        return changes.get('newStartPageToken')
    else:
        print(f"Failed to retrieve changes: {response.text}")
        return None

access_token = 'YOUR_ACCESS_TOKEN_HERE'  # Replace with your actual access token
start_page_token = 'YOUR_START_PAGE_TOKEN_HERE'  # Replace with your actual start page token

while True:
    new_start_page_token = list_changes(access_token, start_page_token)
    if new_start_page_token:
        print(f"New start page token: {new_start_page_token}")
        start_page_token = new_start_page_token
    else:
        print("No new start page token received, using the old one for the next check.")
    
    time.sleep(60)  # Wait for 60 seconds before checking again
