from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import time

gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication.
drive = GoogleDrive(gauth)


folder_id = '1472rYLfk_V7ONqSEKAzr2JtqWyotHB_U'  # Replace with the ID of the folder you're monitoring

def list_files_in_folder(folder_id):
    """List all files in the specified Google Drive folder."""
    query = f"'{folder_id}' in parents and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    return {file['id']: file['title'] for file in file_list}

# Initially list files and remember the state
last_state = list_files_in_folder(folder_id)

while True:
    current_state = list_files_in_folder(folder_id)
    print(f"Current state: {current_state}")
    if current_state != last_state:
        print("Change detected!")
        added = [file for file in current_state if file not in last_state]
        if added:
            print("Added files:")
            for file_id in added:
                print(f"- {current_state[file_id]} (ID: {file_id})")
        last_state = current_state
    else:
        print("No change detected.")
    
    time.sleep(20)  # Check every 60 seconds
