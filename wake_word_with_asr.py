import pvporcupine
import pyaudio
import struct
import numpy as np
import wave
import time
import webrtcvad
import whisper
#from pydub import AudioSegment
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()
access_key = os.getenv("PORCUPINE_ACCESS_KEY")

#Load Whisper model
model = whisper.load_model("small")

# Initialize Porcupine with access key from env
porcupine = pvporcupine.create(
     access_key=access_key,
     keyword_paths=['Hey-Inbox_en_windows_v3_0_0.ppn']  #defining path
)

# Recording function with VAD
def record_until_silence(filename="command.wav"):
    CHUNK = 320
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    SILENCE_LIMIT = 3.0  # seconds

    vad = webrtcvad.Vad()
    vad.set_mode(2)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

    print("Recording command until silence...")

    frames = []
    silence_start = None

    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        is_speech = vad.is_speech(data, RATE)

        if is_speech:
            silence_start = None
        else:
            if silence_start is None:
                silence_start = time.time()
            elif time.time() - silence_start > SILENCE_LIMIT:
                print("Silence detected. Stopping recording.")
                break

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    print(f"Recording saved to {filename}")

# Start audio stream for wake word detection
pa = pyaudio.PyAudio()
audio_stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length
)

print("Listening for wake word...")

try:
    while True:
        pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

        result = porcupine.process(pcm)
        if result >= 0:
            print("Wake word detected!")

            # Record command
            record_until_silence("command.wav")
           # sound = AudioSegment.from_wav("command.wav")
            #sound = sound.set_frame_rate(44100)
            #sound.export("command_resampled.wav", format="wav")
            # Transcribe recorded command using Whisper
            print("Transcribing command...")
            transcription = model.transcribe("command.wav", language="en", temperature=0)

            print("Transcribed text:", transcription["text"])

except KeyboardInterrupt:
    print("Stopping...")

finally:
    audio_stream.close()
    pa.terminate()
    porcupine.delete()