import numpy as np
import librosa
import json
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pickle

class BlankClassifier:
    """
    AI-powered blank/silence classifier
    Uses machine learning to distinguish natural pauses from technical failures
    """
    
    def __init__(self, model_file="models/blank_classifier.pkl"):
        """Initialize the classifier"""
        self.model_file = model_file
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        # Try to load existing model
        self.load_model()
        
        # If no model exists, use rule-based fallback
        if not self.is_trained:
            print("⚠️ No trained model found. Using rule-based classification.")
    
    def extract_features(self, audio_segment, sr, context_before=None, context_after=None):
        """
        Extract features from audio segment for classification
        
        Args:
            audio_segment: Audio data (numpy array)
            sr: Sample rate
            context_before: Audio before the silence
            context_after: Audio after the silence
            
        Returns:
            Feature vector
        """
        features = []
        
        # 1. Duration-based features
        duration = len(audio_segment) / sr
        features.append(duration)
        
        # 2. Energy-based features
        rms = np.sqrt(np.mean(audio_segment**2))
        features.append(rms)
        
        # 3. Spectral features
        if len(audio_segment) > 512:
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_segment, sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_segment, sr=sr)
            
            features.append(np.mean(spectral_centroid))
            features.append(np.mean(spectral_rolloff))
        else:
            features.extend([0, 0])
        
        # 4. Context-based features (transition analysis)
        if context_before is not None and len(context_before) > 512:
            # Energy before silence
            rms_before = np.sqrt(np.mean(context_before**2))
            features.append(rms_before)
            
            # Fade detection
            fade_in = self._detect_fade(context_before)
            features.append(fade_in)
        else:
            features.extend([0, 0])
        
        if context_after is not None and len(context_after) > 512:
            # Energy after silence
            rms_after = np.sqrt(np.mean(context_after**2))
            features.append(rms_after)
            
            # Fade detection
            fade_out = self._detect_fade(context_after[::-1])  # Reverse to check fade out
            features.append(fade_out)
        else:
            features.extend([0, 0])
        
        # 5. Transition abruptness
        if context_before is not None and context_after is not None:
            abruptness = self._calculate_transition_abruptness(context_before, context_after)
            features.append(abruptness)
        else:
            features.append(0)
        
        # 6. Zero crossing rate (noisiness indicator)
        if len(audio_segment) > 0:
            zcr = np.mean(librosa.feature.zero_crossing_rate(audio_segment))
            features.append(zcr)
        else:
            features.append(0)
        
        return np.array(features)
    
    def _detect_fade(self, audio_segment):
        """
        Detect if there's a fade in/out
        Returns fade factor (0 = abrupt, 1 = smooth fade)
        """
        if len(audio_segment) < 100:
            return 0
        
        # Calculate RMS in windows
        window_size = len(audio_segment) // 10
        windows = []
        
        for i in range(10):
            start = i * window_size
            end = start + window_size
            if end <= len(audio_segment):
                window = audio_segment[start:end]
                windows.append(np.sqrt(np.mean(window**2)))
        
        if len(windows) < 2:
            return 0
        
        # Check if there's a gradual decrease/increase
        diffs = np.diff(windows)
        avg_change = np.mean(np.abs(diffs))
        
        # Smooth fade = consistent gradual change
        if avg_change > 0:
            consistency = 1 - (np.std(diffs) / (avg_change + 1e-6))
            return np.clip(consistency, 0, 1)
        
        return 0
    
    def _calculate_transition_abruptness(self, before, after):
        """
        Calculate how abrupt the transition is
        Returns abruptness score (0 = smooth, 1 = very abrupt)
        """
        # Get energy of last part of 'before' and first part of 'after'
        window_size = min(len(before), len(after), 2048)
        
        energy_before = np.sqrt(np.mean(before[-window_size:]**2))
        energy_after = np.sqrt(np.mean(after[:window_size]**2))
        
        # Calculate ratio
        if max(energy_before, energy_after) > 0:
            ratio = abs(energy_before - energy_after) / max(energy_before, energy_after)
            return ratio
        
        return 0
    
    def classify_blank_ml(self, audio_file, start_time, end_time):
        """
        Classify blank using machine learning model
        
        Args:
            audio_file: Path to audio file
            start_time: Start time of blank in seconds
            end_time: End time of blank in seconds
            
        Returns:
            "natural" or "abnormal"
        """
        if not self.is_trained:
            return self.classify_blank_rules(audio_file, start_time, end_time)
        
        # Load audio
        y, sr = librosa.load(audio_file, sr=None)
        
        # Extract segments
        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)
        
        # Context windows (1 second before/after)
        context_window = sr  # 1 second
        
        silence_segment = y[start_sample:end_sample]
        context_before = y[max(0, start_sample - context_window):start_sample]
        context_after = y[end_sample:min(len(y), end_sample + context_window)]
        
        # Extract features
        features = self.extract_features(silence_segment, sr, context_before, context_after)
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        confidence = np.max(self.model.predict_proba(features_scaled)[0])
        
        result = "natural" if prediction == 1 else "abnormal"
        
        print(f"   ML Classification: {result} (confidence: {confidence:.2f})")
        
        return result
    
    def classify_blank_rules(self, audio_file, start_time, end_time):
        """
        Classify blank using rule-based system (fallback)
        
        Args:
            audio_file: Path to audio file
            start_time: Start time of blank in seconds
            end_time: End time of blank in seconds
            
        Returns:
            "natural" or "abnormal"
        """
        duration = end_time - start_time
        
        # Load audio
        y, sr = librosa.load(audio_file, sr=None, 
                            offset=max(0, start_time - 1),
                            duration=duration + 2)
        
        # Rule 1: Very short silences are usually natural
        if duration < 0.5:
            return "natural"
        
        # Rule 2: Very long silences are usually abnormal
        if duration > 10:
            return "abnormal"
        
        # Rule 3: Check fade
        if len(y) > sr:
            context_window = sr // 4  # 0.25s
            
            if len(y) > context_window * 2:
                start_segment = y[:context_window]
                end_segment = y[-context_window:]
                
                rms_start = np.sqrt(np.mean(start_segment**2))
                rms_end = np.sqrt(np.mean(end_segment**2))
                
                # If both ends have similar energy and it's gradual
                if rms_start > 0.001 and rms_end > 0.001:
                    ratio = min(rms_start, rms_end) / max(rms_start, rms_end)
                    
                    if ratio > 0.3:  # Gradual transition
                        return "natural"
        
        # Rule 4: Medium duration with abrupt transition
        if duration > 3:
            return "abnormal"
        
        # Default to natural for uncertainty
        return "natural"
    
    def train_model(self, training_data_file):
        """
        Train the classifier with labeled data
        
        Args:
            training_data_file: JSON file with training examples
                Format: [
                    {
                        "audio_file": "path/to/file.wav",
                        "start_time": 10.5,
                        "end_time": 13.2,
                        "label": "natural"  # or "abnormal"
                    },
                    ...
                ]
        """
        print(f"📚 Training model from: {training_data_file}")
        
        # Load training data
        with open(training_data_file, 'r') as f:
            training_data = json.load(f)
        
        X = []
        y = []
        
        for example in training_data:
            audio_file = example['audio_file']
            start_time = example['start_time']
            end_time = example['end_time']
            label = example['label']
            
            if not os.path.exists(audio_file):
                print(f"⚠️ Skipping: {audio_file} (not found)")
                continue
            
            # Load audio
            audio, sr = librosa.load(audio_file, sr=None)
            
            # Extract segments
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            context_window = sr
            
            silence_segment = audio[start_sample:end_sample]
            context_before = audio[max(0, start_sample - context_window):start_sample]
            context_after = audio[end_sample:min(len(audio), end_sample + context_window)]
            
            # Extract features
            features = self.extract_features(silence_segment, sr, context_before, context_after)
            
            X.append(features)
            y.append(1 if label == "natural" else 0)
        
        if len(X) == 0:
            print("❌ No valid training examples found")
            return False
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"   Training samples: {len(X)}")
        print(f"   Features per sample: {X.shape[1]}")
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_scaled, y)
        
        # Calculate accuracy
        accuracy = self.model.score(X_scaled, y)
        print(f"   Training accuracy: {accuracy*100:.2f}%")
        
        self.is_trained = True
        
        # Save model
        self.save_model()
        
        return True
    
    def save_model(self):
        """Save trained model to disk"""
        if not self.is_trained:
            print("⚠️ No trained model to save")
            return
        
        os.makedirs(os.path.dirname(self.model_file), exist_ok=True)
        
        with open(self.model_file, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler
            }, f)
        
        print(f"✅ Model saved: {self.model_file}")
    
    def load_model(self):
        """Load trained model from disk"""
        if not os.path.exists(self.model_file):
            return False
        
        try:
            with open(self.model_file, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.is_trained = True
            
            print(f"✅ Model loaded: {self.model_file}")
            return True
        except Exception as e:
            print(f"⚠️ Error loading model: {e}")
            return False
    
    def evaluate_model(self, test_data_file):
        """
        Evaluate model on test data
        
        Args:
            test_data_file: JSON file with test examples (same format as training)
        """
        if not self.is_trained:
            print("❌ No trained model to evaluate")
            return
        
        print(f"🧪 Evaluating model on: {test_data_file}")
        
        with open(test_data_file, 'r') as f:
            test_data = json.load(f)
        
        correct = 0
        total = 0
        
        for example in test_data:
            audio_file = example['audio_file']
            start_time = example['start_time']
            end_time = example['end_time']
            true_label = example['label']
            
            if not os.path.exists(audio_file):
                continue
            
            predicted_label = self.classify_blank_ml(audio_file, start_time, end_time)
            
            if predicted_label == true_label:
                correct += 1
            
            total += 1
        
        if total > 0:
            accuracy = (correct / total) * 100
            print(f"\n📊 EVALUATION RESULTS")
            print(f"   Correct: {correct}/{total}")
            print(f"   Accuracy: {accuracy:.2f}%")
        else:
            print("❌ No valid test examples")


# CLI Interface
if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("🤖 AI BLANK CLASSIFIER")
    print("=" * 80)
    
    classifier = BlankClassifier()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python blank_classifier.py classify <audio_file> <start_sec> <end_sec>")
        print("  python blank_classifier.py train <training_data.json>")
        print("  python blank_classifier.py evaluate <test_data.json>")
        print("\nExample:")
        print("  python blank_classifier.py classify recording.wav 10.5 15.3")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "classify":
        audio_file = sys.argv[2]
        start_time = float(sys.argv[3])
        end_time = float(sys.argv[4])
        
        result = classifier.classify_blank_ml(audio_file, start_time, end_time)
        print(f"\n🏷️ Classification: {result.upper()}")
        
    elif command == "train":
        training_file = sys.argv[2]
        classifier.train_model(training_file)
        
    elif command == "evaluate":
        test_file = sys.argv[2]
        classifier.evaluate_model(test_file)
        
    else:
        print(f"❌ Unknown command: {command}")
