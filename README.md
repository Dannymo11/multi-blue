# Bluetooth Audio Stem Splitter

This project enables streaming different stems of an audio file to separate Bluetooth audio devices simultaneously, creating an immersive listening experience. It can operate in two modes:

1. **Stereo Mode**: Splits a stereo audio file into left and right channels and sends each to a different Bluetooth speaker
2. **Stem Separation Mode**: Uses AI to separate an audio track into its component stems (vocals, drums, bass, other) and routes different stem combinations to each speaker

## Requirements
- macOS (uses CoreBluetooth framework)
- Python 3.8+
- Two or more Bluetooth audio devices
- FFmpeg (for audio processing)
- TensorFlow 2.x (for stem separation)

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

### Basic Usage (Stereo Mode)
```bash
python blue.py your_audio_file.mp3
```

The script will:
1. Connect to two specified Bluetooth devices
2. Split the stereo audio file into left and right channels
3. Stream left channel to first device, right channel to second device

### Advanced Usage (Stem Separation Mode)
```bash
python blue.py your_audio_file.mp3 --use-stems --left-stems vocals,other --right-stems drums,bass
```

This will:
1. Use AI to separate your audio file into stems (vocals, drums, bass, other)
2. Send vocals and other instruments to the left speaker
3. Send drums and bass to the right speaker

### Command Line Options
```
--sync-offset MILLISECONDS  # Adjust timing between speakers (positive = delay left, negative = delay right)
--use-stems                 # Enable stem separation mode
--left-stems STEMS         # Comma-separated list of stems for left speaker (vocals,drums,bass,other)
--right-stems STEMS        # Comma-separated list of stems for right speaker (vocals,drums,bass,other)
```

## Notes
- Audio synchronization between devices may vary depending on Bluetooth latency
- Supports MP3 and other audio formats
- Both audio devices must support A2DP profile for streaming
- Stem separation requires significant processing power and may take several minutes for the first run
- The first time you run stem separation, Spleeter will download pre-trained models (about 150MB)

## Stem Separation
The stem separation feature uses Spleeter, an open-source music source separation library developed by Deezer Research. It can separate audio tracks into:

- **vocals**: The main vocal track
- **drums**: Drum sounds and percussion
- **bass**: Bass guitar and low-frequency instruments
- **other**: All other instruments and sounds

You can create custom mixes by specifying which stems should go to each speaker.
