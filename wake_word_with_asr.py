import pvporcupine
import pyaudio
import struct
import wave
import time
import webrtcvad
import whisper
import threading
import requests
import os
from dotenv import load_dotenv

load_dotenv()
access_key = os.getenv("PORCUPINE_ACCESS_KEY")
model = whisper.load_model("small")

porcupine = pvporcupine.create(
    access_key=access_key,
    keyword_paths=['Hey-Inbox_en_windows_v3_0_0.ppn']
)

def record_until_silence(filename="command.wav"):
    CHUNK = 320
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    SILENCE_LIMIT = 3.0

    vad = webrtcvad.Vad()
    vad.set_mode(2)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

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
                break

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def listen_for_wake_word():
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )

    print("Listening for wake word...")

    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            result = porcupine.process(pcm)
            if result >= 0:
                print("Wake word detected!")
                record_until_silence("command.wav")

                print("Transcribing...")
                transcription = model.transcribe("command.wav", language="en", temperature=0)
                print("Transcribed:", transcription["text"])

                # send to FastAPI endpoint
                try:
                    requests.post("http://localhost:8000/process_command", json={"text": transcription["text"]})
                except Exception as e:
                    print("Failed to send to FastAPI:", e)

    except KeyboardInterrupt:
        print("Shutting down listener.")
    finally:
        stream.close()
        pa.terminate()
        porcupine.delete()

def record_user_decision(filename="user_decision.wav", silence_limit=2.0, max_record_time=7.0):
    CHUNK = 320  # Must be 10/20/30 ms for WebRTC VAD
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    vad = webrtcvad.Vad()
    vad.set_mode(2)  # 0 = less aggressive, 3 = most aggressive

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

    print("🎤 Listening for your decision...")

    frames = []
    silence_start = None
    start_time = time.time()

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        is_speech = vad.is_speech(data, RATE)
        current_time = time.time()

        if is_speech:
            silence_start = None
        else:
            if silence_start is None:
                silence_start = current_time
            elif (current_time - silence_start) > silence_limit:
                print("🛑 Silence detected, stopping recording.")
                break

        if (current_time - start_time) > max_record_time:
            print("⏱️ Max recording time reached.")
            break

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    print(f"🎧 Audio saved to {filename}")

