from huggingface_hub import HfApi, HfFileSystem
import re
from tqdm import tqdm
import concurrent.futures
import gradio as gr
import datetime
import pandas as pd
import os
import threading
import time

HF_TOKEN = os.getenv('HF_TOKEN')

api = HfApi()
fs = HfFileSystem()

def restart_space():
  time.sleep(36000)
  api.restart_space(repo_id="Weyaxi/thebloke-quantized-models", token=HF_TOKEN)

text = f"""
🎯 The Leaderboard aims to track TheBloke's quantized models.



"""

quant_models = [i.__dict__['id'] for i in api.list_models(author="TheBloke") if "GPTQ" in i.__dict__['id'] or "GGUF" in i.__dict__['id'] or "AWQ" in i.__dict__['id'] or "GGML" in i.__dict__['id']]


pattern = r'\(https://huggingface\.co/([^/]+)/([^/]+)\)'
liste = {}

def process_model(i, pattern, liste):
    text = fs.read_text(i + "/README.md")
    matches = re.search(pattern, text)

    if matches:
        author = matches.group(1)
        model_name = matches.group(2)
        full_id = (author + "/" + model_name).split(")")[0]

        try:
            liste[full_id].append(i)
        except KeyError:
            liste[full_id] = [i]


num_threads = 64

with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
    futures = []
    for i in quant_models:
        future = executor.submit(process_model, i, pattern, liste)
        futures.append(future)

    concurrent.futures.wait(futures)


authors, models, gptq, gguf, awq, ggml = [], [], [], [], [], []


for model, values in liste.items():
    models.append(model)

    gptq_value, gguf_value, awq_value, ggml_value = None, None, None, None

    for value in values:
        if "-GPTQ" in value:
            gptq_value = value
        elif "-GGUF" in value:
            gguf_value = value
        elif "-AWQ" in value:
            awq_value = value
        elif "-GGML" in value:
            ggml_value = value

    authors.append(model.split('/')[0])
    gptq.append(gptq_value)
    gguf.append(gguf_value)
    awq.append(awq_value)
    ggml.append(ggml_value)


df = pd.DataFrame({'👤 Author Name': authors, '🤖 Model Name': models, '👍 GPTQ': gptq, '📥 GGUF': gguf, '🤷‍♂️ AWQ': awq, '😭 GGML': ggml})


def search(search_text):
  if not search_text:
    return df

  if len(search_text.split('/'))>1:
    return df[df['🤖 Model Name'] == clickable(search_text)]
  else:
    return df[df['👤 Author Name'] == clickable(search_text)]


def clickable(x):
  return None if not x else f'<a target="_blank" href="https://huggingface.co/{x}" style="color: var(--link-text-color); text-decoration: underline;text-decoration-style: dotted;">{x}</a>'


def to_clickable(df):
    for column in list(df.columns):
          df[column] = df[column].apply(lambda x: clickable(x))
    return df


with gr.Blocks() as demo:
    gr.Markdown("""<center><img src = "https://cdn-uploads.huggingface.co/production/uploads/6426d3f3a7723d62b53c259b/tvPikpAzKTKGN5wrpadOJ.jpeg" width=200 height=200></center>""")
    gr.Markdown("""<h1 align="center" id="space-title">The Bloke Quantized Models</h1>""")
    gr.Markdown(text)

    with gr.Column(min_width=320):
        search_bar = gr.Textbox(placeholder="🔍 Search for a author or a specific model", show_label=False)


    df_clickable = to_clickable(df)
    gr_df = gr.Dataframe(df_clickable, interactive=False, datatype=["markdown"]*len(df.columns))

    search_bar.submit(fn=search, inputs=search_bar, outputs=gr_df)

threading.Thread(target=restart_space).start()
demo.launch()