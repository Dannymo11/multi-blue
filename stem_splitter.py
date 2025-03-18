import os
import numpy as np
from pydub import AudioSegment
import tempfile
import shutil
from spleeter.separator import Separator

class StemSplitter:
    """
    A class to handle audio stem separation using Spleeter.
    """
    
    def __init__(self, num_stems=4):
        """
        Initialize the stem splitter.
        
        Args:
            num_stems (int): Number of stems to separate into (2, 4, or 5)
                2: vocals and accompaniment
                4: vocals, drums, bass, and other
                5: vocals, drums, bass, piano, and other
        """
        if num_stems not in [2, 4, 5]:
            raise ValueError("Number of stems must be 2, 4, or 5")
            
        self.num_stems = num_stems
        self.separator = Separator(f'spleeter:{num_stems}stems')
        self.temp_dir = None
        self.stems = {}
        
    def separate(self, audio_file):
        """
        Separate the audio file into stems.
        
        Args:
            audio_file (str): Path to the audio file to separate
            
        Returns:
            dict: Dictionary of stem names to numpy arrays
        """
        # Create a temporary directory for Spleeter output
        self.temp_dir = tempfile.mkdtemp()
        
        try:
            # Run Spleeter to separate the stems
            self.separator.separate_to_file(audio_file, self.temp_dir)
            
            # Get the base filename without extension
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            stems_dir = os.path.join(self.temp_dir, base_name)
            
            # Load each stem as a numpy array
            self.stems = {}
            
            if self.num_stems == 2:
                stem_files = ['vocals.wav', 'accompaniment.wav']
            elif self.num_stems == 4:
                stem_files = ['vocals.wav', 'drums.wav', 'bass.wav', 'other.wav']
            else:  # 5 stems
                stem_files = ['vocals.wav', 'drums.wav', 'bass.wav', 'piano.wav', 'other.wav']
                
            for stem_file in stem_files:
                stem_name = os.path.splitext(stem_file)[0]
                stem_path = os.path.join(stems_dir, stem_file)
                
                # Load the stem audio
                audio = AudioSegment.from_wav(stem_path)
                
                # Convert to mono and get numpy array
                audio_mono = audio.set_channels(1)
                samples = np.array(audio_mono.get_array_of_samples()).astype(np.float32)
                
                # Normalize to [-1.0, 1.0]
                samples = samples / (1 << (8 * audio.sample_width - 1))
                
                # Store the stem
                self.stems[stem_name] = {
                    'samples': samples,
                    'sample_rate': audio.frame_rate
                }
                
            return self.stems
                
        except Exception as e:
            print(f"Error separating stems: {e}")
            raise
            
    def combine_stems(self, stem_names):
        """
        Combine multiple stems into a single audio channel.
        
        Args:
            stem_names (list): List of stem names to combine
            
        Returns:
            tuple: (combined samples as numpy array, sample rate)
        """
        if not self.stems:
            raise ValueError("No stems available. Call separate() first.")
            
        # Check if all requested stems exist
        for stem in stem_names:
            if stem not in self.stems:
                raise ValueError(f"Stem '{stem}' not found. Available stems: {list(self.stems.keys())}")
        
        # Get the first stem to determine sample rate and length
        first_stem = self.stems[stem_names[0]]
        sample_rate = first_stem['sample_rate']
        combined = np.zeros_like(first_stem['samples'])
        
        # Add all stems together
        for stem_name in stem_names:
            combined += self.stems[stem_name]['samples']
            
        # Normalize to prevent clipping
        max_val = np.max(np.abs(combined))
        if max_val > 1.0:
            combined = combined / max_val
            
        return combined, sample_rate
        
    def cleanup(self):
        """
        Clean up temporary files.
        """
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            
    def __del__(self):
        """
        Ensure cleanup when the object is destroyed.
        """
        self.cleanup()
