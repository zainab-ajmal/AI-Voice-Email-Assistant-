from fastapi import FastAPI
from fastapi.responses import JSONResponse
from llm_handler import process_with_llm
import whisper
import os
from dotenv import load_dotenv
import traceback

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
