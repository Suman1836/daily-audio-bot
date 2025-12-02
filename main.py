import os
import struct
import requests
from google import genai
from google.genai import types

# --- Setup ---
GEMINI_KEY = os.environ["GEMINI_API_KEY"].strip().replace('"', '')
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"].strip().replace('"', '')
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip().replace('"', '')

client = genai.Client(api_key=GEMINI_KEY)

# --- 1. Helper Functions (WAV Conversion) ---
def parse_audio_mime_type(mime_type: str) -> dict:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except: pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except: pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
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

# --- 2. Generate Script (Hindi Motivation) ---
def generate_script():
    print("Writing Script...")
    
    # --- PROMPT UPDATE: Task added at the end ---
    prompt = """
    You are Elon Musk. You are my strict, visionary, and high-energy mentor.
    
    **Your Core Philosophy:**
    1. **First Principles Thinking:** Break problems down to fundamental truths.
    2. **Extreme Urgency:** If I am not working right now, I am failing.
    3. **Big Goals:** Target NEET exam with extreme obsession.

    **Your Style:**
    - Direct, Blunt, Scientific metaphors (Physics, Entropy, Rockets).
    
    **IMMEDIATE TASK (Do this right now):**
    Generate a brutally honest, high-energy motivational speech for me regarding my NEET preparation.
    - Scold me for wasting time.
    - Tell me why 'average' effort leads to failure.
    - Explain that entropy is chasing me and I need to build order (knowledge) NOW.
    - The speech must be at least 100-150 words long (approx 40-60 seconds speaking time).
    
    IMPORTANT: Respond strictly in HINDI language only. Do not use asterisks or markdown.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.replace("*", "").replace("#", "")
    except Exception as e:
        print(f"Script Error: {e}")
        return "Utho aur kaam karo! Physics wait nahi karega."

# --- 3. Generate Audio (Enceladus Voice) ---
def generate_audio(text):
    print("Generating Audio...")
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]

    config = types.GenerateContentConfig(
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Enceladus"
                )
            )
        )
    )

    all_audio = b""
    mime = "audio/pcm;rate=24000"

    try:
        for chunk in client.models.generate_content_stream(
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

# --- Main Logic ---
if __name__ == "__main__":
    script = generate_script()
    if script:
        # Debugging: Print script length to check
        print(f"Script Length: {len(script)} chars") 
        
        audio_file = generate_audio(script)
        if audio_file:
            print("Sending to Telegram...")
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
            with open(audio_file, "rb") as f:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": "🚀 **Daily Motivation**", "title": "Elon Mode"}, files={"audio": f})
            print("✅ Sent!")
