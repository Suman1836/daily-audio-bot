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
# Flash v2.5 Model ID
MODEL_ID = "eleven_flash_v2_5"

# --- Clients Initialize ---
client_gemini = genai.Client(api_key=GEMINI_KEY)
client_eleven = ElevenLabs(api_key=ELEVENLABS_KEY)

# --- 1. Generate Script (Gemini) ---
def generate_script():
    print("Generating Script...")
    prompt = """
    Act as Elon Musk. Write a short, high-intensity motivational message for a student.
    
    Constraints:
    1. Maximum 2-3 sentences.
    2. Max 50 words (To save audio credits).
    3. Brutally honest and energetic.
    """
    try:
        response = client_gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.replace("*", "").replace("#", "").strip()
    except Exception as e:
        print(f"Script Error: {e}")
        return "Wake up. The competition is not sleeping. Get to work."

# --- 2. Generate Audio (ElevenLabs Flash v2.5) ---
def generate_audio(text):
    print("Generating Audio via ElevenLabs...")
    
    try:
        # অডিও জেনারেট করা হচ্ছে (Stream হিসেবে আসে)
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
            caption = f"🎙️ **Daily Fuel (Flash v2.5)**\n\n{text_script}"
            if len(caption) > 1024: caption = caption[:1021] + "..."
            
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"audio": f})
        print("✅ Audio Sent Successfully!")
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- Main Logic ---
if __name__ == "__main__":
    script = generate_script()
    if script:
        print(f"Script: {script}")
        audio = generate_audio(script)
        if audio:
            send_telegram(audio, script)
        else:
            print("Failed to generate audio.")
    else:
        print("Failed to generate script.")
