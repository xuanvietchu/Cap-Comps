from dotenv import load_dotenv
import os

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env")

DATA_PATH = "data/test/test.csv"
MODEL_NAME = "gemini-3.1-flash-lite"