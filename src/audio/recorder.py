import pyaudio
import wave
import threading
import time
import os
from datetime import datetime
from pydub import AudioSegment
import json

class AudioRecorder:
    def __init__(self, config_file="config/settings.json"):
        """Initialize the audio recorder with configuration"""
        self.config = self.load_config(config_file)
        self.is_recording = False
        self.frames = []
        self.audio = None
        self.stream = None
        self.recording_thread = None
        self.current_file = None
        self.start_time = None
        
        # Audio parameters from config
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 2  # Stereo
        self.rate = int(self.config["audio"]["sample_rate"])
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "audio": {
                    "format": "wav",
                    "quality": "192k",
                    "sample_rate": "44100",
                    "max_duration": 60,
                    "smart_split": True
                },
                "storage": {
                    "path": "data/recordings",
                    "naming_pattern": "record_%jour%-%mois%-%annee%_%heure%h%minutes%"
                }
            }
    
    def generate_filename(self):
        """Generate filename based on the naming pattern"""
        now = datetime.now()
        pattern = self.config["storage"]["naming_pattern"]
        
        # Replace variables
        filename = pattern.replace("%jour%", now.strftime("%d"))
        filename = filename.replace("%mois%", now.strftime("%m"))
        filename = filename.replace("%annee%", now.strftime("%Y"))
        filename = filename.replace("%heure%", now.strftime("%H"))
        filename = filename.replace("%minutes%", now.strftime("%M"))
        filename = filename.replace("%secondes%", now.strftime("%S"))
        
        # Add extension
        extension = self.config["audio"]["format"]
        filename = f"{filename}.{extension}"
        
        # Create full path
        storage_path = self.config["storage"]["path"]
        os.makedirs(storage_path, exist_ok=True)
        
        return os.path.join(storage_path, filename)
    
    def start_recording(self):
        """Start audio recording"""
        if self.is_recording:
            print("Already recording!")
            return False
        
        try:
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            
            # Open stream
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            self.is_recording = True
            self.frames = []
            self.start_time = time.time()
            self.current_file = self.generate_filename()
            
            # Start recording in a separate thread
            self.recording_thread = threading.Thread(target=self._record)
            self.recording_thread.start()
            
            print(f"Recording started: {self.current_file}")
            return True
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            return False
    
    def _record(self):
        """Internal recording loop (runs in separate thread)"""
        max_duration = self.config["audio"]["max_duration"] * 60  # Convert to seconds
        
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
                
                # Check if max duration reached
                elapsed_time = time.time() - self.start_time
                if elapsed_time >= max_duration:
                    print(f"Max duration reached ({max_duration}s), splitting file...")
                    self._save_current_recording()
                    
                    # Start new recording if still recording
                    if self.is_recording:
                        self.frames = []
                        self.start_time = time.time()
                        self.current_file = self.generate_filename()
                        print(f"New file started: {self.current_file}")
                
            except Exception as e:
                print(f"Error during recording: {e}")
                break
    
    def stop_recording(self):
        """Stop audio recording and save file"""
        if not self.is_recording:
            print("Not recording!")
            return None
        
        self.is_recording = False
        
        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join()
        
        # Save the recording
        saved_file = self._save_current_recording()
        
        # Cleanup
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        print(f"Recording stopped and saved: {saved_file}")
        return saved_file
    
    def _save_current_recording(self):
        """Save current frames to file"""
        if not self.frames:
            print("No frames to save!")
            return None
        
        temp_wav = self.current_file.replace(
            f".{self.config['audio']['format']}", 
            "_temp.wav"
        )
        
        # Save as WAV first
        wf = wave.open(temp_wav, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        # Convert to desired format if not WAV
        output_format = self.config["audio"]["format"]
        if output_format != "wav":
            self._convert_audio(temp_wav, self.current_file, output_format)
            os.remove(temp_wav)  # Remove temporary WAV
        else:
            os.rename(temp_wav, self.current_file)
        
        return self.current_file
    
    def _convert_audio(self, input_file, output_file, output_format):
        """Convert audio to desired format"""
        try:
            audio = AudioSegment.from_wav(input_file)
            
            # Get quality (bitrate)
            quality = self.config["audio"]["quality"]
            
            # Export with specified format and quality
            audio.export(
                output_file,
                format=output_format,
                bitrate=quality
            )
            
            print(f"Converted {input_file} to {output_format} at {quality}")
            
        except Exception as e:
            print(f"Error converting audio: {e}")
    
    def get_recording_duration(self):
        """Get current recording duration in seconds"""
        if self.is_recording and self.start_time:
            return time.time() - self.start_time
        return 0
    
    def get_recording_info(self):
        """Get information about current recording"""
        return {
            "is_recording": self.is_recording,
            "duration": self.get_recording_duration(),
            "current_file": self.current_file,
            "sample_rate": self.rate,
            "channels": self.channels,
            "format": self.config["audio"]["format"]
        }
    
    def list_audio_devices(self):
        """List all available audio input devices"""
        audio = pyaudio.PyAudio()
        devices = []
        
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:
                devices.append({
                    "index": i,
                    "name": device_info["name"],
                    "channels": device_info["maxInputChannels"],
                    "sample_rate": int(device_info["defaultSampleRate"])
                })
        
        audio.terminate()
        return devices


# Test function
if __name__ == "__main__":
    print("=== Audio Recorder Test ===")
    
    recorder = AudioRecorder()
    
    # List available devices
    print("\nAvailable audio devices:")
    devices = recorder.list_audio_devices()
    for device in devices:
        print(f"  [{device['index']}] {device['name']} - {device['channels']} channels @ {device['sample_rate']} Hz")
    
    # Test recording
    print("\nStarting 5-second test recording...")
    recorder.start_recording()
    
    for i in range(5):
        time.sleep(1)
        duration = recorder.get_recording_duration()
        print(f"Recording... {duration:.1f}s")
    
    saved_file = recorder.stop_recording()
    print(f"\nRecording saved to: {saved_file}")
