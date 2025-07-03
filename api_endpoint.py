from fastapi import FastAPI
import whisper

app = FastAPI()

# Load Whisper model once on startup
model = whisper.load_model("small")

@app.get("/")
def read_root():
    return {"message": "API is running!"}

@app.post("/transcribe")
def transcribe_audio():
    # Transcribe recorded command.wav file
    result = model.transcribe("command.wav")
    return {"transcription": result["text"]}
