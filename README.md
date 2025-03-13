# Bluetooth Audio Stem Splitter

This project enables streaming different stems of an audio file to separate Bluetooth audio devices simultaneously, creating an immersive listening experience.

## Requirements
- macOS (uses CoreBluetooth framework)
- Python 3.8+
- Two or more Bluetooth audio devices

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure your Bluetooth devices are:
   - Powered on
   - In pairing mode
   - Within range

## Usage
1. Place your stereo audio file in the project directory
2. Modify the script to specify your audio file:
```python
splitter = AudioSplitter("your_audio_file.wav")
```
3. Run the script:
```bash
python blue.py
```

The script will:
1. Scan for available Bluetooth audio devices
2. Connect to two devices
3. Split the stereo audio file
4. Stream left channel to first device, right channel to second device

## Note
- Audio synchronization between devices may vary depending on Bluetooth latency
- Supports WAV and other formats supported by soundfile library
- Both audio devices must support A2DP profile for streaming
