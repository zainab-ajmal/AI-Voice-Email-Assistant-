from fastapi import FastAPI
from fastapi.responses import JSONResponse
from llm_handler import process_with_llm
from emailer import send_email
import whisper
import os
from dotenv import load_dotenv
import traceback
import json

# Load environment
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Load Whisper model once
model = whisper.load_model("small")

@app.get("/")
def read_root():
    return {"message": "Voice Email Assistant API is running!"}

@app.post("/transcribe")
def transcribe_audio():
    try:
        # Step 1: Transcribe audio
        result = model.transcribe("command.wav")
        transcription = result["text"]
        print("🎤 Transcription:", transcription)

        # Step 2: Get LLM response
        llm_response = process_with_llm(transcription)
        print("🤖 LLM Response:", llm_response)

        return {
            "transcription": transcription,
            "llm_response": llm_response
        }

    except Exception as e:
        print("🔥 Error:", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/send_email")
def send_email_route():
    try:
        # Step 1: Transcribe audio
        result = model.transcribe("command.wav")
        transcription = result["text"]
        print("🎤 Transcription:", transcription)

        # Step 2: Process with LLM to get structured email data
        llm_response = process_with_llm(transcription)
        print("🤖 LLM Response:", llm_response)

        # Step 3: Parse LLM response (assuming it's JSON string)
        email_data = json.loads(llm_response)

        recipient = email_data.get("recipient")
        subject = email_data.get("subject", "No Subject")
        body = email_data.get("body", "")

        # Step 4: Send email
        email_send_result = send_email(recipient, subject, body)
        print("📧 Email Send Result:", email_send_result)

        return {
            "transcription": transcription,
            "llm_response": email_data,
            "email_send_result": email_send_result
        }

    except Exception as e:
        print("🔥 Error:", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )