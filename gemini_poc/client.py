
import asyncio
import os
import websockets
import json
import base64
import pyaudio
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash-native-audio-latest" 
URI = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={API_KEY}"

# Audio params
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 512

p = pyaudio.PyAudio()

# Print default device info
try:
    default_input = p.get_default_input_device_info()
    print(f"Using Input Device: {default_input['name']}")
    default_output = p.get_default_output_device_info()
    print(f"Using Output Device: {default_output['name']}")
except Exception as e:
    print(f"Error getting default devices: {e}")

# Load Output Device Index from .env
output_device_index = os.getenv("GEMINI_OUTPUT_DEVICE_INDEX")
if output_device_index:
    output_device_index = int(output_device_index)
    print(f"Using Configured Output Device Index: {output_device_index}")
else:
    output_device_index = None # Use default

input_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
output_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, output_device_index=output_device_index)

async def gemini_voice_chat():
    async with websockets.connect(URI) as ws:
        print("Connected to Gemini Live API!")
        
        # Initial config
        await ws.send(json.dumps({
            "setup": {
                "model": f"models/{MODEL}",
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {"prebuilt_voice_config": {"voice_name": "Kore"}}
                    }
                }
            }
        }))

        # Send initial text to trigger response
        print("Scnding initial 'Hello' to trigger response...")
        await ws.send(json.dumps({
            "client_content": {
                "turns": [{
                    "role": "user",
                    "parts": [{"text": "Hello? Can you hear me?"}]
                }],
                "turn_complete": True
            }
        }))

        # Receive loop
        async def receive():
            try:
                print("Listening for response...")
                async for msg in ws:
                    data = json.loads(msg)
                    server_content = data.get("serverContent")
                    if server_content:
                        model_turn = server_content.get("modelTurn")
                        if model_turn:
                            parts = model_turn.get("parts")
                            for part in parts:
                                if "inlineData" in part:
                                    audio_data = base64.b64decode(part["inlineData"]["data"])
                                    output_stream.write(audio_data)
                                    print(f"R({len(audio_data)})", end=" ", flush=True)
                    
                    # Log other messages
                    if "serverContent" not in data:
                       # print(f"\nMsg: {data.keys()}")
                       pass

            except Exception as e:
                print(f"Receive error: {e}")

        # Send loop
        async def send():
             while True:
                data = input_stream.read(CHUNK, exception_on_overflow=False)
                await ws.send(json.dumps({
                    "realtime_input": {
                        "media_chunks": [{
                            "mime_type": "audio/pcm",
                            "data": base64.b64encode(data).decode()
                        }]
                    }
                }))
                await asyncio.sleep(0.01)

        await asyncio.gather(receive(), send())

if __name__ == "__main__":
    try:
        if not API_KEY:
            print("Error: GEMINI_API_KEY not found in .env")
        else:
            asyncio.run(gemini_voice_chat())
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        input_stream.stop_stream()
        input_stream.close()
        output_stream.stop_stream()
        output_stream.close()
        p.terminate()
