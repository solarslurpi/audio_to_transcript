import gradio as gr
import pandas as pd

# Initialize an empty DataFrame
data = pd.DataFrame(columns=["Name", "Age"])

# Function to add data to the DataFrame
def add_data(name, age):
    global data
    new_row_df = pd.DataFrame([{"Name": name, "Age": age}], columns=data.columns)
    data = pd.concat([data, new_row_df], ignore_index=True)
    return data

# Gradio interface with input fields for Name and Age
inputs = gr.Interface(
    fn=add_data,
    inputs=[gr.Textbox(lines=1, label="Enter Name:"),
            gr.Number(label="Enter Age:")],
    outputs=gr.Dataframe(headers=["Name", "Age"]),
    title="Dataframe App",
    description="Add data to a DataFrame.",
)

inputs.launch()