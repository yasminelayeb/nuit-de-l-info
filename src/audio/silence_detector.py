import numpy as np
import librosa
from pydub import AudioSegment
from pydub.silence import detect_silence, detect_nonsilent
import json
import os

class SilenceDetector:
    def __init__(self, config_file="config/settings.json"):
        """Initialize silence detector with configuration"""
        self.config = self.load_config(config_file)
        
        # Parameters from config
        self.silence_threshold = self.config["audio"]["silence_threshold"]  # in dB
        self.min_silence_duration = self.config["audio"]["min_silence_duration"] * 1000  # Convert to ms
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "audio": {
                    "silence_threshold": -40,
                    "min_silence_duration": 3,
                    "silence_detection": True
                }
            }
    
    def detect_silence_segments(self, audio_file):
        """
        Detect silence segments in an audio file
        Returns: List of tuples (start_ms, end_ms) for each silence segment
        """
        try:
            # Load audio file
            audio = AudioSegment.from_file(audio_file)
            
            # Detect silence
            silence_segments = detect_silence(
                audio,
                min_silence_len=self.min_silence_duration,
                silence_thresh=self.silence_threshold
            )
            
            # Convert to seconds for readability
            silence_segments_sec = [
                (start / 1000, end / 1000) 
                for start, end in silence_segments
            ]
            
            return silence_segments_sec
            
        except Exception as e:
            print(f"Error detecting silence: {e}")
            return []
    
    def detect_nonsilent_segments(self, audio_file):
        """
        Detect non-silent (audio) segments
        Returns: List of tuples (start_ms, end_ms) for each audio segment
        """
        try:
            audio = AudioSegment.from_file(audio_file)
            
            nonsilent_segments = detect_nonsilent(
                audio,
                min_silence_len=self.min_silence_duration,
                silence_thresh=self.silence_threshold
            )
            
            # Convert to seconds
            nonsilent_segments_sec = [
                (start / 1000, end / 1000) 
                for start, end in nonsilent_segments
            ]
            
            return nonsilent_segments_sec
            
        except Exception as e:
            print(f"Error detecting non-silent segments: {e}")
            return []
    
    def analyze_audio_levels(self, audio_file):
        """
        Analyze audio levels throughout the file
        Returns: Dictionary with analysis results
        """
        try:
            # Load audio with librosa
            y, sr = librosa.load(audio_file, sr=None)
            
            # Calculate RMS energy
            rms = librosa.feature.rms(y=y)[0]
            
            # Convert to dB
            db = librosa.amplitude_to_db(rms, ref=np.max)
            
            # Statistics
            analysis = {
                "duration_seconds": len(y) / sr,
                "sample_rate": sr,
                "avg_level_db": float(np.mean(db)),
                "max_level_db": float(np.max(db)),
                "min_level_db": float(np.min(db)),
                "std_level_db": float(np.std(db)),
                "silence_ratio": self._calculate_silence_ratio(db)
            }
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing audio levels: {e}")
            return None
    
    def _calculate_silence_ratio(self, db_levels):
        """Calculate the ratio of silence in the audio"""
        silence_frames = np.sum(db_levels < self.silence_threshold)
        total_frames = len(db_levels)
        
        if total_frames == 0:
            return 0.0
        
        return float(silence_frames / total_frames)
    
    def classify_silence_type(self, audio_file, silence_segment):
        """
        Classify if a silence segment is natural or abnormal
        
        Natural silence: Musical pauses, breaths between speech
        Abnormal silence: Technical cuts, broadcast interruptions
        
        Returns: "natural" or "abnormal"
        """
        try:
            start_sec, end_sec = silence_segment
            duration = end_sec - start_sec
            
            # Load audio
            y, sr = librosa.load(audio_file, sr=None, 
                                offset=max(0, start_sec - 1),  # 1s before silence
                                duration=duration + 2)  # +1s before and after
            
            # Analyze the context around the silence
            
            # 1. Check if there's a gradual fade (natural) or sudden cut (abnormal)
            if len(y) > sr * 0.5:  # At least 0.5s of audio
                # Check first and last 0.25s
                window_size = int(sr * 0.25)
                
                start_segment = y[:window_size]
                end_segment = y[-window_size:]
                
                # Calculate RMS for fade detection
                start_rms = np.sqrt(np.mean(start_segment**2))
                end_rms = np.sqrt(np.mean(end_segment**2))
                
                # If there's a gradual fade, it's likely natural
                if start_rms > 0.001 and end_rms > 0.001:
                    fade_ratio = min(start_rms, end_rms) / max(start_rms, end_rms)
                    
                    if fade_ratio > 0.3:  # Gradual transition
                        return "natural"
            
            # 2. Check silence duration
            # Very short silences (< 1s) in music are usually natural
            # Very long silences (> 5s) are usually abnormal in broadcast
            if duration < 1.0:
                return "natural"
            elif duration > 5.0:
                return "abnormal"
            
            # 3. Check frequency content before/after silence
            # Natural pauses usually have similar frequency content
            # Abnormal cuts might have different content
            
            # Default to natural if uncertain
            return "natural"
            
        except Exception as e:
            print(f"Error classifying silence: {e}")
            return "unknown"
    
    def detect_and_classify_all_silences(self, audio_file):
        """
        Detect all silences and classify them
        Returns: List of dictionaries with silence info
        """
        silence_segments = self.detect_silence_segments(audio_file)
        
        results = []
        for segment in silence_segments:
            start, end = segment
            duration = end - start
            
            classification = self.classify_silence_type(audio_file, segment)
            
            results.append({
                "start_time": start,
                "end_time": end,
                "duration": duration,
                "type": classification,
                "alert_needed": classification == "abnormal"
            })
        
        return results
    
    def generate_silence_report(self, audio_file):
        """
        Generate a comprehensive silence report
        """
        print(f"\n=== Silence Analysis Report ===")
        print(f"File: {audio_file}")
        
        # Audio analysis
        analysis = self.analyze_audio_levels(audio_file)
        if analysis:
            print(f"\nAudio Statistics:")
            print(f"  Duration: {analysis['duration_seconds']:.2f}s")
            print(f"  Average Level: {analysis['avg_level_db']:.2f} dB")
            print(f"  Max Level: {analysis['max_level_db']:.2f} dB")
            print(f"  Min Level: {analysis['min_level_db']:.2f} dB")
            print(f"  Silence Ratio: {analysis['silence_ratio']*100:.1f}%")
        
        # Silence detection
        silences = self.detect_and_classify_all_silences(audio_file)
        
        if silences:
            print(f"\nDetected Silences: {len(silences)}")
            
            abnormal_count = sum(1 for s in silences if s['type'] == 'abnormal')
            natural_count = sum(1 for s in silences if s['type'] == 'natural')
            
            print(f"  Natural: {natural_count}")
            print(f"  Abnormal: {abnormal_count} ⚠️")
            
            if abnormal_count > 0:
                print(f"\n⚠️ ALERT: {abnormal_count} abnormal silence(s) detected!")
            
            print("\nDetailed Silence List:")
            for i, silence in enumerate(silences, 1):
                alert_marker = "⚠️" if silence['alert_needed'] else "✓"
                print(f"  {alert_marker} Silence #{i}:")
                print(f"     Time: {silence['start_time']:.2f}s - {silence['end_time']:.2f}s")
                print(f"     Duration: {silence['duration']:.2f}s")
                print(f"     Type: {silence['type']}")
        else:
            print("\nNo significant silences detected.")
        
        return {
            "audio_analysis": analysis,
            "silences": silences,
            "abnormal_count": sum(1 for s in silences if s['type'] == 'abnormal')
        }


# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python silence_detector.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    if not os.path.exists(audio_file):
        print(f"Error: File '{audio_file}' not found!")
        sys.exit(1)
    
    detector = SilenceDetector()
    report = detector.generate_silence_report(audio_file)
