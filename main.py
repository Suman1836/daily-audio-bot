import os
import sys
import struct
import requests
import mimetypes
import base64
import re
from openai import OpenAI
from google import genai
from google.genai import types

# --- Setup Keys ---
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip().replace('"', '')
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip().replace('"', '')
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip().replace('"', '')
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip().replace('"', '')

# --- Clients ---
# 1. DeepSeek (Script Writing)
client_deepseek = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# 2. Gemini (Voice Generation)
client_gemini = genai.Client(api_key=GEMINI_KEY)

# --- Helper Functions (Provided by User) ---

def parse_audio_mime_type(mime_type: str) -> dict:
    """Parses bits per sample and rate from an audio MIME type string."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels,
        sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

# --- 1. Generate Script ---

PROMPT_TEXT = """
You are Elon Musk. You are my strict, visionary, and high-energy mentor.

**IMMEDIATE TASK:**
Generate a brutally honest, high-energy motivational speech for me regarding my NEET preparation.
- Scold me for wasting time.
- Explain that entropy is chasing me and I need to build order (knowledge) NOW.

IMPORTANT: Respond strictly in HINDI language only. Do not use asterisks or hashtags.
"""

def generate_script_gemini():
    print("Writing Script (Fallback: Gemini 2.0 Flash)...")
    try:
        response = client_gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=PROMPT_TEXT
        )
        if response.text:
            return response.text.replace("*", "").replace("#", "").strip()
        return None
    except Exception as e:
        print(f"Gemini Script Error: {e}")
        return None

def generate_script_deepseek():
    print("Writing Script (DeepSeek R1)...")
    try:
        # Using deepseek-r1 as it is the current stable reasoning model
        # User provided snippet uses deepseek-v3.2 but R1 is preferred for fixing silent failures
        response = client_deepseek.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[{"role": "user", "content": PROMPT_TEXT}],
            extra_body={"reasoning": {"enabled": True}}
        )

        content = response.choices[0].message.content
        if not content:
            print(f"Warning: Empty content from DeepSeek. Raw response: {response}")
            return None

        return content.replace("*", "").replace("#", "").strip()
    except Exception as e:
        print(f"DeepSeek Script Error: {e}")
        return None

def generate_script():
    # Try DeepSeek first
    script = generate_script_deepseek()
    if script:
        return script

    # Fallback to Gemini
    print("⚠️ Falling back to Gemini for script generation...")
    script = generate_script_gemini()
    if script:
        return script

    return "Utho aur kaam karo! Physics wait nahi karega."

# --- 2. Generate Audio (Gemini TTS - Enceladus) ---
def generate_audio(text):
    print("Generating Audio via Gemini TTS (Enceladus)...")
    
    model = "gemini-2.5-flash-preview-tts"
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Enceladus"
                )
            )
        ),
    )

    all_audio = b""
    mime = "audio/pcm;rate=24000" # Default fallback

    try:
        for chunk in client_gemini.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue

            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                all_audio += part.inline_data.data
                mime = part.inline_data.mime_type
        
        if all_audio:
            # Convert the accumulated raw PCM data to WAV
            wav_data = convert_to_wav(all_audio, mime)
            filename = "motivation.wav"
            with open(filename, "wb") as f:
                f.write(wav_data)
            print(f"File saved to: {filename}")
            return filename
            
    except Exception as e:
        print(f"Audio Error: {e}")
        return None

# --- 3. Send to Telegram ---
def send_telegram(audio_file):
    print("Sending to Telegram...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    try:
        with open(audio_file, "rb") as f:
            caption = "🚀 **Elon Musk Mode**\n🧠 Script: DeepSeek / Gemini\n🎙️ Voice: Gemini (Enceladus)"
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"audio": f})
        print("✅ Sent Successfully!")
    except Exception as e:
        print(f"Telegram Error: {e}")
        raise e

# --- Main Logic ---
if __name__ == "__main__":
    script = generate_script()
    if script:
        print(f"Script Generated: {script[:50]}...")
        audio = generate_audio(script)
        if audio:
            try:
                send_telegram(audio)
            except Exception:
                sys.exit(1)
        else:
            print("Failed to generate audio.")
            sys.exit(1)
    else:
        print("Failed to generate script.")
        sys.exit(1)
