import subprocess
import time
import numpy as np
import pyaudio
from pydub import AudioSegment
from threading import Event, Thread

class BluetoothDevice:
    def __init__(self, address, name):
        self.address = address
        self.name = name
        self.connected = False

    def connect(self):
        try:
            result = subprocess.run(['bluetoothconnector', '--connect', self.address],
                                 capture_output=True, text=True)
            self.connected = result.returncode == 0
            return self.connected
        except Exception as e:
            print(f"Error connecting to {self.name}: {e}")
            return False

    def disconnect(self):
        try:
            subprocess.run(['bluetoothconnector', '--disconnect', self.address],
                         capture_output=True, text=True)
            self.connected = False
        except Exception as e:
            print(f"Error disconnecting from {self.name}: {e}")

class AudioManager:
    def __init__(self, audio_file):
        self.audio_file = audio_file
        self.audio = AudioSegment.from_mp3(audio_file)
        
        if self.audio.channels != 2:
            raise ValueError("Audio file must be stereo")
        
        # Apply a slight delay to compensate for Bluetooth latency differences
        # This is configurable and may need adjustment based on your specific devices
        self.sync_offset_ms = 0  # Start with no offset, adjust as needed
        
        # Split into separate channels
        self.left_audio = self.audio.split_to_mono()[0]
        self.right_audio = self.audio.split_to_mono()[1]
        
        # Apply any sync offset if needed
        if self.sync_offset_ms > 0:
            # Add silence to the beginning of the left channel
            self.left_audio = AudioSegment.silent(duration=self.sync_offset_ms) + self.left_audio
        elif self.sync_offset_ms < 0:
            # Add silence to the beginning of the right channel
            self.right_audio = AudioSegment.silent(duration=-self.sync_offset_ms) + self.right_audio
        
        # Make sure both channels are the same length
        max_length = max(len(self.left_audio), len(self.right_audio))
        if len(self.left_audio) < max_length:
            self.left_audio = self.left_audio + AudioSegment.silent(duration=max_length - len(self.left_audio))
        if len(self.right_audio) < max_length:
            self.right_audio = self.right_audio + AudioSegment.silent(duration=max_length - len(self.right_audio))
        
        # Convert to numpy arrays and normalize
        self.left_channel = np.array(self.left_audio.get_array_of_samples()).astype(np.float32)
        self.right_channel = np.array(self.right_audio.get_array_of_samples()).astype(np.float32)
        
        # Normalize to [-1.0, 1.0]
        self.left_channel = self.left_channel / (1 << (8 * self.audio.sample_width - 1))
        self.right_channel = self.right_channel / (1 << (8 * self.audio.sample_width - 1))
        
        self.sample_rate = self.audio.frame_rate
        self.pa = pyaudio.PyAudio()
        self.streams = {}
        self.buffer_size = 1024  # Smaller buffer size for better sync
        
    def list_audio_devices(self):
        devices = []
        for i in range(self.pa.get_device_count()):
            device_info = self.pa.get_device_info_by_index(i)
            if device_info['maxOutputChannels'] > 0:  # Output devices only
                devices.append(device_info)
        return devices
        
    def create_stream(self, device_info, channel_data):
        return self.pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.sample_rate,
            output=True,
            output_device_index=device_info['index'],
            frames_per_buffer=self.buffer_size,  # Use consistent buffer size
            stream_callback=self._callback_factory(channel_data)
        )
    
    def _callback_factory(self, channel_data):
        position = 0
        start_time = None
        
        def callback(in_data, frame_count, time_info, status):
            nonlocal position, start_time
            
            # Initialize start time on first callback for precise synchronization
            if start_time is None:
                start_time = time.time()
            
            # Calculate expected position based on elapsed time
            # This helps keep both streams in sync even if callbacks occur at different times
            elapsed_time = time.time() - start_time
            expected_position = int(elapsed_time * self.sample_rate)
            
            # Correct drift if it's significant (more than 2 buffer sizes)
            drift = expected_position - position
            if abs(drift) > self.buffer_size * 2:
                print(f"Correcting drift of {drift} samples")
                position = expected_position
            
            if position >= len(channel_data):
                return (np.zeros(frame_count, dtype=np.float32), pyaudio.paComplete)
            
            # Get the next chunk of audio data
            out_data = channel_data[position:position + frame_count]
            position += frame_count
            
            # Pad with zeros if we don't have enough data
            if len(out_data) < frame_count:
                out_data = np.pad(out_data, (0, frame_count - len(out_data)))
            
            return (out_data.astype(np.float32), pyaudio.paContinue)
        return callback

def get_bluetooth_devices():
    try:
        result = subprocess.run(['bluetoothconnector', '--inquiry'],
                             capture_output=True, text=True)
        devices = []
        for line in result.stdout.split('\n'):
            if ' - ' in line:
                address = line.split(' - ')[0].strip()
                name = line.split(' - ')[1].strip()
                devices.append(BluetoothDevice(address, name))
        return devices
    except Exception as e:
        print(f"Error listing Bluetooth devices: {e}")
        return []

def get_audio_device_by_name(pa, name):
    """Find an audio device by its name"""
    for i in range(pa.get_device_count()):
        device_info = pa.get_device_info_by_index(i)
        if name.lower() in device_info['name'].lower():
            return device_info
    return None

def main(audio_file_path, sync_offset_ms=0):
    print("\n=== Bluetooth Audio Stem Splitter ===")
    
    # Initialize audio manager
    print("\nStep 1: Loading audio file...")
    try:
        audio_manager = AudioManager(audio_file_path)
        # Apply any sync offset specified
        audio_manager.sync_offset_ms = sync_offset_ms
        if sync_offset_ms != 0:
            print(f"  - Applying sync offset of {sync_offset_ms}ms")
            # Reload audio with the new offset
            audio_manager = AudioManager(audio_file_path)
            audio_manager.sync_offset_ms = sync_offset_ms
            
        print(f"✓ Successfully loaded {audio_file_path}")
        print(f"  - Sample rate: {audio_manager.sample_rate} Hz")
        print(f"  - Duration: {len(audio_manager.left_channel) / audio_manager.sample_rate:.2f} seconds")
    except Exception as e:
        print(f"✗ Error loading audio file: {e}")
        return

    # Define our target devices
    print("\nStep 2: Setting up Bluetooth connections...")
    target_devices = [
        ('28-fa-19-08-57-9f', 'JBL Charge 5'),      # JBL Charge 5 (-34)
        ('a8-16-9d-d3-54-b8', 'JBL Charge 5 Wi-Fi') # JBL Charge 5 Wi-Fi (-37)
    ]

    devices = [BluetoothDevice(addr, name) for addr, name in target_devices]
    print("Target devices:")
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device.name} ({device.address}) - Will play {'left' if i == 1 else 'right'} channel")

    # Connect to selected devices
    try:
        device1 = devices[0]
        device2 = devices[1]
        
        print(f"\nStep 3: Establishing connections...")
        print(f"Connecting to {device1.name} (left channel)...")
        if not device1.connect():
            print(f"✗ Failed to connect to {device1.name}")
            print("  Please ensure the device is powered on and in pairing mode")
            return
        print(f"✓ Connected to {device1.name}")

        print(f"Connecting to {device2.name} (right channel)...")
        if not device2.connect():
            print(f"✗ Failed to connect to {device2.name}")
            print("  Please ensure the device is powered on and in pairing mode")
            device1.disconnect()
            return
        print(f"✓ Connected to {device2.name}")

        # Wait for devices to be ready
        print("\nStep 4: Preparing audio devices...")
        print("Waiting for devices to be ready...")
        time.sleep(2)

        # Find audio output devices
        print("Scanning for audio output devices...")
        device1_audio = get_audio_device_by_name(audio_manager.pa, device1.name)
        device2_audio = get_audio_device_by_name(audio_manager.pa, device2.name)

        if not (device1_audio and device2_audio):
            print("\n✗ Could not find matching audio output devices.")
            print("Available audio devices:")
            for i, device in enumerate(audio_devices):
                print(f"{i + 1}. {device['name']}")
            print("\nPlease ensure both JBL speakers are connected and recognized by macOS")
            print("You may need to select them in System Settings > Sound")
            return

        # Create audio streams
        print("\nStep 5: Setting up audio streams...")
        print(f"Creating stream for {device1.name} (left channel)...")
        stream1 = audio_manager.create_stream(device1_audio, audio_manager.left_channel)
        print(f"Creating stream for {device2.name} (right channel)...")
        stream2 = audio_manager.create_stream(device2_audio, audio_manager.right_channel)

        # Prepare for synchronized start
        print("\nStep 6: Preparing for synchronized playback...")
        
        # Pre-buffer audio to reduce initial latency
        time.sleep(0.5)  # Short delay to allow devices to initialize
        
        # Start both streams with minimal delay between them
        print("Starting synchronized playback...")
        print("Press Ctrl+C to stop playback")
        
        # Start streams with precise timing
        stream1.start_stream()
        # Minimal delay between stream starts
        time.sleep(0.001)  
        stream2.start_stream()

        # Wait for playback to complete
        try:
            while stream1.is_active() or stream2.is_active():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nPlayback interrupted")

        # Cleanup
        print("\nCleaning up...")
        stream1.stop_stream()
        stream2.stop_stream()
        stream1.close()
        stream2.close()
        device1.disconnect()
        device2.disconnect()

    except Exception as e:
        print(f"Error during playback: {e}")
        # Cleanup in case of error
        try:
            device1.disconnect()
            device2.disconnect()
        except:
            pass

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Stream audio to two Bluetooth devices with synchronized playback')
    parser.add_argument('audio_file', help='Path to the stereo audio file (MP3)')
    parser.add_argument('--sync-offset', type=int, default=0, 
                        help='Sync offset in milliseconds. Positive values delay left channel, negative values delay right channel')
    
    args = parser.parse_args()
    main(args.audio_file, args.sync_offset)




    
    # Initialize audio splitter with your audio file
    try:
        splitter = AudioSplitter("kyoto.mp3")  # Replace with your audio file
        streams = splitter.create_audio_streams(list(bluetooth_manager.devices.values()))
        
        print("\nStarting audio playback...")
        # Start playback on all devices simultaneously
        for device_info in streams.values():
            device_info['stream'].start_stream()
            
        # Keep the script running while audio plays
        try:
            while any(not stream['stream'].is_stopped() for stream in streams.values()):
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping playback...")
        finally:
            # Clean up streams
            for device_info in streams.values():
                device_info['stream'].stop_stream()
                device_info['stream'].close()
            
    except Exception as e:
        print(f"Error during playback: {e}")

if __name__ == "__main__":
    main()