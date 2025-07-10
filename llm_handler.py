import os
from dotenv import load_dotenv
from groq import Groq  # ✅ Groq LLM client

# Load environment variables
load_dotenv()

# Fetch the API key
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found. Make sure your .env file is present and correct.")

# Initialize Groq client
client = Groq(api_key=api_key)

def process_with_llm(transcribed_text: str) -> str:
    prompt = f"""You are a smart voice email assistant. The user said: "{transcribed_text}". 
Analyze it and determine whether it's a command to send an email, read email, or perform another email-related task. 
Respond in valid JSON with fields like action, recipient (if any), subject, and body. You are an AI that extracts email commands. Output ONLY JSON with keys: action, recipient, subject, body. No explanations."""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",  
            messages=[
                {"role": "system", "content": "You are an AI assistant for voice-controlled email."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM error: {str(e)}"
