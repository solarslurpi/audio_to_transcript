# Check if a directory on GDrive has an mp3 file added. 
from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import time

# Authenticate with service account credentials
gauth = GoogleAuth()
scope = ['https://www.googleapis.com/auth/drive']
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('/path/to/service_account.json', scope)
drive = GoogleDrive(gauth) 

# Folder ID of the Google Drive directory to monitor
folder_id = '1234567890abcdefghijklmnopqrstuvwxyz'

# Get initial list of files in folder
file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(folder_id)}).GetList()
initial_files = set([f['title'] for f in file_list])

while True:
  # Get current list of files
  file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(folder_id)}).GetList()
  current_files = set([f['title'] for f in file_list])
  
  # Check if any new MP3 files were added
  new_files = current_files - initial_files
  if any([f.endswith('.mp3') for f in new_files]):
    print('New MP3 file added!')
    # Do something with the new file

  # Update initial file list  
  initial_files = current_files

  # Check again after 60 seconds
  time.sleep(60)
