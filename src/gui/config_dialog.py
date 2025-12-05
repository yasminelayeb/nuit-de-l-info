from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QLineEdit, QPushButton, QComboBox, 
                             QSpinBox, QCheckBox, QFileDialog, QTabWidget,
                             QWidget, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt
import json
import os

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = "config/settings.json"
        self.config = self.load_config()
        self.init_ui()
        self.load_values()
        
    def init_ui(self):
        self.setWindowTitle("Configuration du Module")
        self.setGeometry(150, 150, 700, 600)
        
        layout = QVBoxLayout()
        
        # Tabs pour organiser les paramètres
        tabs = QTabWidget()
        
        # Tab 1: Audio Settings
        tab_audio = self.create_audio_tab()
        tabs.addTab(tab_audio, "Audio")
        
        # Tab 2: Storage Settings
        tab_storage = self.create_storage_tab()
        tabs.addTab(tab_storage, "Stockage")
        
        # Tab 3: AI Settings
        tab_ai = self.create_ai_tab()
        tabs.addTab(tab_ai, "Intelligence Artificielle")
        
        # Tab 4: Email Alerts
        tab_email = self.create_email_tab()
        tabs.addTab(tab_email, "Alertes Email")
        
        layout.addWidget(tabs)
        
        # Boutons de validation
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Enregistrer")
        btn_save.clicked.connect(self.save_config)
        button_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        btn_test = QPushButton("Tester la configuration")
        btn_test.clicked.connect(self.test_config)
        button_layout.addWidget(btn_test)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_audio_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Format audio
        format_group = QGroupBox("Format Audio")
        format_layout = QVBoxLayout()
        
        format_h_layout = QHBoxLayout()
        format_h_layout.addWidget(QLabel("Format:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["wav", "mp3", "flac", "ogg", "m4a"])
        format_h_layout.addWidget(self.combo_format)
        format_layout.addLayout(format_h_layout)
        
        quality_h_layout = QHBoxLayout()
        quality_h_layout.addWidget(QLabel("Qualité (bitrate):"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["64k", "128k", "192k", "256k", "320k"])
        quality_h_layout.addWidget(self.combo_quality)
        format_layout.addLayout(quality_h_layout)
        
        sample_rate_layout = QHBoxLayout()
        sample_rate_layout.addWidget(QLabel("Sample Rate (Hz):"))
        self.combo_sample_rate = QComboBox()
        self.combo_sample_rate.addItems(["44100", "48000", "96000"])
        sample_rate_layout.addWidget(self.combo_sample_rate)
        format_layout.addLayout(sample_rate_layout)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Durée des fichiers
        duration_group = QGroupBox("Gestion de la Durée")
        duration_layout = QVBoxLayout()
        
        max_duration_layout = QHBoxLayout()
        max_duration_layout.addWidget(QLabel("Durée maximale par fichier (minutes):"))
        self.spin_max_duration = QSpinBox()
        self.spin_max_duration.setRange(1, 1440)  # 1 min à 24h
        self.spin_max_duration.setValue(60)
        max_duration_layout.addWidget(self.spin_max_duration)
        duration_layout.addLayout(max_duration_layout)
        
        self.check_smart_split = QCheckBox("Détection intelligente des longues discussions (ne pas couper)")
        duration_layout.addWidget(self.check_smart_split)
        
        duration_group.setLayout(duration_layout)
        layout.addWidget(duration_group)
        
        # Détection de silence
        silence_group = QGroupBox("Détection de Silence")
        silence_layout = QVBoxLayout()
        
        self.check_silence_detection = QCheckBox("Activer la détection de silence")
        silence_layout.addWidget(self.check_silence_detection)
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Seuil de silence (dB):"))
        self.spin_silence_threshold = QSpinBox()
        self.spin_silence_threshold.setRange(-60, -10)
        self.spin_silence_threshold.setValue(-40)
        threshold_layout.addWidget(self.spin_silence_threshold)
        silence_layout.addLayout(threshold_layout)
        
        min_silence_layout = QHBoxLayout()
        min_silence_layout.addWidget(QLabel("Durée minimale de silence (secondes):"))
        self.spin_min_silence = QSpinBox()
        self.spin_min_silence.setRange(1, 60)
        self.spin_min_silence.setValue(3)
        min_silence_layout.addWidget(self.spin_min_silence)
        silence_layout.addLayout(min_silence_layout)
        
        silence_group.setLayout(silence_layout)
        layout.addWidget(silence_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_storage_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Chemin de stockage
        path_group = QGroupBox("Chemin de Stockage")
        path_layout = QVBoxLayout()
        
        path_h_layout = QHBoxLayout()
        path_h_layout.addWidget(QLabel("Dossier:"))
        self.line_storage_path = QLineEdit()
        path_h_layout.addWidget(self.line_storage_path)
        btn_browse = QPushButton("Parcourir...")
        btn_browse.clicked.connect(self.browse_folder)
        path_h_layout.addWidget(btn_browse)
        path_layout.addLayout(path_h_layout)
        
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # Nomenclature des fichiers
        naming_group = QGroupBox("Nomenclature des Fichiers")
        naming_layout = QVBoxLayout()
        
        naming_layout.addWidget(QLabel("Pattern de nommage:"))
        self.line_naming_pattern = QLineEdit()
        self.line_naming_pattern.setPlaceholderText("ex: emission_%jour%-%mois%-%annee%_%heure%h%minutes%")
        naming_layout.addWidget(self.line_naming_pattern)
        
        naming_layout.addWidget(QLabel("Variables disponibles:"))
        variables_text = QLabel(
            "%jour% %mois% %annee% %heure% %minutes% %secondes%\n"
            "%emission% %type% %utilisateur%"
        )
        variables_text.setStyleSheet("color: gray; font-size: 10px;")
        naming_layout.addWidget(variables_text)
        
        naming_group.setLayout(naming_layout)
        layout.addWidget(naming_group)
        
        # Durée de vie des fichiers
        lifetime_group = QGroupBox("Durée de Vie des Fichiers")
        lifetime_layout = QVBoxLayout()
        
        self.check_auto_delete = QCheckBox("Suppression automatique")
        lifetime_layout.addWidget(self.check_auto_delete)
        
        lifetime_h_layout = QHBoxLayout()
        lifetime_h_layout.addWidget(QLabel("Conserver pendant:"))
        self.spin_lifetime_days = QSpinBox()
        self.spin_lifetime_days.setRange(1, 365)
        self.spin_lifetime_days.setValue(30)
        lifetime_h_layout.addWidget(self.spin_lifetime_days)
        lifetime_h_layout.addWidget(QLabel("jours"))
        lifetime_layout.addLayout(lifetime_h_layout)
        
        lifetime_group.setLayout(lifetime_layout)
        layout.addWidget(lifetime_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_ai_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Transcription
        transcription_group = QGroupBox("Transcription Audio")
        transcription_layout = QVBoxLayout()
        
        self.check_transcription = QCheckBox("Activer la transcription automatique")
        transcription_layout.addWidget(self.check_transcription)
        
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Modèle Whisper:"))
        self.combo_whisper_model = QComboBox()
        self.combo_whisper_model.addItems(["tiny", "base", "small", "medium", "large"])
        model_layout.addWidget(self.combo_whisper_model)
        transcription_layout.addLayout(model_layout)
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Langue:"))
        self.combo_language = QComboBox()
        self.combo_language.addItems(["fr", "en", "es", "de", "it", "auto"])
        lang_layout.addWidget(self.combo_language)
        transcription_layout.addLayout(lang_layout)
        
        transcription_group.setLayout(transcription_layout)
        layout.addWidget(transcription_group)
        
        # Synthèse intelligente
        summary_group = QGroupBox("Synthèse Intelligente")
        summary_layout = QVBoxLayout()
        
        self.check_ai_summary = QCheckBox("Générer une synthèse automatique")
        summary_layout.addWidget(self.check_ai_summary)
        
        summary_layout.addWidget(QLabel("Format de synthèse:"))
        self.combo_summary_format = QComboBox()
        self.combo_summary_format.addItems(["Résumé court", "Résumé détaillé", "Points clés", "Compte-rendu"])
        summary_layout.addWidget(self.combo_summary_format)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Classification des blancs
        blank_group = QGroupBox("Classification des Blancs (IA)")
        blank_layout = QVBoxLayout()
        
        self.check_blank_classification = QCheckBox("Utiliser l'IA pour détecter les blancs anormaux")
        blank_layout.addWidget(self.check_blank_classification)
        
        blank_layout.addWidget(QLabel("Un blanc naturel = pause musicale normale"))
        blank_layout.addWidget(QLabel("Un blanc anormal = coupure technique"))
        
        blank_group.setLayout(blank_layout)
        layout.addWidget(blank_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_email_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Configuration SMTP
        smtp_group = QGroupBox("Configuration SMTP")
        smtp_layout = QVBoxLayout()
        
        self.check_email_alerts = QCheckBox("Activer les alertes email")
        smtp_layout.addWidget(self.check_email_alerts)
        
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("Serveur SMTP:"))
        self.line_smtp_server = QLineEdit()
        self.line_smtp_server.setPlaceholderText("smtp.gmail.com")
        server_layout.addWidget(self.line_smtp_server)
        smtp_layout.addLayout(server_layout)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.spin_smtp_port = QSpinBox()
        self.spin_smtp_port.setRange(1, 65535)
        self.spin_smtp_port.setValue(587)
        port_layout.addWidget(self.spin_smtp_port)
        smtp_layout.addLayout(port_layout)
        
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("Email expéditeur:"))
        self.line_sender_email = QLineEdit()
        email_layout.addWidget(self.line_sender_email)
        smtp_layout.addLayout(email_layout)
        
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Mot de passe:"))
        self.line_email_password = QLineEdit()
        self.line_email_password.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.line_email_password)
        smtp_layout.addLayout(password_layout)
        
        recipient_layout = QHBoxLayout()
        recipient_layout.addWidget(QLabel("Destinataires (séparés par ;):"))
        self.line_recipients = QLineEdit()
        recipient_layout.addWidget(self.line_recipients)
        smtp_layout.addLayout(recipient_layout)
        
        smtp_group.setLayout(smtp_layout)
        layout.addWidget(smtp_group)
        
        # Types d'alertes
        alerts_group = QGroupBox("Types d'Alertes")
        alerts_layout = QVBoxLayout()
        
        self.check_alert_blank = QCheckBox("Alerter lors d'un blanc anormal")
        alerts_layout.addWidget(self.check_alert_blank)
        
        self.check_alert_error = QCheckBox("Alerter lors d'une erreur d'enregistrement")
        alerts_layout.addWidget(self.check_alert_error)
        
        self.check_alert_storage = QCheckBox("Alerter si l'espace disque est faible")
        alerts_layout.addWidget(self.check_alert_storage)
        
        alerts_group.setLayout(alerts_layout)
        layout.addWidget(alerts_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier de stockage")
        if folder:
            self.line_storage_path.setText(folder)
    
    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        default_config = {
            "audio": {
                "format": "wav",
                "quality": "192k",
                "sample_rate": "44100",
                "max_duration": 60,
                "smart_split": True,
                "silence_detection": True,
                "silence_threshold": -40,
                "min_silence_duration": 3
            },
            "storage": {
                "path": "data/recordings",
                "naming_pattern": "record_%jour%-%mois%-%annee%_%heure%h%minutes%",
                "auto_delete": True,
                "lifetime_days": 30
            },
            "ai": {
                "transcription": True,
                "whisper_model": "base",
                "language": "fr",
                "ai_summary": True,
                "summary_format": "Résumé détaillé",
                "blank_classification": True
            },
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "password": "",
                "recipients": "",
                "alert_blank": True,
                "alert_error": True,
                "alert_storage": True
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default_config
        return default_config
    
    def load_values(self):
        """Charge les valeurs depuis la config dans l'interface"""
        # Audio
        self.combo_format.setCurrentText(self.config["audio"]["format"])
        self.combo_quality.setCurrentText(self.config["audio"]["quality"])
        self.combo_sample_rate.setCurrentText(str(self.config["audio"]["sample_rate"]))
        self.spin_max_duration.setValue(self.config["audio"]["max_duration"])
        self.check_smart_split.setChecked(self.config["audio"]["smart_split"])
        self.check_silence_detection.setChecked(self.config["audio"]["silence_detection"])
        self.spin_silence_threshold.setValue(self.config["audio"]["silence_threshold"])
        self.spin_min_silence.setValue(self.config["audio"]["min_silence_duration"])
        
        # Storage
        self.line_storage_path.setText(self.config["storage"]["path"])
        self.line_naming_pattern.setText(self.config["storage"]["naming_pattern"])
        self.check_auto_delete.setChecked(self.config["storage"]["auto_delete"])
        self.spin_lifetime_days.setValue(self.config["storage"]["lifetime_days"])
        
        # AI
        self.check_transcription.setChecked(self.config["ai"]["transcription"])
        self.combo_whisper_model.setCurrentText(self.config["ai"]["whisper_model"])
        self.combo_language.setCurrentText(self.config["ai"]["language"])
        self.check_ai_summary.setChecked(self.config["ai"]["ai_summary"])
        self.combo_summary_format.setCurrentText(self.config["ai"]["summary_format"])
        self.check_blank_classification.setChecked(self.config["ai"]["blank_classification"])
        
        # Email
        self.check_email_alerts.setChecked(self.config["email"]["enabled"])
        self.line_smtp_server.setText(self.config["email"]["smtp_server"])
        self.spin_smtp_port.setValue(self.config["email"]["smtp_port"])
        self.line_sender_email.setText(self.config["email"]["sender_email"])
        self.line_email_password.setText(self.config["email"]["password"])
        self.line_recipients.setText(self.config["email"]["recipients"])
        self.check_alert_blank.setChecked(self.config["email"]["alert_blank"])
        self.check_alert_error.setChecked(self.config["email"]["alert_error"])
        self.check_alert_storage.setChecked(self.config["email"]["alert_storage"])
    
    def save_config(self):
        """Sauvegarde la configuration"""
        self.config = {
            "audio": {
                "format": self.combo_format.currentText(),
                "quality": self.combo_quality.currentText(),
                "sample_rate": self.combo_sample_rate.currentText(),
                "max_duration": self.spin_max_duration.value(),
                "smart_split": self.check_smart_split.isChecked(),
                "silence_detection": self.check_silence_detection.isChecked(),
                "silence_threshold": self.spin_silence_threshold.value(),
                "min_silence_duration": self.spin_min_silence.value()
            },
            "storage": {
                "path": self.line_storage_path.text(),
                "naming_pattern": self.line_naming_pattern.text(),
                "auto_delete": self.check_auto_delete.isChecked(),
                "lifetime_days": self.spin_lifetime_days.value()
            },
            "ai": {
                "transcription": self.check_transcription.isChecked(),
                "whisper_model": self.combo_whisper_model.currentText(),
                "language": self.combo_language.currentText(),
                "ai_summary": self.check_ai_summary.isChecked(),
                "summary_format": self.combo_summary_format.currentText(),
                "blank_classification": self.check_blank_classification.isChecked()
            },
            "email": {
                "enabled": self.check_email_alerts.isChecked(),
                "smtp_server": self.line_smtp_server.text(),
                "smtp_port": self.spin_smtp_port.value(),
                "sender_email": self.line_sender_email.text(),
                "password": self.line_email_password.text(),
                "recipients": self.line_recipients.text(),
                "alert_blank": self.check_alert_blank.isChecked(),
                "alert_error": self.check_alert_error.isChecked(),
                "alert_storage": self.check_alert_storage.isChecked()
            }
        }
        
        # Créer le dossier config s'il n'existe pas
        os.makedirs("config", exist_ok=True)
        
        # Sauvegarder
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, indent=4, fp=f)
        
        QMessageBox.information(self, "Succès", "Configuration sauvegardée avec succès!")
        self.accept()
    
    def test_config(self):
        """Teste la configuration"""
        QMessageBox.information(self, "Test", "Test de configuration - À implémenter")
