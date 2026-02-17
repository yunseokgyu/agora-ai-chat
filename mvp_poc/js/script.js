// Agora Globals
let client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
let localAudioTrack;

// Gemini Globals
let audioContext;   // For Microphone input
let playbackCtx;    // For Speaker output
let nextStartTime = 0;
let websocket;

// Visualizer Globals
let analyser;
let visualizerCanvas = document.getElementById('visualizer');
let visualizerCtx = visualizerCanvas.getContext('2d');

// --- UI Logic ---
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const callBtn = document.getElementById('call-btn');
const rippleRing = document.getElementById('ripple-ring');
const avatarHalo = document.getElementById('avatar-halo');

// Chat UI
const chatInterface = document.getElementById('chat-interface');
const chatToggleBtn = document.getElementById('chat-toggle-btn');
const closeChatBtn = document.getElementById('close-chat-btn');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatHistory = document.getElementById('chat-history');

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
        stopVisualizer();
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

// --- Visualizer Logic ---
function initVisualizer() {
    if (!playbackCtx) return;
    analyser = playbackCtx.createAnalyser();
    analyser.fftSize = 256;
    drawVisualizer();
}

function drawVisualizer() {
    if (!analyser) return;
    requestAnimationFrame(drawVisualizer);

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(dataArray);

    visualizerCtx.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);

    // Circular Visualizer
    const centerX = visualizerCanvas.width / 2;
    const centerY = visualizerCanvas.height / 2;
    const radius = 50;
    const bars = 40;

    for (let i = 0; i < bars; i++) {
        const value = dataArray[i];
        const barHeight = (value / 255) * 80;
        const rad = (i * 2 * Math.PI) / bars;

        const xStart = centerX + Math.cos(rad) * radius;
        const yStart = centerY + Math.sin(rad) * radius;
        const xEnd = centerX + Math.cos(rad) * (radius + barHeight);
        const yEnd = centerY + Math.sin(rad) * (radius + barHeight);

        visualizerCtx.strokeStyle = `rgba(255, 255, 255, ${value / 255})`;
        visualizerCtx.lineWidth = 4;
        visualizerCtx.beginPath();
        visualizerCtx.moveTo(xStart, yStart);
        visualizerCtx.lineTo(xEnd, yEnd);
        visualizerCtx.stroke();
    }
}

function stopVisualizer() {
    visualizerCtx.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
}


// --- Chat Logic ---
function toggleChat() {
    chatInterface.classList.toggle('hidden');
}

function addMessage(text, sender) {
    const div = document.createElement('div');
    div.classList.add('message');
    div.classList.add(sender === 'user' ? 'user-message' : 'ai-message');
    div.innerText = text;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    // 1. Show in UI
    addMessage(text, 'user');
    chatInput.value = '';

    // 2. Send to Backend
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({
            type: "text",
            text: text
        }));
    }
}


// --- Agora Functions ---

async function fetchConfig() {
    try {
        // Automatically detect current host (localhost or deployed)
        const protocol = window.location.protocol;
        const host = window.location.host;
        const configUrl = `${protocol}//${host}/config`; // Relative path

        const response = await fetch(configUrl);
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
        const protocol = window.location.protocol;
        const host = window.location.host;
        const tokenUrl = `${protocol}//${host}/rtc_token?channelName=${channelName}&uid=${uid}`;

        const response = await fetch(tokenUrl);
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
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        websocket = new WebSocket(`${protocol}//${host}/ws/chat`);

        websocket.onopen = async () => {
            updateUiStatus('Connected! Say Hello', 'connected');
            // Start Recording
            await startRecording();
        };

        websocket.onmessage = async (event) => {
            const data = JSON.parse(event.data);

            // Handle Text Message
            if (data.type === 'text') {
                addMessage(data.text, 'ai');
            }

            // Handle Server Content (Audio)
            if (data.serverContent && data.serverContent.modelTurn) {
                updateUiStatus('AI Speaking...', 'speaking');

                const parts = data.serverContent.modelTurn.parts;
                for (const part of parts) {
                    if (part.inlineData && part.inlineData.data) {
                        playPcmAudio(part.inlineData.data);
                    }
                    // Extract text parts if present in standard Gemini response
                    if (part.text) {
                        addMessage(part.text, 'ai');
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
            initVisualizer(); // Init visualizer when playback starts
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

        // Connect to Visualizer AND Speaker
        if (analyser) {
            source.connect(analyser); // Connect to visualizer
            analyser.connect(playbackCtx.destination); // Connect visualizer to speaker (pass-through)
        } else {
            source.connect(playbackCtx.destination);
        }

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

// Init Event Listeners
document.getElementById('call-btn').addEventListener('click', toggleCall);
chatToggleBtn.addEventListener('click', toggleChat);
closeChatBtn.addEventListener('click', toggleChat);
sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
