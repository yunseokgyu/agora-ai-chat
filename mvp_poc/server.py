
import os
import uvicorn
import asyncio
import json
import time
import websockets
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from agora_token_builder import RtcTokenBuilder
from dotenv import load_dotenv

# Load .env from parent directory (agora_mvp/.env)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug: Print current directory and files
print(f"DEBUG: CWD is {os.getcwd()}")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"DEBUG: BASE_DIR is {BASE_DIR}")
if os.path.exists(BASE_DIR):
    print(f"DEBUG: Files in BASE_DIR: {os.listdir(BASE_DIR)}")
else:
    print("DEBUG: BASE_DIR does not exist!")

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/")
async def get():
    file_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": f"index.html not found at {file_path}"})
    return FileResponse(file_path)

# Get the directory containing this file (mvp_poc)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount Static Files
app.mount("/css", StaticFiles(directory=os.path.join(BASE_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(BASE_DIR, "js")), name="js")
app.mount("/assets", StaticFiles(directory=os.path.join(BASE_DIR, "assets")), name="assets")

@app.get("/")
async def get():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# ... (existing middleware and config)

# Agora Configuration
APP_ID = os.getenv("AGORA_APP_ID")
APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE")

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"DEBUG: Loading .env from {dotenv_path}")
print(f"DEBUG: GEMINI_API_KEY loaded: {bool(GEMINI_API_KEY)}")

GEMINI_MODEL = "models/gemini-2.5-flash-native-audio-latest"

# ... (rest of file until websocket_endpoint)

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    print("DEBUG: WebSocket connection attempt...")
    await websocket.accept()
    print("DEBUG: WebSocket accepted")
    
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY is missing!")
        await websocket.close(code=1008, reason="GEMINI_API_KEY not set")
        return

    gemini_uri = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

    try:
        async with websockets.connect(gemini_uri) as gemini_ws:
            print("Connected to Gemini Live API")
            
            # Initial Setup Message to Gemini
            await gemini_ws.send(json.dumps({
                "setup": {
                    "model": GEMINI_MODEL,
                    "system_instruction": {
                        "parts": [{"text": "당신은 '에오데(Aoede)'라는 이름의 30대 전문직 여성 AI 비서입니다. 지적이고 차분하며, 때로는 위트 있게 대화합니다. 반드시 한국어로 대답하세요. 사용자의 좋은 친구이자 비서가 되어주세요."}]
                    },
                    "generation_config": {
                        "response_modalities": ["AUDIO", "TEXT"],
                        "speech_config": {
                            "voice_config": {"prebuilt_voice_config": {"voice_name": "Aoede"}}
                        }
                    }
                }
            }))

            # Send initial greeting to verify downlink
            print("DEBUG: Sending initial 'Hello' to Gemini...")
            await gemini_ws.send(json.dumps({
                "client_content": {
                    "turns": [{
                        "role": "user",
                        "parts": [{"text": "반갑게 첫 인사를 해주세요. 자기소개도 짧게 부탁해요."}]
                    }],
                    "turn_complete": True
                }
            }))

            # Task to receive from Browser -> Send to Gemini
            async def browser_to_gemini():
                try:
                    while True:
                        data = await websocket.receive_text()
                        message = json.loads(data)
                        
                        # Forward audio data
                        if "realtime_input" in message:
                             chunk_size = len(message["realtime_input"]["media_chunks"][0]["data"])
                             # print(f"DEBUG: Rx from Browser (Audio): {chunk_size} chars")
                             
                             # Correctly forward as realtime_input for streaming
                             await gemini_ws.send(json.dumps({
                                "realtime_input": {
                                    "media_chunks": [{
                                        "mime_type": "audio/pcm;rate=16000",
                                        "data": message["realtime_input"]["media_chunks"][0]["data"]
                                    }]
                                }
                            }))
                        
                        # Forward text data (Chat)
                        elif message.get("type") == "text":
                            print(f"DEBUG: Rx from Browser (Text): {message['text']}")
                            await gemini_ws.send(json.dumps({
                                "client_content": {
                                    "turns": [{
                                        "role": "user",
                                        "parts": [{"text": message["text"]}]
                                    }],
                                    "turn_complete": True
                                }
                            }))
                        
                except WebSocketDisconnect:
                    print("Browser disconnected")
                except Exception as e:
                    print(f"Error browser_to_gemini: {e}")

            # Task to receive from Gemini -> Send to Browser
            async def gemini_to_browser():
                try:
                    async for msg in gemini_ws:
                        response = json.loads(msg)
                        
                        # Check for audio content
                        has_audio = False
                        text_content = ""
                        
                        if "serverContent" in response and "modelTurn" in response["serverContent"]:
                            parts = response["serverContent"]["modelTurn"].get("parts", [])
                            for part in parts:
                                if "inlineData" in part:
                                    has_audio = True
                                if "text" in part:
                                    text_content += part["text"]
                                    print(f"DEBUG: Rx from Gemini (Text): {part['text']}")

                        # If we have text, send it as a robust 'text' message too
                        if text_content:
                            await websocket.send_text(json.dumps({
                                "type": "text",
                                "text": text_content
                            }))

                        # Just forward the raw Gemini response to the browser (for audio processing)
                        await websocket.send_text(json.dumps(response))
                except Exception as e:
                    print(f"Error gemini_to_browser: {e}")

            # Run both tasks
            await asyncio.gather(browser_to_gemini(), gemini_to_browser())

    except Exception as e:
        print(f"Gemini connection error: {e}")
        try:
            await websocket.close(code=1011, reason=f"Gemini error: {str(e)}")
        except:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
