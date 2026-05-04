
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("LLM_API_KEY")
if not api_key:
    print("API Key not found!")
    exit(1)

client = genai.Client(api_key=api_key)

try:
    print("Available models:")
    for m in client.models.list():
        print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
