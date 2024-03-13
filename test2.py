import streamlit as st
import time
import random

# Function to update UI with progress status
def update_progress(progress_placeholder, progress):
    progress_placeholder.text(f"Progress: {progress}%")

# Function to update UI with SSE messages
def update_sse_message(message_placeholder, new_message):
    message_placeholder.text(f"SSE Message: {new_message}")

# Mock code for downloading video with UI updates
def download_video(url, progress_placeholder, message_placeholder):
    # Simulate downloading process
    for i in range(5):
        progress = (i + 1) * 20
        update_progress(progress_placeholder, progress)
        time.sleep(1)

    # Trigger SSE events after download completion
    send_random_sse_events(message_placeholder)

# Mock code for sending random SSE events
def send_random_sse_events(message_placeholder):
    sse_messages = ["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"]

    for _ in range(5):
        random_message = random.choice(sse_messages)
        update_sse_message(message_placeholder, random_message)
        time.sleep(1)

if __name__ == '__main__':
    st.title('Mock YouTube MP3 Downloader')

    url = st.text_input('Enter YouTube URL:')
    progress_placeholder = st.empty()
    message_placeholder = st.empty()

    if st.button('Download MP3'):
        if url:
            st.text("Downloading MP3...")
            download_video(url, progress_placeholder, message_placeholder)