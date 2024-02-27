from fastapi import UploadFile
from pathlib import Path
from io import BytesIO

# Function to convert a Path object to an UploadFile object
def path_to_upload_file(path: Path) -> UploadFile:
    # Read the binary content of the file
    file_content = path.read_bytes()
    # Create a BytesIO object from the binary content
    file_like = BytesIO(file_content)
    # Create an UploadFile object. The filename and content_type can be adjusted as needed.
    upload_file = UploadFile(filename=path.name, file=file_like)
    return upload_file

# Example usage
if __name__ == "__main__":
    # Specify your file path here
    file_path = Path(r"C:\Users\happy\Documents\Projects\audio_to_transcript\temp_mp3s\test.mp3")
    
    # Convert Path object to UploadFile
    upload_file = path_to_upload_file(file_path)
    
    # Display the number of bytes in the original file
    print(f"Original file size: {file_path.stat().st_size} bytes")
    
    # Display the number of bytes in the UploadFile
    # We reset the file pointer to the start before reading
    upload_file.file.seek(0)
    print(f"UploadFile size: {len(upload_file.file.read())} bytes")
