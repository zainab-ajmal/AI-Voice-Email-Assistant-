import pvporcupine
import pyaudio
import struct
import numpy as np
import wave
import webrtcvad
import collections
import time


def record_until_silence(filename="command.wav"):
    CHUNK = 320  # 20ms at 16kHz mono
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    SILENCE_LIMIT = 3.0  # seconds of silence before ending

    vad = webrtcvad.Vad()
    vad.set_mode(2)  # 0=aggressive silence detection, 3=very sensitive

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

    print("Recording command until silence...")

    frames = []
    ring_buffer = collections.deque(maxlen=int(SILENCE_LIMIT * RATE / CHUNK))
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


# Initialize Porcupine
porcupine = pvporcupine.create(
    access_key='oIdo/FHEb2dBhULDYSPLaj87kpM09DUuDtRhnvYPUwe94C5T0R9RtQ==', # my access_key from site
    keyword_paths=['Hey-Inbox_en_windows_v3_0_0.ppn']  # e.g., 'porcupine.ppn' for default test
)

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
            record_until_silence("command.wav")

            # Here you will call your recording function after wake word detection

except KeyboardInterrupt:
    print("Stopping...")

finally:
    audio_stream.close()
    pa.terminate()
    porcupine.delete()
