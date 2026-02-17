
import pyaudio

p = pyaudio.PyAudio()

print("Available Audio Devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"Index {i}: {info['name']} (Input Chans: {info['maxInputChannels']}, Output Chans: {info['maxOutputChannels']})")

p.terminate()
