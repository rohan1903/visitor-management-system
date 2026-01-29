import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
from firebase_config import firebase_db as db

# Audio settings
SAMPLERATE = 16000
CHANNELS = 1
FILENAME = "visitor_audio.wav"

def record_audio(duration=10):
    print(f"🎤 Recording for {duration} seconds... Start speaking.")
    audio = sd.rec(int(duration * SAMPLERATE), samplerate=SAMPLERATE, channels=CHANNELS)
    sd.wait()
    sf.write(FILENAME, audio, SAMPLERATE)
    print("🛑 Recording finished and saved.")

def transcribe_audio(file_path=FILENAME):
    print("🧠 Transcribing...")
    model = whisper.load_model("tiny")  # or "small"

    result = model.transcribe(file_path)
    return result["text"]

def store_feedback(visitor_id, feedback_text):
    ref = db.reference('feedbacks')
    ref.push({
        "visitor_id": visitor_id,
        "feedback": feedback_text
    })
    print(f"✅ Feedback stored in Firebase for visitor_id: {visitor_id}")

# Optional standalone test
if __name__ == "__main__":
    visitor_id = input("Enter visitor ID: ")
    record_audio(duration=10)
    feedback = transcribe_audio()
    print("Transcribed Feedback:", feedback)
    store_feedback(visitor_id, feedback)
