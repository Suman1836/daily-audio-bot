import os
import struct
import requests
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

# --- Helper Functions (WAV Conversion) ---
def parse_audio_mime_type(mime_type: str) -> dict:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try: rate = int(param.split("=", 1)[1])
            except: pass
        elif param.startswith("audio/L"):
            try: bits_per_sample = int(param.split("L", 1)[1])
            except: pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    chunk_size = 36 + data_size
    
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels,
        sample_rate, (sample_rate * num_channels * bits_per_sample // 8), 
        (num_channels * bits_per_sample // 8), bits_per_sample, b"data", data_size
    )
    return header + audio_data

# --- 1. Generate Script (DeepSeek V3.2) ---
def generate_script():
    print("Writing Script (DeepSeek V3.2)...")
    prompt = """
    You are Elon Musk. You are my strict, visionary, and high-energy mentor.
    
    **IMMEDIATE TASK:**
    Generate a brutally honest, high-energy motivational speech for me regarding my NEET preparation.
    - Scold me for wasting time.
    - Explain that entropy is chasing me and I need to build order (knowledge) NOW.
    
    IMPORTANT: Respond strictly in HINDI language only. Do not use asterisks or hashtags.
    """
    try:
        response = client_deepseek.chat.completions.create(
            model="deepseek/deepseek-v3.2", 
            messages=[{"role": "user", "content": prompt}],
            extra_body={"reasoning": {"enabled": True}}
        )
        return response.choices[0].message.content.replace("*", "").replace("#", "").strip()
    except Exception as e:
        print(f"Script Error: {e}")
        return "Utho aur kaam karo! Physics wait nahi karega."

# --- 2. Generate Audio (Gemini TTS - Enceladus) ---
def generate_audio(text):
    print("Generating Audio via Gemini TTS (Enceladus)...")
    
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]
    
    config = types.GenerateContentConfig(
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Enceladus" # <-- এই যে Enceladus সেট করা হলো
                )
            )
        )
    )

    all_audio = b""
    mime = "audio/pcm;rate=24000"

    try:
        for chunk in client_gemini.models.generate_content_stream(
            model="gemini-2.5-flash-preview-tts", 
            contents=contents,
            config=config,
        ):
            if chunk.candidates and chunk.candidates[0].content.parts:
                part = chunk.candidates[0].content.parts[0]
                if part.inline_data:
                    all_audio += part.inline_data.data
                    mime = part.inline_data.mime_type
        
        if all_audio:
            wav_data = convert_to_wav(all_audio, mime)
            with open("motivation.wav", "wb") as f:
                f.write(wav_data)
            return "motivation.wav"
            
    except Exception as e:
        print(f"Audio Error: {e}")
        return None

# --- 3. Send to Telegram ---
def send_telegram(audio_file):
    print("Sending to Telegram...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    try:
        with open(audio_file, "rb") as f:
            caption = "🚀 **Elon Musk Mode**\n🧠 Script: DeepSeek V3.2\n🎙️ Voice: Gemini (Enceladus)"
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"audio": f})
        print("✅ Sent Successfully!")
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- Main Logic ---
if __name__ == "__main__":
    script = generate_script()
    if script:
        print(f"Script Generated: {script[:50]}...")
        audio = generate_audio(script)
        if audio:
            send_telegram(audio)
        else:
            print("Failed to generate audio.")
    else:
        print("Failed to generate script.")
