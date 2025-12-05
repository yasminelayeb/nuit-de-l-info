from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QStatusBar, QTextEdit,
                             QProgressBar, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from gui.config_dialog import ConfigDialog
from audio.recorder import AudioRecorder
from audio.silence_detector import SilenceDetector
from ai.transcription import AudioTranscriber
from notifications.email_sender import EmailSender
import os

class ProcessingThread(QThread):
    """Thread for post-processing (silence detection, transcription)"""
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, audio_file, silence_detector, transcriber, email_sender):
        super().__init__()
        self.audio_file = audio_file
        self.silence_detector = silence_detector
        self.transcriber = transcriber
        self.email_sender = email_sender
        
    def run(self):
        results = {}
        
        try:
            # 1. Detect silences
            self.update_signal.emit("🔍 Détection des silences...")
            silences = self.silence_detector.detect_and_classify_all_silences(self.audio_file)
            
            abnormal = [s for s in silences if s['type'] == 'abnormal']
            results['silences'] = silences
            results['abnormal_count'] = len(abnormal)
            
            if abnormal:
                self.update_signal.emit(f"⚠️ {len(abnormal)} blanc(s) anormal(aux) détecté(s)")
                
                # Send email alerts
                for blank in abnormal:
                    blank_info = {
                        "file": self.audio_file,
                        "start_time": blank['start_time'],
                        "end_time": blank['end_time'],
                        "duration": blank['duration']
                    }
                    self.email_sender.send_blank_alert(blank_info)
            else:
                self.update_signal.emit("✅ Aucun blanc anormal détecté")
            
            # 2. Transcribe (if enabled)
            if self.transcriber.config["ai"]["transcription"]:
                self.update_signal.emit("🎙️ Transcription en cours (cela peut prendre du temps)...")
                
                transcription_result = self.transcriber.transcribe_and_save(self.audio_file)
                results['transcription'] = transcription_result
                
                self.update_signal.emit("✅ Transcription terminée")
            
            results['success'] = True
            
        except Exception as e:
            self.update_signal.emit(f"❌ Erreur: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
            
            # Send error alert
            error_info = {
                "type": "Processing Error",
                "message": str(e),
                "file": self.audio_file,
                "time": ""
            }
            self.email_sender.send_error_alert(error_info)
        
        self.finished_signal.emit(results)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize modules
        self.recorder = AudioRecorder()
        self.silence_detector = SilenceDetector()
        self.transcriber = AudioTranscriber()
        self.email_sender = EmailSender()
        
        # UI update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_recording_info)
        
        # Processing thread
        self.processing_thread = None
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Module d'Enregistrement Audio Professionnel")
        self.setGeometry(100, 100, 1000, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Title
        title = QLabel("🎙️ Système d'Enregistrement Audio Professionnel")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("margin: 20px; color: #2c3e50;")
        main_layout.addWidget(title)
        
        # Status section
        status_group = QGroupBox("État de l'enregistrement")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("⚪ Prêt")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(16)
        self.status_label.setFont(status_font)
        status_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #e74c3c;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        
        self.btn_start_recording = QPushButton("🔴 Démarrer l'enregistrement")
        self.btn_start_recording.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 15px;
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.btn_start_recording.clicked.connect(self.start_recording)
        buttons_layout.addWidget(self.btn_start_recording)
        
        self.btn_stop_recording = QPushButton("⏹️ Arrêter l'enregistrement")
        self.btn_stop_recording.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 15px;
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.btn_stop_recording.clicked.connect(self.stop_recording)
        self.btn_stop_recording.setEnabled(False)
        buttons_layout.addWidget(self.btn_stop_recording)
        
        main_layout.addLayout(buttons_layout)
        
        # Config button
        self.btn_config = QPushButton("⚙️ Configuration")
        self.btn_config.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                padding: 10px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.btn_config.clicked.connect(self.open_config)
        main_layout.addWidget(self.btn_config)
        
        # Info section
        info_group = QGroupBox("Informations et Logs")
        info_layout = QVBoxLayout()
        
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setStyleSheet("""
            QTextEdit {
                background-color: #ecf0f1;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        info_layout.addWidget(self.info_box)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("✅ Application démarrée")
        
        # Display available devices
        self.display_audio_devices()
        
    def display_audio_devices(self):
        """Display available audio devices"""
        devices = self.recorder.list_audio_devices()
        
        if devices:
            device_text = "🎤 Périphériques audio disponibles:\n"
            for device in devices:
                device_text += f"   • [{device['index']}] {device['name']} ({device['channels']} canaux, {device['sample_rate']} Hz)\n"
        else:
            device_text = "⚠️ Aucun périphérique audio détecté"
        
        self.info_box.setPlainText(device_text)
        
    def start_recording(self):
        """Start audio recording"""
        success = self.recorder.start_recording()
        
        if success:
            self.status_label.setText("🔴 Enregistrement en cours...")
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.btn_start_recording.setEnabled(False)
            self.btn_stop_recording.setEnabled(True)
            self.btn_config.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.update_timer.start(100)  # Update every 100ms
            
            self.info_box.append(f"\n{'='*60}")
            self.info_box.append(f"🔴 Enregistrement démarré: {self.recorder.current_file}")
            self.info_box.append(f"{'='*60}")
            
            self.statusBar.showMessage("🔴 Enregistrement en cours...")
        else:
            QMessageBox.critical(self, "Erreur", "Impossible de démarrer l'enregistrement. Vérifiez votre périphérique audio.")
            self.statusBar.showMessage("❌ Erreur lors du démarrage")
        
    def stop_recording(self):
        """Stop audio recording"""
        self.update_timer.stop()
        self.status_label.setText("⏳ Arrêt et sauvegarde...")
        self.status_label.setStyleSheet("color: #f39c12;")
        
        saved_file = self.recorder.stop_recording()
        
        self.status_label.setText("✅ Enregistrement terminé")
        self.status_label.setStyleSheet("color: #27ae60;")
        self.btn_start_recording.setEnabled(True)
        self.btn_stop_recording.setEnabled(False)
        self.btn_config.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if saved_file:
            self.info_box.append(f"\n✅ Fichier sauvegardé: {saved_file}")
            self.statusBar.showMessage(f"✅ Enregistrement sauvegardé: {os.path.basename(saved_file)}")
            
            # Start post-processing
            self.process_recording(saved_file)
        else:
            QMessageBox.warning(self, "Attention", "L'enregistrement n'a pas pu être sauvegardé.")
            self.statusBar.showMessage("⚠️ Erreur de sauvegarde")
        
    def update_recording_info(self):
        """Update recording information while recording"""
        info = self.recorder.get_recording_info()
        duration = info['duration']
        
        # Update status
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        self.status_label.setText(f"🔴 Enregistrement: {minutes:02d}:{seconds:02d}")
        
        # Update progress bar
        max_duration = self.recorder.config["audio"]["max_duration"] * 60
        progress = int((duration / max_duration) * 100)
        self.progress_bar.setValue(min(progress, 100))
        
        # Update status bar
        self.statusBar.showMessage(f"🔴 Enregistrement: {minutes:02d}:{seconds:02d} - {os.path.basename(self.recorder.current_file)}")
        
    def process_recording(self, audio_file):
        """Process recording: detect silences, transcribe, send alerts"""
        self.info_box.append(f"\n{'='*60}")
        self.info_box.append("🔄 Post-traitement en cours...")
        self.info_box.append(f"{'='*60}")
        
        self.status_label.setText("🔄 Analyse en cours...")
        self.status_label.setStyleSheet("color: #3498db;")
        
        # Disable buttons during processing
        self.btn_start_recording.setEnabled(False)
        self.btn_config.setEnabled(False)
        
        # Start processing thread
        self.processing_thread = ProcessingThread(
            audio_file,
            self.silence_detector,
            self.transcriber,
            self.email_sender
        )
        
        self.processing_thread.update_signal.connect(self.on_processing_update)
        self.processing_thread.finished_signal.connect(self.on_processing_finished)
        self.processing_thread.start()
        
    def on_processing_update(self, message):
        """Handle processing updates"""
        self.info_box.append(message)
        self.statusBar.showMessage(message)
        
    def on_processing_finished(self, results):
        """Handle processing completion"""
        self.info_box.append(f"\n{'='*60}")
        
        if results.get('success'):
            self.info_box.append("✅ Post-traitement terminé avec succès")
            
            # Display summary
            if 'abnormal_count' in results:
                if results['abnormal_count'] > 0:
                    self.info_box.append(f"⚠️ {results['abnormal_count']} blanc(s) anormal(aux) détecté(s)")
                else:
                    self.info_box.append("✅ Aucun problème détecté")
            
            if 'transcription' in results:
                trans = results['transcription']
                self.info_box.append(f"📝 Transcription: {trans.get('transcript', 'N/A')}")
                self.info_box.append(f"📄 Résumé: {trans.get('summary', 'N/A')}")
            
            self.status_label.setText("✅ Prêt")
            self.status_label.setStyleSheet("color: #27ae60;")
            
        else:
            self.info_box.append(f"❌ Erreur: {results.get('error', 'Erreur inconnue')}")
            self.status_label.setText("❌ Erreur de traitement")
            self.status_label.setStyleSheet("color: #e74c3c;")
        
        self.info_box.append(f"{'='*60}\n")
        
        # Re-enable buttons
        self.btn_start_recording.setEnabled(True)
        self.btn_config.setEnabled(True)
        
        self.statusBar.showMessage("✅ Prêt pour un nouvel enregistrement")
        
    def open_config(self):
        """Open configuration dialog"""
        dialog = ConfigDialog(self)
        if dialog.exec_():
            # Reload configurations
            self.recorder = AudioRecorder()
            self.silence_detector = SilenceDetector()
            self.transcriber = AudioTranscriber()
            self.email_sender = EmailSender()
            
            self.info_box.append("\n⚙️ Configuration mise à jour")
            self.statusBar.showMessage("✅ Configuration sauvegardée")
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.recorder.is_recording:
            reply = QMessageBox.question(
                self,
                "Confirmation",
                "Un enregistrement est en cours. Voulez-vous vraiment quitter?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.recorder.stop_recording()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
