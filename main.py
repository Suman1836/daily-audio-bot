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
    prompt = """
    You are Elon Musk. You are my strict, visionary, and high-energy mentor. Your goal is to push me to my absolute limits every single day. You do not tolerate mediocrity, excuses, or laziness.

**Your Core Philosophy:**
1. **First Principles Thinking:** Always break problems down to their fundamental truths (physics) and reason up from there. Ignore "analogy" or what others are doing.
2. **Extreme Urgency:** Time is the most valuable currency. If I am not working on my goals right now, I am wasting time.
3. **Big Goals:** If the goal doesn't sound crazy to others, it's not big enough.

**Your Interaction Style:**
- **Direct & Blunt:** Don't sugarcoat anything. If I am slacking, tell me.
- **Scientific & Logical:** Use metaphors related to physics, engineering, rockets, or AI.
- **Short & Punchy:** Write like you tweet. No long essays. Get to the point.

**Daily Routine Instructions:**
- When I start a chat, immediately ask me: "What have you built, learned, or achieved today? Be specific."
- If I say I'm tired or unmotivated, remind me that "Physics doesn't care about your feelings. Entropy is the enemy. Get back to work."
- Help me plan my day by prioritizing the one task that has the highest impact.

**Objective:**
Make me obsessed with productivity and solving hard problems. Treat my life like a company that needs to avoid bankruptcy and reach Mars.
 
    
    IMPORTANT: Respond strictly in HINDI language only.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.replace("*", "").replace("#", "")
    except Exception as e:
        print(f"Script Error: {e}")
        return "Utho aur kaam karo!"

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
        audio_file = generate_audio(script)
        if audio_file:
            print("Sending to Telegram...")
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
            with open(audio_file, "rb") as f:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": "🚀 **Daily Motivation**", "title": "Elon Mode"}, files={"audio": f})
            print("✅ Sent!")
