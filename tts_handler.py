import pyttsx3

def speak_text(text: str):
    """Speaks the given text using offline TTS engine."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
