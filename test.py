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

# Function to edit data in the DataFrame
def edit_data(index, name, age):
    global data
    data.at[index, "Name"] = name
    data.at[index, "Age"] = age
    return data

# Function to delete data from the DataFrame based on index
def delete_data(index):
    global data
    data = data.drop(index)  # Drop rows by index
    return data

# Gradio interface with input fields for Name and Age for adding, editing, and deleting data in the DataFrame
inputs = gr.Interface(
    fn=add_data,
    inputs=[gr.Textbox(lines=1, label="Enter Name:"), gr.Number(label="Enter Age:")],
    outputs=gr.Dataframe(headers=["Name", "Age"]),
    title="Dataframe App",
    description="Add, edit, or delete data in a DataFrame.",
)

with inputs:
    # Add a button column to each row for deleting that specific row
    delete_buttons = [gr.Button("Delete") for _ in range(len(data))]

    def delete_entry(index):
        delete_data(index)

    for i, button in enumerate(delete_buttons):
        button.click(lambda i=i: delete_entry(i))  # Use lambda to capture current value of i

# inputs.additional_controls = delete_buttons

inputs.launch()