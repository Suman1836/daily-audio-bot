import os
import requests
from google import genai
from elevenlabs.client import ElevenLabs

# --- Setup Keys ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip().replace('"', '')
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip().replace('"', '')
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip().replace('"', '')
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip().replace('"', '')

# --- Settings ---
# তোমার দেওয়া Voice ID
VOICE_ID = "SGbOfpm28edC83pZ9iGb"
# Flash v2.5 Model ID (Super Fast & Real)
MODEL_ID = "eleven_flash_v2_5"

# --- Clients Initialize ---
client_gemini = genai.Client(api_key=GEMINI_KEY)
client_eleven = ElevenLabs(api_key=ELEVENLABS_KEY)

# --- 1. Generate Script (The Elon Musk Persona) ---
def generate_script():
    print("Writing Script (Elon Mode)...")
    
    # সেই আগের পাওয়ারফুল প্রম্পট
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
    
    IMPORTANT: Respond strictly in HINDI language only. Do not use asterisks or markdown.
    """

    try:
        response = client_gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        # ক্লিন টেক্সট
        return response.text.replace("*", "").replace("#", "").strip()
    except Exception as e:
        print(f"Script Error: {e}")
        return "Utho aur kaam karo! Physics wait nahi karega."

# --- 2. Generate Audio (ElevenLabs Flash v2.5) ---
def generate_audio(text):
    print("Generating Audio via ElevenLabs Flash v2.5...")
    
    try:
        # অডিও জেনারেট করা হচ্ছে
        audio_generator = client_eleven.text_to_speech.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id=MODEL_ID,
            output_format="mp3_44100_128",
        )
        
        # ফাইল সেভ করা
        filename = "motivation.mp3"
        with open(filename, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
                
        return filename
    except Exception as e:
        print(f"ElevenLabs Error: {e}")
        return None

# --- 3. Send to Telegram ---
def send_telegram(audio_file, text_script):
    print("Sending to Telegram...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    
    try:
        with open(audio_file, "rb") as f:
            # ক্যাপশনে ছোট করে টেক্সট থাকবে
            caption = "🚀 **Elon Musk Mode (Flash v2.5)**"
            
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"audio": f})
        print("✅ Audio Sent Successfully!")
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- Main Logic ---
if __name__ == "__main__":
    script = generate_script()
    if script:
        print(f"Script Generated: {script[:50]}...") # লগ এ দেখার জন্য
        audio = generate_audio(script)
        if audio:
            send_telegram(audio, script)
        else:
            print("Failed to generate audio.")
    else:
        print("Failed to generate script.")
