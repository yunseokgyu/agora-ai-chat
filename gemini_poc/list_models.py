
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("Error: GEMINI_API_KEY not found.")
else:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        models = response.json().get('models', [])
        print("Available Models:")
        for model in models:
            print(f"- {model['name']}: {model.get('supportedGenerationMethods')}")
    else:
        print(f"Error fetching models: {response.status_code} - {response.text}")
