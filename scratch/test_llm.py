
import os
from llama_index.llms.google_genai import GoogleGenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("LLM_API_KEY")
model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

if not api_key:
    print("API Key not found!")
    exit(1)

try:
    llm = GoogleGenAI(model=model_name, api_key=api_key)
    response = llm.complete("Olá, você está funcionando?")
    print(f"Response: {response}")
except Exception as e:
    print(f"Error: {e}")
