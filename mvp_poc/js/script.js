// Agora Globals
let client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
let localAudioTrack;

// Gemini Globals
let audioContext;   // For Microphone input
let playbackCtx;    // For Speaker output
let nextStartTime = 0;
let websocket;

// --- UI Logic ---
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const callBtn = document.getElementById('call-btn');
const rippleRing = document.getElementById('ripple-ring');
const avatarHalo = document.getElementById('avatar-halo');

function updateUiStatus(msg, type = 'neutral') {
    statusText.innerText = msg;
    statusDot.className = 'status-dot'; // Reset
    if (type === 'connected') statusDot.classList.add('connected');
    if (type === 'listening') statusDot.classList.add('listening');
    if (type === 'speaking') statusDot.classList.add('speaking');
}

async function toggleCall() {
    if (callBtn.classList.contains('active')) {
        await stopAiChat();
        await leaveChannel();
        callBtn.classList.remove('active');
        callBtn.innerHTML = '📞'; // Phone icon
        callBtn.classList.add('call-btn');
        callBtn.classList.remove('hangup-btn');
        updateUiStatus('Ready to connect');
        avatarHalo.style.transform = 'scale(1)';
    } else {
        updateUiStatus('Connecting...', 'neutral');
        callBtn.disabled = true;

        // Start Agora & Gemini
        await joinChannel(); // Placeholder for now, main focus AI
        await startAiChat();

        callBtn.disabled = false;
        callBtn.classList.add('active');
        callBtn.innerHTML = '❌'; // Hangup icon
        callBtn.classList.remove('call-btn');
        callBtn.classList.add('hangup-btn');
        avatarHalo.style.transform = 'scale(1.05)';
    }
}

// --- Agora Functions ---

async function fetchConfig() {
    try {
        const response = await fetch('http://localhost:8000/config');
        if (!response.ok) throw new Error("Failed to fetch config");
        const data = await response.json();
        return data.appId;
    } catch (error) {
        console.error("Error fetching App ID:", error);
        return null;
    }
}

async function fetchToken(channelName, uid) {
    try {
        const response = await fetch(`http://localhost:8000/rtc_token?channelName=${channelName}&uid=${uid}`);
        if (!response.ok) throw new Error("Failed to fetch token");
        const data = await response.json();
        return data.token;
    } catch (error) {
        console.error("Error fetching Token:", error);
        return null;
    }
}

async function joinChannel() {
    const channelName = "test_channel";
    const uid = Math.floor(Math.random() * 10000);

    const appId = await fetchConfig();
    if (!appId) return;

    const token = await fetchToken(channelName, uid);
    if (!token) return;

    try {
        await client.join(appId, channelName, token, uid);
        localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack();
        await client.publish([localAudioTrack]);

        // Volume Visualizer Logic for Agora (User Voice)
        setInterval(() => {
            if (localAudioTrack) {
                const volume = localAudioTrack.getVolumeLevel();
                // Map volume 0-1 to ripple size 200px - 300px
                const size = 200 + (volume * 150);
                rippleRing.style.width = `${size}px`;
                rippleRing.style.height = `${size}px`;
                if (volume > 0.1) {
                    rippleRing.classList.add('ripple-active');
                    updateUiStatus('Listening...', 'listening');
                } else {
                    rippleRing.classList.remove('ripple-active');
                }
            }
        }, 100);

    } catch (error) {
        console.error("Agora Join Error:", error);
    }
}

async function leaveChannel() {
    if (localAudioTrack) {
        localAudioTrack.close();
        localAudioTrack = null;
    }
    await client.leave();
}

// --- Gemini AI Chat Functions (Browser Relay) ---

async function startAiChat() {
    try {
        // 1. Setup Audio Context
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });

        // 2. WebSocket Connect
        websocket = new WebSocket("ws://localhost:8000/ws/chat");

        websocket.onopen = async () => {
            updateUiStatus('Connected! Say Hello', 'connected');
            // Start Recording
            await startRecording();
        };

        websocket.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            // Handle Server Content (Audio)
            if (data.serverContent && data.serverContent.modelTurn) {
                updateUiStatus('AI Speaking...', 'speaking');

                const parts = data.serverContent.modelTurn.parts;
                for (const part of parts) {
                    if (part.inlineData && part.inlineData.data) {
                        playPcmAudio(part.inlineData.data);
                    }
                }

                // Reset status after a short delay (simple heuristic)
                setTimeout(() => {
                    if (websocket && websocket.readyState === WebSocket.OPEN) {
                        updateUiStatus('Listening...', 'listening');
                    }
                }, 2000);
            }
        };

        websocket.onclose = () => {
            updateUiStatus('Disconnected', 'neutral');
        };

    } catch (e) {
        console.error(e);
        updateUiStatus('Connection Error', 'neutral');
    }
}

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    source.connect(processor);
    processor.connect(audioContext.destination);

    processor.onaudioprocess = (e) => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            const inputData = e.inputBuffer.getChannelData(0);
            const pcmData = floatTo16BitPCM(inputData);
            const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcmData.buffer)));

            websocket.send(JSON.stringify({
                "realtime_input": {
                    "media_chunks": [{
                        "mime_type": "audio/pcm",
                        "data": base64Audio
                    }]
                }
            }));
        }
    };

    window.localAiStream = stream;
    window.aiProcessor = processor;
    window.aiSource = source;
}

function stopAiChat() {
    if (websocket) websocket.close();
    if (audioContext) audioContext.close();
    if (window.localAiStream) window.localAiStream.getTracks().forEach(track => track.stop());

    websocket = null;
    audioContext = null;
}

// Helper: Play PCM Audio from Base64 (Queued)
function playPcmAudio(base64Data) {
    try {
        if (!playbackCtx) {
            playbackCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
        }

        const binaryString = atob(base64Data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        const int16Array = new Int16Array(bytes.buffer);
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }

        const buffer = playbackCtx.createBuffer(1, float32Array.length, 24000);
        buffer.getChannelData(0).set(float32Array);

        const source = playbackCtx.createBufferSource();
        source.buffer = buffer;
        source.connect(playbackCtx.destination);

        const currentTime = playbackCtx.currentTime;
        if (nextStartTime < currentTime) {
            nextStartTime = currentTime + 0.05;
        }

        source.start(nextStartTime);
        nextStartTime += buffer.duration;

    } catch (e) {
        console.error("Audio Playback Error:", e);
    }
}

function floatTo16BitPCM(output, offset, input) {
    const int16 = new Int16Array(output.length);
    for (let i = 0; i < output.length; i++) {
        let s = Math.max(-1, Math.min(1, output[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16;
}

// Init
document.getElementById('call-btn').addEventListener('click', toggleCall);
