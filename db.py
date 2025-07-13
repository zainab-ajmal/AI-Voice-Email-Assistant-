from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Replace with your MongoDB URI
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

# Database and collection
db = client["voice_email_assistant"]
tokens_collection = db["user_tokens"]
