import whisper
import torch
import json
import os
from datetime import datetime

class AudioTranscriber:
    def __init__(self, config_file="config/settings.json"):
        """Initialize the transcription module with Whisper"""
        self.config = self.load_config(config_file)
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"Using device: {self.device}")
        
    def load_config(self, config_file):
        """Load configuration"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "ai": {
                    "transcription": True,
                    "whisper_model": "base",
                    "language": "fr",
                    "ai_summary": True
                }
            }
    
    def load_model(self):
        """Load Whisper model (lazy loading)"""
        if self.model is None:
            model_name = self.config["ai"]["whisper_model"]
            print(f"Loading Whisper model: {model_name}...")
            self.model = whisper.load_model(model_name, device=self.device)
            print(f"Model loaded successfully!")
        return self.model
    
    def transcribe_audio(self, audio_file, language=None):
        """
        Transcribe audio file to text
        
        Args:
            audio_file: Path to audio file
            language: Language code (fr, en, auto, etc.)
            
        Returns:
            Dictionary with transcription results
        """
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")
        
        # Load model if not loaded
        model = self.load_model()
        
        # Get language from config if not specified
        if language is None:
            language = self.config["ai"]["language"]
        
        print(f"\nTranscribing: {audio_file}")
        print(f"Language: {language}")
        
        # Transcribe
        if language == "auto":
            result = model.transcribe(audio_file, fp16=False)
        else:
            result = model.transcribe(audio_file, language=language, fp16=False)
        
        # Extract information
        transcription = {
            "text": result["text"].strip(),
            "language": result.get("language", language),
            "segments": [],
            "duration": 0
        }
        
        # Process segments (timestamped text)
        for segment in result["segments"]:
            transcription["segments"].append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip()
            })
            transcription["duration"] = segment["end"]
        
        return transcription
    
    def generate_summary(self, text, style="detailed"):
        """
        Generate a summary from transcribed text
        
        Args:
            text: Full transcription text
            style: "short", "detailed", "bullet_points", "report"
            
        Returns:
            Summary text
        """
        # Simple extraction-based summary (can be improved with GPT/Claude API)
        sentences = text.split('. ')
        
        if style == "short":
            # First 3 sentences
            summary = '. '.join(sentences[:3]) + '.'
            return f"RÉSUMÉ COURT:\n{summary}"
        
        elif style == "detailed":
            # First 10 sentences
            summary = '. '.join(sentences[:10]) + '.'
            return f"RÉSUMÉ DÉTAILLÉ:\n{summary}"
        
        elif style == "bullet_points":
            # Extract key sentences
            key_sentences = sentences[:5]
            bullet_points = '\n'.join([f"• {s.strip()}" for s in key_sentences if s.strip()])
            return f"POINTS CLÉS:\n{bullet_points}"
        
        elif style == "report":
            # Structured report
            total_words = len(text.split())
            total_sentences = len(sentences)
            avg_sentence_length = total_words / max(total_sentences, 1)
            
            report = f"""COMPTE-RENDU:
            
Statistiques:
- Nombre de mots: {total_words}
- Nombre de phrases: {total_sentences}
- Longueur moyenne: {avg_sentence_length:.1f} mots/phrase

Contenu:
{'. '.join(sentences[:7]) + '.'}

[Voir transcription complète pour plus de détails]
"""
            return report
        
        return text
    
    def transcribe_and_save(self, audio_file, output_dir=None):
        """
        Transcribe audio and save results to files
        
        Args:
            audio_file: Path to audio file
            output_dir: Directory to save results (default: same as audio)
            
        Returns:
            Dictionary with paths to saved files
        """
        # Transcribe
        transcription = self.transcribe_audio(audio_file)
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(audio_file)
        
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        
        # Save full transcription
        transcript_file = os.path.join(output_dir, f"{base_name}_transcript.txt")
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"TRANSCRIPTION: {base_name}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Langue: {transcription['language']}\n")
            f.write(f"Durée: {transcription['duration']:.1f}s\n")
            f.write("=" * 80 + "\n\n")
            f.write(transcription['text'])
        
        # Save timestamped version
        timestamped_file = os.path.join(output_dir, f"{base_name}_timestamped.txt")
        with open(timestamped_file, 'w', encoding='utf-8') as f:
            f.write(f"TRANSCRIPTION HORODATÉE: {base_name}\n")
            f.write("=" * 80 + "\n\n")
            for segment in transcription['segments']:
                timestamp = f"[{self._format_time(segment['start'])} → {self._format_time(segment['end'])}]"
                f.write(f"{timestamp}\n{segment['text']}\n\n")
        
        # Generate and save summary
        if self.config["ai"]["ai_summary"]:
            summary_file = os.path.join(output_dir, f"{base_name}_summary.txt")
            
            summary_style = self.config["ai"].get("summary_format", "Résumé détaillé")
            style_map = {
                "Résumé court": "short",
                "Résumé détaillé": "detailed",
                "Points clés": "bullet_points",
                "Compte-rendu": "report"
            }
            style = style_map.get(summary_style, "detailed")
            
            summary = self.generate_summary(transcription['text'], style)
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"SYNTHÈSE: {base_name}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                f.write(summary)
        else:
            summary_file = None
        
        # Save JSON version
        json_file = os.path.join(output_dir, f"{base_name}_data.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(transcription, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Transcription saved:")
        print(f"   - Full text: {transcript_file}")
        print(f"   - Timestamped: {timestamped_file}")
        if summary_file:
            print(f"   - Summary: {summary_file}")
        print(f"   - JSON data: {json_file}")
        
        return {
            "transcript": transcript_file,
            "timestamped": timestamped_file,
            "summary": summary_file,
            "json": json_file,
            "transcription": transcription
        }
    
    def _format_time(self, seconds):
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def batch_transcribe(self, audio_files):
        """
        Transcribe multiple audio files
        
        Args:
            audio_files: List of audio file paths
            
        Returns:
            List of results
        """
        results = []
        total = len(audio_files)
        
        print(f"\n🎙️ Batch transcription: {total} files")
        print("=" * 80)
        
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n[{i}/{total}] Processing: {os.path.basename(audio_file)}")
            try:
                result = self.transcribe_and_save(audio_file)
                results.append({"file": audio_file, "success": True, "result": result})
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({"file": audio_file, "success": False, "error": str(e)})
        
        # Summary
        success_count = sum(1 for r in results if r["success"])
        print(f"\n" + "=" * 80)
        print(f"✅ Completed: {success_count}/{total} successful")
        
        return results
    
    def search_in_transcription(self, transcription, keyword):
        """
        Search for keyword in transcription segments
        
        Args:
            transcription: Transcription dictionary
            keyword: Search term
            
        Returns:
            List of matching segments with timestamps
        """
        matches = []
        keyword_lower = keyword.lower()
        
        for segment in transcription['segments']:
            if keyword_lower in segment['text'].lower():
                matches.append({
                    "timestamp": f"{self._format_time(segment['start'])} - {self._format_time(segment['end'])}",
                    "text": segment['text'],
                    "start": segment['start'],
                    "end": segment['end']
                })
        
        return matches


# Test and CLI
if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("🎙️  AUDIO TRANSCRIPTION MODULE")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python transcription.py <audio_file>")
        print("  python transcription.py <audio_file1> <audio_file2> ...")
        print("\nExample:")
        print("  python transcription.py data/recordings/emission.mp3")
        sys.exit(1)
    
    audio_files = sys.argv[1:]
    
    # Check if files exist
    for audio_file in audio_files:
        if not os.path.exists(audio_file):
            print(f"❌ Error: File not found: {audio_file}")
            sys.exit(1)
    
    # Initialize transcriber
    transcriber = AudioTranscriber()
    
    # Transcribe
    if len(audio_files) == 1:
        # Single file
        result = transcriber.transcribe_and_save(audio_files[0])
        
        # Display preview
        print("\n" + "=" * 80)
        print("📝 PREVIEW:")
        print("=" * 80)
        print(result['transcription']['text'][:500] + "...")
        
    else:
        # Batch processing
        results = transcriber.batch_transcribe(audio_files)
