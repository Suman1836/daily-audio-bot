import os
import requests
from openai import OpenAI
from elevenlabs.client import ElevenLabs

# --- Setup Keys ---
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip().replace('"', '')
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip().replace('"', '')
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip().replace('"', '')
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip().replace('"', '')

# --- Settings ---
VOICE_ID = "SGbOfpm28edC83pZ9iGb"
MODEL_ID = "eleven_flash_v2_5"

# --- Clients Initialize ---
client_ai = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

client_eleven = ElevenLabs(api_key=ELEVENLABS_KEY)

# --- 1. Generate Script (DeepSeek V3.2 with Reasoning) ---
def generate_script():
    print("Writing Script (DeepSeek V3.2)...")
    
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
    - Keep it strictly under 100 words (approx 40-50 seconds audio).
    
    IMPORTANT: Respond strictly in HINDI language only. Do not use asterisks (*), hashtags (#) or emojis.
    """

    try:
        # তোমার দেওয়া কোড ফরম্যাট অনুযায়ী
        response = client_ai.chat.completions.create(
            model="deepseek/deepseek-v3.2", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            # Reasoning অন করা হলো
            extra_body={"reasoning": {"enabled": True}}
        )
        
        script_text = response.choices[0].message.content
        
        # ক্লিনিং
        return script_text.replace("*", "").replace("#", "").replace('"', '').strip()
        
    except Exception as e:
        print(f"AI Script Error: {e}")
        return "Utho aur kaam karo! Physics wait nahi karega."

# --- 2. Generate Audio (ElevenLabs) ---
def generate_audio(text):
    print("Generating Audio via ElevenLabs...")
    
    try:
        audio_generator = client_eleven.text_to_speech.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id=MODEL_ID,
            output_format="mp3_44100_128",
        )
        
        filename = "motivation.mp3"
        with open(filename, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
                
        return filename
    except Exception as e:
        print(f"ElevenLabs Error: {e}")
        return None

# --- 3. Send to Telegram ---
def send_telegram(audio_file):
    print("Sending to Telegram...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    
    try:
        with open(audio_file, "rb") as f:
            caption = "🚀 **Elon Musk Mode**\n🧠 Script: DeepSeek V3.2 (Reasoning)\n🎙️ Voice: ElevenLabs"
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"audio": f})
        print("✅ Audio Sent Successfully!")
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
