from fastapi import FastAPI
import gradio as gr

app = FastAPI()

# Define your Gradio interface function
def process_string(string: str):
    return string.upper()  # Example: converts string to uppercase

# Initialize your Gradio interface
gradio_interface = gr.Interface(fn=process_string,
                                inputs=gr.Textbox(label="Enter your string"),
                                outputs="text")

# FastAPI endpoint that launches the Gradio interface
@app.get("/gradio")
def gradio_route():
    return gradio_interface.launch()

# Define a FastAPI endpoint to process the string (optional)
@app.post("/process_string/")
async def process_string_endpoint(string: str):
    return {"processed_string": process_string(string)}
