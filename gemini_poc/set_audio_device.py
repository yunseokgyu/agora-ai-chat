
import sys
import pyaudio
import numpy as np
import os

if len(sys.argv) < 2:
    print("Usage: python set_audio_device.py <device_index>")
    sys.exit(1)

selected_index = int(sys.argv[1])
print(f"Testing audio device index: {selected_index}")

p = pyaudio.PyAudio()

try:
    info = p.get_device_info_by_index(selected_index)
    print(f"Device: {info['name']}")
    
    # Get default sample rate
    fs = int(info['defaultSampleRate'])
    print(f"Using Sample Rate: {fs} Hz")

    # Play test tone
    duration = 1.0  # seconds
    f = 440.0       # sine frequency, Hz, A4
    samples = (np.sin(2*np.pi*np.arange(fs*duration)*f/fs)).astype(np.float32)
    
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=fs,
                    output=True,
                    output_device_index=selected_index)
    
    print("Playing test tone...")
    stream.write(samples.tobytes())
    stream.stop_stream()
    stream.close()
    print("Test tone finished.")
    
    # Update .env
    env_path = "gemini_poc/.env"
    
    # Read existing lines
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
            
    # Remove existing GEMINI_OUTPUT_DEVICE_INDEX
    lines = [line for line in lines if not line.startswith("GEMINI_OUTPUT_DEVICE_INDEX=")]
    
    # Add new index
    lines.append(f"\nGEMINI_OUTPUT_DEVICE_INDEX={selected_index}")
    
    with open(env_path, "w") as f:
        f.writelines(lines)
        
    print(f"Saved GEMINI_OUTPUT_DEVICE_INDEX={selected_index} to {env_path}")

except Exception as e:
    print(f"Error: {e}")

p.terminate()
