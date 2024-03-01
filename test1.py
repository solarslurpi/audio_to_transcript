import re

gdrive_id = '1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5'  # Example ID
pattern = re.compile(r'^[a-zA-Z0-9_-]{25,30}$')

if pattern.match(gdrive_id):
    print("The ID is valid.")
else:
    print("Invalid Google Drive ID format.")
