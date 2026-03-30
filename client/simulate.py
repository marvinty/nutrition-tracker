#!/usr/bin/env python3
"""
ESP32 simulator: records from Mac microphone, POSTs to /audio, speaks the response.

Requirements:
    pip install -r client/requirements.txt
    brew install portaudio  # required on macOS before pip install pyaudio

Usage:
    python client/simulate.py
    API_URL=http://192.168.1.10:8000 python client/simulate.py
"""

import os
import sys
import tempfile
import wave

import pyaudio
import pyttsx3
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
RECORD_SECONDS = 5
FORMAT = pyaudio.paInt16


def record_audio(duration: int = RECORD_SECONDS) -> bytes:
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )
    print(f"Recording for {duration} seconds... speak now.")
    frames = []
    for _ in range(int(SAMPLE_RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    audio.terminate()
    print("Recording complete.")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


def post_audio(wav_bytes: bytes) -> dict:
    response = requests.post(
        f"{API_URL}/audio",
        files={"file": ("recording.wav", wav_bytes, "audio/wav")},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def speak(text: str) -> None:
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def main() -> None:
    print("Nutrition Tracker Simulator")
    print(f"Endpoint: {API_URL}/audio")
    print("-" * 40)
    try:
        wav_bytes = record_audio()
        print("Sending to server...")
        result = post_audio(wav_bytes)
        print(f"\nResponse: {result}")
        summary = (
            f"Logged {result.get('description', 'meal')}. "
            f"{int(result.get('calories') or 0)} calories, "
            f"{result.get('protein') or 0} grams protein."
        )
        print(f"Speaking: {summary}")
        speak(summary)
    except requests.HTTPError as exc:
        print(f"HTTP {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
