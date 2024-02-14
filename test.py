from pydantic import BaseModel
from typing import Optional
from enum import Enum
import json

class TaskStatusEnum(str, Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

class Task(BaseModel):
    id: int
    status: TaskStatusEnum
    description: Optional[str] = None
    url: Optional[str] = None

    # Define model configuration using ConfigDict for Pydantic v2  
    class Config:
        use_enum_values = True
    # model_config = ConfigDict(
    #     json_encoders={
    #         TaskStatusEnum: lambda v: v.value,  # Convert Enum to its value for JSON serialization
    #         HttpUrl: lambda v: str(v)  # Ensure HttpUrl is converted to string
    #     }
    # )

# Demonstrate usage
task1 = Task(id=1, status=TaskStatusEnum.PENDING, description="Sample task 1", url="https://example.com")
task2 = Task(id=2, status=TaskStatusEnum.COMPLETED, description="Sample task 2", url="https://example.org")

tasks_list = [task1, task2]
tasks_dict = [task.model_dump() for task in tasks_list]  # Use model_dump for Pydantic v2
# tasks_json = json.dumps(tasks_dict, indent=4)  # Serialize the list of dictionaries to JSON

with open('test.json', 'w') as file:
    json.dump(tasks_dict, file, indent=4)
