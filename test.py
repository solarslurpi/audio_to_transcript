from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Define the settings class
class Settings(BaseSettings):
    app_name: str = "MyApp"
    max_users: int = 10

# Load environment variables from .env
load_dotenv()

# Access the settings
print(Settings().app_name)  # Output: "MyApp"
print(Settings().max_users)  # Output: 10