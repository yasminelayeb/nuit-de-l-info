import numpy as np
import librosa
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
import json
import os

class AudioProcessor:
    def __init__(self, config_file="config/settings.json"):
        """Initialize audio processor"""
        self.config = self.load_config(config_file)
        
    def load_config(self, config_file):
        """Load configuration"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def normalize_audio(self, input_file, output_file=None):
        """
        Normalize audio levels (make consistent volume)
        
        Args:
            input_file: Path to input audio file
            output_file: Path to output file (default: input_normalized.ext)
            
        Returns:
            Path to normalized file
        """
        if output_file is None:
            base, ext = os.path.splitext(input_file)
            output_file = f"{base}_normalized{ext}"
        
        print(f"🔊 Normalizing: {input_file}")
        
        # Load audio
        audio = AudioSegment.from_file(input_file)
        
        # Normalize (bring to standard volume)
        normalized_audio = normalize(audio)
        
        # Export
        normalized_audio.export(output_file, format=output_file.split('.')[-1])
        
        print(f"✅ Normalized audio saved: {output_file}")
        return output_file
    
    def remove_noise(self, input_file, output_file=None):
        """
        Reduce background noise using spectral gating
        
        Args:
            input_file: Path to input audio file
            output_file: Path to output file
            
        Returns:
            Path to cleaned file
        """
        if output_file is None:
            base, ext = os.path.splitext(input_file)
            output_file = f"{base}_cleaned{ext}"
        
        print(f"🧹 Removing noise: {input_file}")
        
        # Load audio with librosa
        y, sr = librosa.load(input_file, sr=None)
        
        # Estimate noise (first 0.5 seconds assumed to be noise)
        noise_sample = y[:int(0.5 * sr)]
        
        # Calculate noise threshold
        noise_threshold = np.mean(np.abs(noise_sample)) * 1.5
        
        # Simple noise gate
        y_cleaned = np.where(np.abs(y) > noise_threshold, y, 0)
        
        # Save
        import soundfile as sf
        sf.write(output_file, y_cleaned, sr)
        
        print(f"✅ Noise-reduced audio saved: {output_file}")
        return output_file
    
    def trim_silence(self, input_file, output_file=None, threshold_db=-40):
        """
        Remove silence from beginning and end
        
        Args:
            input_file: Path to input audio file
            output_file: Path to output file
            threshold_db: Silence threshold in dB
            
        Returns:
            Path to trimmed file
        """
        if output_file is None:
            base, ext = os.path.splitext(input_file)
            output_file = f"{base}_trimmed{ext}"
        
        print(f"✂️ Trimming silence: {input_file}")
        
        # Load audio
        audio = AudioSegment.from_file(input_file)
        
        # Find non-silent parts
        def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
            trim_ms = 0
            while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
                trim_ms += chunk_size
            return trim_ms
        
        start_trim = detect_leading_silence(audio, threshold_db)
        end_trim = detect_leading_silence(audio.reverse(), threshold_db)
        
        duration = len(audio)
        trimmed = audio[start_trim:duration-end_trim]
        
        # Export
        trimmed.export(output_file, format=output_file.split('.')[-1])
        
        print(f"✅ Trimmed audio saved: {output_file}")
        print(f"   Removed: {start_trim/1000:.2f}s from start, {end_trim/1000:.2f}s from end")
        return output_file
    
    def apply_compression(self, input_file, output_file=None):
        """
        Apply dynamic range compression (make quiet parts louder, loud parts quieter)
        
        Args:
            input_file: Path to input audio file
            output_file: Path to output file
            
        Returns:
            Path to compressed file
        """
        if output_file is None:
            base, ext = os.path.splitext(input_file)
            output_file = f"{base}_compressed{ext}"
        
        print(f"🎚️ Applying compression: {input_file}")
        
        # Load audio
        audio = AudioSegment.from_file(input_file)
        
        # Apply compression
        compressed = compress_dynamic_range(audio)
        
        # Export
        compressed.export(output_file, format=output_file.split('.')[-1])
        
        print(f"✅ Compressed audio saved: {output_file}")
        return output_file
    
    def change_speed(self, input_file, output_file=None, speed=1.0):
        """
        Change audio speed (pitch preserved)
        
        Args:
            input_file: Path to input audio file
            output_file: Path to output file
            speed: Speed multiplier (1.0 = normal, 1.5 = 50% faster, 0.75 = 25% slower)
            
        Returns:
            Path to speed-changed file
        """
        if output_file is None:
            base, ext = os.path.splitext(input_file)
            output_file = f"{base}_speed{speed}{ext}"
        
        print(f"⚡ Changing speed: {input_file} (x{speed})")
        
        # Load with librosa
        y, sr = librosa.load(input_file, sr=None)
        
        # Time stretch (preserves pitch)
        y_stretched = librosa.effects.time_stretch(y, rate=speed)
        
        # Save
        import soundfile as sf
        sf.write(output_file, y_stretched, sr)
        
        print(f"✅ Speed-changed audio saved: {output_file}")
        return output_file
    
    def extract_segment(self, input_file, output_file, start_sec, end_sec):
        """
        Extract a specific segment from audio
        
        Args:
            input_file: Path to input audio file
            output_file: Path to output file
            start_sec: Start time in seconds
            end_sec: End time in seconds
            
        Returns:
            Path to extracted segment
        """
        print(f"✂️ Extracting segment: {start_sec}s - {end_sec}s")
        
        # Load audio
        audio = AudioSegment.from_file(input_file)
        
        # Extract segment (pydub works in milliseconds)
        segment = audio[start_sec*1000:end_sec*1000]
        
        # Export
        segment.export(output_file, format=output_file.split('.')[-1])
        
        print(f"✅ Segment extracted: {output_file}")
        return output_file
    
    def merge_audio_files(self, input_files, output_file, crossfade_ms=0):
        """
        Merge multiple audio files into one
        
        Args:
            input_files: List of input audio file paths
            output_file: Path to output merged file
            crossfade_ms: Crossfade duration in milliseconds
            
        Returns:
            Path to merged file
        """
        print(f"🔗 Merging {len(input_files)} files...")
        
        # Load first file
        merged = AudioSegment.from_file(input_files[0])
        
        # Append other files
        for file in input_files[1:]:
            next_audio = AudioSegment.from_file(file)
            if crossfade_ms > 0:
                merged = merged.append(next_audio, crossfade=crossfade_ms)
            else:
                merged = merged + next_audio
        
        # Export
        merged.export(output_file, format=output_file.split('.')[-1])
        
        print(f"✅ Merged audio saved: {output_file}")
        return output_file
    
    def split_audio_by_duration(self, input_file, output_dir, segment_duration_sec=60):
        """
        Split audio into segments of specified duration
        
        Args:
            input_file: Path to input audio file
            output_dir: Directory to save segments
            segment_duration_sec: Duration of each segment in seconds
            
        Returns:
            List of segment file paths
        """
        print(f"✂️ Splitting audio into {segment_duration_sec}s segments...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Load audio
        audio = AudioSegment.from_file(input_file)
        
        # Calculate number of segments
        total_duration_ms = len(audio)
        segment_duration_ms = segment_duration_sec * 1000
        num_segments = int(np.ceil(total_duration_ms / segment_duration_ms))
        
        segments = []
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        
        for i in range(num_segments):
            start_ms = i * segment_duration_ms
            end_ms = min((i + 1) * segment_duration_ms, total_duration_ms)
            
            segment = audio[start_ms:end_ms]
            
            output_file = os.path.join(output_dir, f"{base_name}_part{i+1:03d}.mp3")
            segment.export(output_file, format="mp3")
            
            segments.append(output_file)
            print(f"   ✅ Segment {i+1}/{num_segments}: {output_file}")
        
        print(f"✅ Split into {len(segments)} segments")
        return segments
    
    def analyze_audio_quality(self, input_file):
        """
        Analyze audio quality metrics
        
        Args:
            input_file: Path to input audio file
            
        Returns:
            Dictionary with quality metrics
        """
        print(f"📊 Analyzing audio quality: {input_file}")
        
        # Load with librosa
        y, sr = librosa.load(input_file, sr=None)
        
        # Calculate metrics
        
        # 1. RMS (loudness)
        rms = librosa.feature.rms(y=y)[0]
        avg_rms = np.mean(rms)
        
        # 2. Zero crossing rate (noisiness)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        avg_zcr = np.mean(zcr)
        
        # 3. Spectral centroid (brightness)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        avg_centroid = np.mean(spectral_centroid)
        
        # 4. Dynamic range
        db = librosa.amplitude_to_db(np.abs(y), ref=np.max)
        dynamic_range = np.max(db) - np.min(db)
        
        # 5. Signal-to-noise ratio estimate
        noise_floor = np.percentile(np.abs(y), 10)
        signal_peak = np.max(np.abs(y))
        snr = 20 * np.log10(signal_peak / noise_floor) if noise_floor > 0 else 0
        
        quality = {
            "file": input_file,
            "sample_rate": sr,
            "duration_sec": len(y) / sr,
            "avg_loudness_rms": float(avg_rms),
            "avg_zero_crossing_rate": float(avg_zcr),
            "avg_spectral_centroid": float(avg_centroid),
            "dynamic_range_db": float(dynamic_range),
            "estimated_snr_db": float(snr),
            "quality_score": self._calculate_quality_score(avg_rms, dynamic_range, snr)
        }
        
        # Display report
        print(f"\n📊 QUALITY REPORT")
        print(f"   Duration: {quality['duration_sec']:.2f}s")
        print(f"   Sample Rate: {quality['sample_rate']} Hz")
        print(f"   Loudness: {quality['avg_loudness_rms']:.4f}")
        print(f"   Dynamic Range: {quality['dynamic_range_db']:.2f} dB")
        print(f"   SNR: {quality['estimated_snr_db']:.2f} dB")
        print(f"   Quality Score: {quality['quality_score']:.1f}/100")
        
        return quality
    
    def _calculate_quality_score(self, rms, dynamic_range, snr):
        """Calculate overall quality score (0-100)"""
        # Normalize metrics
        loudness_score = min(rms * 100, 100)  # Higher is better
        dynamic_score = min(dynamic_range / 60 * 100, 100)  # 60 dB = perfect
        snr_score = min(snr / 40 * 100, 100)  # 40 dB SNR = perfect
        
        # Weighted average
        quality = (loudness_score * 0.3 + dynamic_score * 0.3 + snr_score * 0.4)
        
        return quality
    
    def batch_process(self, input_files, operations):
        """
        Batch process multiple files with specified operations
        
        Args:
            input_files: List of input file paths
            operations: List of operations to apply ['normalize', 'denoise', 'trim', 'compress']
            
        Returns:
            List of processed file paths
        """
        print(f"\n🔄 BATCH PROCESSING: {len(input_files)} files")
        print(f"   Operations: {', '.join(operations)}")
        
        processed_files = []
        
        for i, input_file in enumerate(input_files, 1):
            print(f"\n[{i}/{len(input_files)}] Processing: {os.path.basename(input_file)}")
            
            current_file = input_file
            
            for operation in operations:
                base, ext = os.path.splitext(current_file)
                
                if operation == 'normalize':
                    current_file = self.normalize_audio(current_file)
                elif operation == 'denoise':
                    current_file = self.remove_noise(current_file)
                elif operation == 'trim':
                    current_file = self.trim_silence(current_file)
                elif operation == 'compress':
                    current_file = self.apply_compression(current_file)
            
            processed_files.append(current_file)
        
        print(f"\n✅ Batch processing complete: {len(processed_files)} files processed")
        return processed_files


# CLI Interface
if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("🎛️  AUDIO PROCESSOR")
    print("=" * 80)
    
    if len(sys.argv) < 3:
        print("\nUsage:")
        print("  python processor.py <operation> <input_file> [options]")
        print("\nOperations:")
        print("  normalize <file>              - Normalize audio levels")
        print("  denoise <file>                - Remove background noise")
        print("  trim <file>                   - Trim silence from edges")
        print("  compress <file>               - Apply dynamic compression")
        print("  speed <file> <multiplier>     - Change speed (e.g., 1.5)")
        print("  extract <file> <start> <end>  - Extract segment (seconds)")
        print("  merge <file1> <file2> ... <output> - Merge files")
        print("  split <file> <duration>       - Split into segments")
        print("  analyze <file>                - Analyze quality")
        sys.exit(1)
    
    processor = AudioProcessor()
    operation = sys.argv[1]
    
    if operation == "normalize":
        result = processor.normalize_audio(sys.argv[2])
        
    elif operation == "denoise":
        result = processor.remove_noise(sys.argv[2])
        
    elif operation == "trim":
        result = processor.trim_silence(sys.argv[2])
        
    elif operation == "compress":
        result = processor.apply_compression(sys.argv[2])
        
    elif operation == "speed":
        speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        result = processor.change_speed(sys.argv[2], speed=speed)
        
    elif operation == "extract":
        start = float(sys.argv[3])
        end = float(sys.argv[4])
        output = sys.argv[5] if len(sys.argv) > 5 else "extracted.mp3"
        result = processor.extract_segment(sys.argv[2], output, start, end)
        
    elif operation == "merge":
        input_files = sys.argv[2:-1]
        output_file = sys.argv[-1]
        result = processor.merge_audio_files(input_files, output_file)
        
    elif operation == "split":
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        output_dir = sys.argv[4] if len(sys.argv) > 4 else "segments"
        result = processor.split_audio_by_duration(sys.argv[2], output_dir, duration)
        
    elif operation == "analyze":
        result = processor.analyze_audio_quality(sys.argv[2])
        
    else:
        print(f"❌ Unknown operation: {operation}")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✅ Operation completed successfully")
