

from datetime import datetime

# Initialize an empty dictionary to act as the progress store
status_dict = {}


def create_task_id():
    now = datetime.now()
    midnight = datetime.combine(now.date(), datetime.min.time())
    seconds_since_midnight = (now - midnight).seconds

    # Format the seconds to ensure it is a 5-digit number. This will only work correctly up to 99999 seconds (27.7 hours)
    task_id = f"{seconds_since_midnight:05d}"
    return task_id


def update_task_status(task_id, status, filename=None):
    BASE_URL = 'http://localhost:8000/static/'
    if task_id:
        if filename:
            download_url = f"{BASE_URL}{filename}"
            status_dict[task_id] = {"status": status, "url": download_url}
        else:
            status_dict[task_id] = {"status": status}
    else:
        raise ValueError(f"Invalid task ID {task_id}")


def get_task_status(task_id):
    """Retrieve the status of a task."""
    if task_id in status_dict:
        return status_dict[task_id]
    else:
        return None  # or raise an exception, depending on your error handling strategy
