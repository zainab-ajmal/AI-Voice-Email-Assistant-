# email_followup.py
from tts_handler import speak_text

def speak_email_flow(email_text: str, read_email_aloud: bool = True):
    if read_email_aloud:
        speak_text("Here’s your email:")
        speak_text(email_text)

    speak_text("Should I send it, save it as draft, or review it first?")
