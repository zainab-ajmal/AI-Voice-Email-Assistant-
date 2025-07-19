import webrtcvad
import collections
import sys
import wave
import time
import os
import pyaudio
import struct
import whisper

RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAME_DURATION = 30  # ms
FRAME_SIZE = int(RATE * FRAME_DURATION / 1000)
MAX_SILENT_SECONDS = 1.5  # Stop recording after this long silence

def frame_generator(stream, vad):
    ring_buffer = collections.deque(maxlen=int(RATE / FRAME_SIZE * MAX_SILENT_SECONDS))
    triggered = False
    voiced_frames = []
    start_time = time.time()

    print("🎙️ Speak the labels you want to create in Gmail...")

    while True:
        frame = stream.read(FRAME_SIZE, exception_on_overflow=False)
        if len(frame) == 0:
            break
        is_speech = vad.is_speech(frame, RATE)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                break

    print("🛑 Silence detected. Stopping recording...")
    return b''.join(voiced_frames)

def save_wave(path, audio):
    wf = wave.open(path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(audio)
    wf.close()

def transcribe_with_whisper(audio_path="command.wav"):
    print("🔍 Transcribing with Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="en")
    print(f"📝 You said: {result['text']}")
    return result["text"]

def record_command():
    vad = webrtcvad.Vad(2)  # Aggressiveness (0-3)
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=FRAME_SIZE)
    audio_data = frame_generator(stream, vad)
    stream.stop_stream()
    stream.close()
    pa.terminate()

    save_wave("command.wav", audio_data)
    print("✅ Voice command saved as 'command.wav'")

    # Transcribe and show what was said
    transcribe_with_whisper("command.wav")

if __name__ == "__main__":
    record_command()
