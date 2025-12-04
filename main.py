import os
import struct
import requests
import mimetypes
import tempfile
from openai import OpenAI
from google import genai
from google.genai import types

# --- Setup Keys ---
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip().replace('"', '')
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip().replace('"', '')
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip().replace('"', '')
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip().replace('"', '')

# Validate environment variables
if not all([OPENROUTER_KEY, GEMINI_KEY, BOT_TOKEN, CHAT_ID]):
    raise ValueError("Missing one or more required environment variables")

# --- Clients ---
# 1. DeepSeek (Script Writing)
client_deepseek = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
    default_headers={
        "HTTP-Referer": "https://github.com",
        "X-Title": "Daily Audio Bot",
    }
)

# 2. Gemini (Voice Generation)
client_gemini = genai.Client(api_key=GEMINI_KEY)

# --- Helper Functions (WAV Conversion) ---
def parse_audio_mime_type(mime_type: str) -> dict:
    """Parse audio parameters from MIME type string."""
    bits_per_sample = 16
    rate = 24000
    
    if mime_type:
        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try: 
                    rate = int(param.split("=", 1)[1])
                except: 
                    pass
            elif param.startswith("audio/L"):
                try:
                    bits_per_sample = int(param.split("L", 1)[1])
                except:
                    pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Convert raw audio data to WAV format."""
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
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16,
        1, num_channels, sample_rate,
        byte_rate, block_align, bits_per_sample,
        b"data", data_size
    )
    return header + audio_data

def save_binary_file(file_name, data):
    """Save binary data to a file."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")

# --- 1. Generate Script (DeepSeek V3.2) ---
def generate_script():
    print("Writing Script (DeepSeek V3.2)...")
    prompt = """
    You are Elon Musk. You are my strict, visionary, and high-energy mentor.
    
    **IMMEDIATE TASK:**
    Generate a brutally honest, high-energy motivational speech for me regarding my NEET preparation.
    - Scold me for wasting time.
    - Explain that entropy is chasing me and I need to build order (knowledge) NOW.
    
    IMPORTANT: Respond strictly in BENGALI language only. Do not use asterisks or hashtags.
    """
    try:
        response = client_deepseek.chat.completions.create(
            model="deepseek/deepseek-v3.2", 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.9
        )
        script = response.choices[0].message.content
        # Clean up the script
        script = script.replace("*", "").replace("#", "").strip()
        print(f"Script generated successfully: {len(script)} characters")
        return script
    except Exception as e:
        print(f"Script Error: {e}")
        return "Utho aur kaam karo! Physics wait nahi karega. Time waste mat karo, padhai shuru karo!"

# --- 2. Generate Audio (Gemini TTS - gemini-2.5-flash-preview-tts) ---
def generate_audio(text, output_file="motivation.wav"):
    print("Generating Audio via Gemini TTS (Enceladus voice)...")
    
    if len(text) < 10:
        print("Text too short for audio generation")
        return None
    
    try:
        model = "gemini-2.5-flash-preview-tts"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=text),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Enceladus"  # Using Enceladus voice as requested
                    )
                )
            ),
        )

        all_audio_data = b""
        mime_type = None
        file_index = 0
        
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
                
            if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                data_buffer = inline_data.data
                
                if mime_type is None:
                    mime_type = inline_data.mime_type
                
                all_audio_data += data_buffer
        
        if all_audio_data:
            # Convert to WAV format
            file_extension = mimetypes.guess_extension(mime_type) if mime_type else None
            if file_extension is None or file_extension != ".wav":
                # Convert to WAV if not already
                wav_data = convert_to_wav(all_audio_data, mime_type or "audio/pcm;rate=24000")
                save_binary_file(output_file, wav_data)
            else:
                save_binary_file(output_file, all_audio_data)
            
            print(f"Audio file generated: {output_file}")
            return output_file
        else:
            print("No audio data received from Gemini TTS")
            return None
            
    except Exception as e:
        print(f"Audio Generation Error: {e}")
        return None

# --- 3. Send to Telegram ---
def send_telegram(audio_file):
    print("Sending to Telegram...")
    
    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    
    try:
        with open(audio_file, "rb") as f:
            files = {"audio": f}
            data = {
                "chat_id": CHAT_ID,
                "caption": "🚀 **Elon Musk Mode**\n🧠 Script: DeepSeek V3.2\n🎙️ Voice: Gemini TTS (Enceladus)",
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                print("✅ Audio sent successfully to Telegram!")
                return True
            else:
                print(f"❌ Telegram API error: {result}")
                return False
                
    except requests.exceptions.RequestException as e:
        print(f"Telegram Request Error: {e}")
        return False
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

# --- Main Logic ---
def main():
    print("=== Daily Audio Bot Started ===")
    
    # Step 1: Generate script
    print("\n1. Generating script...")
    script = generate_script()
    if not script:
        print("Failed to generate script")
        return
    
    print(f"Script preview: {script[:100]}...")
    
    # Step 2: Generate audio
    print("\n2. Generating audio...")
    audio_file = "motivation.wav"
    audio_path = generate_audio(script, audio_file)
    
    if not audio_path:
        print("Failed to generate audio file")
        # Send text message as fallback
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": CHAT_ID,
                "text": f"📝 **Today's Motivation (Text Only):**\n\n{script[:1000]}",
                "parse_mode": "Markdown"
            }
            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                print("✅ Text sent as fallback")
        except Exception as e:
            print(f"Fallback text send failed: {e}")
        return
    
    # Step 3: Send to Telegram
    print("\n3. Sending to Telegram...")
    success = send_telegram(audio_path)
    
    # Cleanup
    try:
        if os.path.exists(audio_path):
            os.unlink(audio_path)
            print("Temporary file cleaned up")
    except Exception as e:
        print(f"Cleanup error: {e}")
    
    if success:
        print("\n=== Process completed successfully ===")
    else:
        print("\n=== Process completed with errors ===")

if __name__ == "__main__":
    main()