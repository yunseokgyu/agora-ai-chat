
import pyaudio
import sys

p = pyaudio.PyAudio()

print("\n--- Audio Output Devices ---")
output_devices = []
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxOutputChannels'] > 0:
        print(f"Index {i}: {info['name']}")
        output_devices.append(i)

print("\n-----------------------------")
try:
    selection = input("Enter the Index number of your Focusrite/Headphones: ")
    selected_index = int(selection)
    
    if selected_index in output_devices:
        print(f"\nYou selected Index {selected_index}. Initializing test...")
        
        # Simple beep test
        import numpy as np
        duration = 1.0  # seconds
        f = 440.0       # sine frequency, Hz, A4
        fs = 44100      # sampling rate, Hz
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
        print("Test tone finished. Did you hear it?")
        
        # Write selection to .env for client.py to use
        with open("gemini_poc/.env", "a") as f:
            f.write(f"\nGEMINI_OUTPUT_DEVICE_INDEX={selected_index}")
        print("Index saved to .env")

    else:
        print("Invalid index selected.")
except ValueError:
    print("Invalid input. Please enter a number.")
except Exception as e:
    print(f"Error: {e}")

p.terminate()
