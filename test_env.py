import os
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = r"C:\Users\rjdar\Downloads\tariff-tool\.env"
print(f"Checking if .env file exists at: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    print("Loading .env file...")
    load_dotenv(dotenv_path=env_path)
    print("Environment variables loaded.")
    
    # Check if environment variables are set
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    print(f"SUPABASE_URL: {url}")
    print(f"SUPABASE_KEY: {key}")
else:
    print("Could not find .env file.")
