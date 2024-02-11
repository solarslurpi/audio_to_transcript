from shared import login_with_service_account
from pydrive2.drive import GoogleDrive

# This is the ID of the folder you want to upload the file to.
FOLDER_ID = '1472rYLfk_V7ONqSEKAzr2JtqWyotHB_U'
auth = login_with_service_account()
drive = GoogleDrive(auth)
# Create a 'test.txt' file for demonstration purposes.
with open('test.txt', 'w') as file:
    file.write('This is a test file.')

def upload_to_gdrive(file_name, folder_id):
    # Authenticate the client using a service account

    # Create a file on Google Drive
    file_metadata = {
        'title': file_name,
        'parents': [{'id': folder_id}]
    }
    gfile = drive.CreateFile(file_metadata)
    gfile.SetContentFile(file_name)
    gfile.Upload()

    print(f"Uploaded file with ID: {gfile['id']}")

# Call the function to upload 'test.txt' to the specified Google Drive folder
upload_to_gdrive('test.txt', FOLDER_ID)
