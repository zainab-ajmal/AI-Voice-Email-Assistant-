import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")  # open api key

#making a function to extract intent
def extract_intent_with_gpt(transcription_text):
    prompt = f"""
You are an AI assistant for an email voice assistant.
Given this voice command:

"{transcription_text}"

Respond only in JSON format like:
{{
  "intent": "<intent_name>",
  "entities": {{
    "recipient": "<name or contact>",
    "message": "<message content>"
  }}
}}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message["content"]
