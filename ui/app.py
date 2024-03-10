from fastapi import FastAPI
import random
import time
import uvicorn

app = FastAPI()

@app.get('/test')
def test():
    import gradio as gra
    async def balabala():
    def user_greeting(name):
        return "Hi! " + name + " Welcome to your first Gradio application!😎"

    #define gradio interface and other parameters
    app =  gra.Interface(fn = user_greeting, inputs="text", outputs="text")

    global app
    demo.queue()
    demo.startup_events()
    app = gr.mount_gradio_app(app, demo, f'/gradio')

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)