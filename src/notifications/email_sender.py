import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import os

class EmailSender:
    def __init__(self, config_file="config/settings.json"):
        """Initialize email sender with configuration"""
        self.config = self.load_config(config_file)
        
    def load_config(self, config_file):
        """Load email configuration"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("email", {})
        else:
            return {
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
    
    def send_email(self, subject, body, recipients=None):
        """
        Send email alert
        
        Args:
            subject: Email subject
            body: Email body (can be HTML)
            recipients: List of recipients (default: from config)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.config.get("enabled", False):
            print("⚠️ Email alerts are disabled in configuration")
            return False
        
        # Get recipients
        if recipients is None:
            recipients_str = self.config.get("recipients", "")
            if not recipients_str:
                print("❌ No recipients configured")
                return False
            recipients = [r.strip() for r in recipients_str.split(';') if r.strip()]
        
        if not recipients:
            print("❌ No valid recipients")
            return False
        
        # Get sender info
        sender_email = self.config.get("sender_email", "")
        password = self.config.get("password", "")
        
        if not sender_email or not password:
            print("❌ Sender email or password not configured")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = sender_email
            message["To"] = ", ".join(recipients)
            
            # Add body
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    {body}
                    <hr>
                    <p style="color: gray; font-size: 12px;">
                        Envoyé automatiquement par le Module d'Enregistrement Audio<br>
                        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </body>
            </html>
            """
            
            part = MIMEText(html_body, "html")
            message.attach(part)
            
            # Connect to SMTP server
            smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
            smtp_port = self.config.get("smtp_port", 587)
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(message)
            
            print(f"✅ Email sent to {len(recipients)} recipient(s)")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
    
    def send_blank_alert(self, blank_info):
        """
        Send alert for abnormal silence/blank detection
        
        Args:
            blank_info: Dictionary with blank details
                {
                    "start_time": float,
                    "end_time": float,
                    "duration": float,
                    "file": str,
                    "type": "abnormal"
                }
        """
        if not self.config.get("alert_blank", True):
            return False
        
        subject = "⚠️ ALERTE: Blanc anormal détecté"
        
        body = f"""
        <h2 style="color: #d9534f;">⚠️ Blanc anormal détecté</h2>
        
        <p><strong>Un silence anormal a été détecté dans l'enregistrement.</strong></p>
        
        <table style="border-collapse: collapse; width: 100%;">
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Fichier:</strong></td>
                <td style="padding: 8px;">{blank_info.get('file', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Heure de début:</strong></td>
                <td style="padding: 8px;">{self._format_time(blank_info.get('start_time', 0))}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Heure de fin:</strong></td>
                <td style="padding: 8px;">{self._format_time(blank_info.get('end_time', 0))}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Durée:</strong></td>
                <td style="padding: 8px; color: #d9534f;"><strong>{blank_info.get('duration', 0):.2f} secondes</strong></td>
            </tr>
        </table>
        
        <p style="margin-top: 20px;">
            <strong>Action requise:</strong> Vérifiez l'enregistrement et l'équipement audio.
        </p>
        """
        
        return self.send_email(subject, body)
    
    def send_error_alert(self, error_info):
        """
        Send alert for recording errors
        
        Args:
            error_info: Dictionary with error details
        """
        if not self.config.get("alert_error", True):
            return False
        
        subject = "❌ ERREUR: Problème d'enregistrement"
        
        body = f"""
        <h2 style="color: #d9534f;">❌ Erreur d'enregistrement</h2>
        
        <p><strong>Une erreur est survenue lors de l'enregistrement.</strong></p>
        
        <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px;">
            <p><strong>Type d'erreur:</strong> {error_info.get('type', 'Inconnu')}</p>
            <p><strong>Message:</strong> {error_info.get('message', 'N/A')}</p>
            <p><strong>Fichier concerné:</strong> {error_info.get('file', 'N/A')}</p>
            <p><strong>Heure:</strong> {error_info.get('time', datetime.now().strftime('%H:%M:%S'))}</p>
        </div>
        
        <p style="margin-top: 20px;">
            <strong>Action requise:</strong> Vérifiez le système et relancez l'enregistrement si nécessaire.
        </p>
        """
        
        return self.send_email(subject, body)
    
    def send_storage_alert(self, storage_info):
        """
        Send alert for low storage space
        
        Args:
            storage_info: Dictionary with storage details
        """
        if not self.config.get("alert_storage", True):
            return False
        
        subject = "⚠️ ALERTE: Espace disque faible"
        
        body = f"""
        <h2 style="color: #f0ad4e;">⚠️ Espace disque faible</h2>
        
        <p><strong>L'espace disque disponible est insuffisant.</strong></p>
        
        <table style="border-collapse: collapse; width: 100%;">
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Chemin:</strong></td>
                <td style="padding: 8px;">{storage_info.get('path', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Espace disponible:</strong></td>
                <td style="padding: 8px; color: #f0ad4e;"><strong>{storage_info.get('available_gb', 0):.2f} GB</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Espace total:</strong></td>
                <td style="padding: 8px;">{storage_info.get('total_gb', 0):.2f} GB</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Utilisation:</strong></td>
                <td style="padding: 8px;">{storage_info.get('usage_percent', 0):.1f}%</td>
            </tr>
        </table>
        
        <p style="margin-top: 20px;">
            <strong>Action requise:</strong> Libérez de l'espace disque ou supprimez les anciens enregistrements.
        </p>
        """
        
        return self.send_email(subject, body)
    
    def send_daily_report(self, report_data):
        """
        Send daily recording report
        
        Args:
            report_data: Dictionary with report information
        """
        subject = f"📊 Rapport quotidien - {datetime.now().strftime('%Y-%m-%d')}"
        
        body = f"""
        <h2 style="color: #5cb85c;">📊 Rapport quotidien d'enregistrement</h2>
        
        <h3>Résumé du {datetime.now().strftime('%Y-%m-%d')}</h3>
        
        <table style="border-collapse: collapse; width: 100%;">
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Nombre d'enregistrements:</strong></td>
                <td style="padding: 8px;">{report_data.get('total_recordings', 0)}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Durée totale:</strong></td>
                <td style="padding: 8px;">{report_data.get('total_duration', '0h 0m')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Taille totale:</strong></td>
                <td style="padding: 8px;">{report_data.get('total_size', '0 MB')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Blancs anormaux:</strong></td>
                <td style="padding: 8px;">{report_data.get('abnormal_blanks', 0)}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f5f5f5;"><strong>Erreurs:</strong></td>
                <td style="padding: 8px;">{report_data.get('errors', 0)}</td>
            </tr>
        </table>
        
        <h3 style="margin-top: 20px;">Fichiers créés</h3>
        <ul>
        """
        
        for file_info in report_data.get('files', []):
            body += f"<li>{file_info}</li>"
        
        body += """
        </ul>
        
        <p style="margin-top: 20px; color: gray; font-size: 12px;">
            Ce rapport est généré automatiquement chaque jour.
        </p>
        """
        
        return self.send_email(subject, body)
    
    def _format_time(self, seconds):
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def test_connection(self):
        """Test email configuration"""
        print("\n🧪 Testing email configuration...")
        print(f"   SMTP Server: {self.config.get('smtp_server', 'N/A')}")
        print(f"   SMTP Port: {self.config.get('smtp_port', 'N/A')}")
        print(f"   Sender: {self.config.get('sender_email', 'N/A')}")
        print(f"   Recipients: {self.config.get('recipients', 'N/A')}")
        
        if not self.config.get("enabled"):
            print("\n⚠️ Email alerts are DISABLED")
            return False
        
        # Try to send test email
        subject = "✅ Test - Configuration Email"
        body = """
        <h2>✅ Test réussi</h2>
        <p>Votre configuration email fonctionne correctement.</p>
        <p>Vous recevrez désormais les alertes automatiques.</p>
        """
        
        return self.send_email(subject, body)


# CLI Test
if __name__ == "__main__":
    print("=" * 80)
    print("📧  EMAIL ALERT SYSTEM TEST")
    print("=" * 80)
    
    sender = EmailSender()
    
    # Test connection
    sender.test_connection()
    
    # Example: Send blank alert
    print("\nExample: Sending blank alert...")
    blank_info = {
        "file": "emission_05-12_14h30.mp3",
        "start_time": 1523.5,
        "end_time": 1528.5,
        "duration": 5.0,
        "type": "abnormal"
    }
    sender.send_blank_alert(blank_info)
