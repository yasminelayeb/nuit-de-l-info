import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

class FileManager:
    def __init__(self, config_file="config/settings.json", db_file="data/recordings.db"):
        """Initialize file manager with database"""
        self.config = self.load_config(config_file)
        self.db_file = db_file
        self.init_database()
        
    def load_config(self, config_file):
        """Load configuration"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "storage": {
                "path": "data/recordings",
                "auto_delete": True,
                "lifetime_days": 30
            }
        }
    
    def init_database(self):
        """Initialize SQLite database"""
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL UNIQUE,
                file_size INTEGER,
                duration REAL,
                format TEXT,
                sample_rate INTEGER,
                created_date TEXT,
                transcribed BOOLEAN DEFAULT 0,
                has_abnormal_blanks BOOLEAN DEFAULT 0,
                blank_count INTEGER DEFAULT 0,
                notes TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER,
                transcript_file TEXT,
                language TEXT,
                word_count INTEGER,
                created_date TEXT,
                FOREIGN KEY (recording_id) REFERENCES recordings (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blanks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER,
                start_time REAL,
                end_time REAL,
                duration REAL,
                type TEXT,
                alerted BOOLEAN DEFAULT 0,
                FOREIGN KEY (recording_id) REFERENCES recordings (id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Database initialized: {self.db_file}")
    
    def add_recording(self, filepath, **kwargs):
        """Add a recording to the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            # Get file info
            file_size = os.path.getsize(filepath)
            filename = os.path.basename(filepath)
            created_date = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO recordings (filename, filepath, file_size, duration, 
                                      format, sample_rate, created_date, 
                                      transcribed, has_abnormal_blanks, blank_count, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                filename,
                filepath,
                file_size,
                kwargs.get('duration', 0),
                kwargs.get('format', 'unknown'),
                kwargs.get('sample_rate', 44100),
                created_date,
                kwargs.get('transcribed', False),
                kwargs.get('has_abnormal_blanks', False),
                kwargs.get('blank_count', 0),
                kwargs.get('notes', '')
            ))
            
            recording_id = cursor.lastrowid
            conn.commit()
            
            print(f"✅ Recording added to database: {filename} (ID: {recording_id})")
            return recording_id
            
        except sqlite3.IntegrityError:
            print(f"⚠️ Recording already exists: {filepath}")
            return None
        finally:
            conn.close()
    
    def add_transcription(self, recording_id, transcript_file, language, word_count):
        """Add transcription info to database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transcriptions (recording_id, transcript_file, language, word_count, created_date)
            VALUES (?, ?, ?, ?, ?)
        """, (recording_id, transcript_file, language, word_count, datetime.now().isoformat()))
        
        # Update recording as transcribed
        cursor.execute("UPDATE recordings SET transcribed = 1 WHERE id = ?", (recording_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Transcription added for recording ID: {recording_id}")
    
    def add_blank(self, recording_id, start_time, end_time, duration, blank_type, alerted=False):
        """Add blank/silence info to database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO blanks (recording_id, start_time, end_time, duration, type, alerted)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (recording_id, start_time, end_time, duration, blank_type, alerted))
        
        # Update recording blank count
        cursor.execute("""
            UPDATE recordings 
            SET blank_count = (SELECT COUNT(*) FROM blanks WHERE recording_id = ?),
                has_abnormal_blanks = (SELECT COUNT(*) > 0 FROM blanks WHERE recording_id = ? AND type = 'abnormal')
            WHERE id = ?
        """, (recording_id, recording_id, recording_id))
        
        conn.commit()
        conn.close()
    
    def get_all_recordings(self):
        """Get all recordings from database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM recordings ORDER BY created_date DESC")
        columns = [description[0] for description in cursor.description]
        recordings = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return recordings
    
    def search_recordings(self, keyword=None, start_date=None, end_date=None, has_blanks=None):
        """Search recordings with filters"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        query = "SELECT * FROM recordings WHERE 1=1"
        params = []
        
        if keyword:
            query += " AND (filename LIKE ? OR notes LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if start_date:
            query += " AND created_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND created_date <= ?"
            params.append(end_date)
        
        if has_blanks is not None:
            query += " AND has_abnormal_blanks = ?"
            params.append(has_blanks)
        
        query += " ORDER BY created_date DESC"
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        recordings = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return recordings
    
    def delete_old_recordings(self, days=None):
        """Delete recordings older than specified days"""
        if days is None:
            days = self.config["storage"].get("lifetime_days", 30)
        
        if not self.config["storage"].get("auto_delete", False):
            print("⚠️ Auto-delete is disabled in configuration")
            return []
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Get recordings to delete
        cursor.execute("SELECT * FROM recordings WHERE created_date < ?", (cutoff_date,))
        old_recordings = cursor.fetchall()
        
        deleted_files = []
        
        for recording in old_recordings:
            recording_id, filename, filepath = recording[0], recording[1], recording[2]
            
            # Delete physical files
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    deleted_files.append(filepath)
                
                # Delete associated files (transcript, summary, etc.)
                base_path = os.path.splitext(filepath)[0]
                for ext in ['_transcript.txt', '_timestamped.txt', '_summary.txt', '_data.json']:
                    associated_file = base_path + ext
                    if os.path.exists(associated_file):
                        os.remove(associated_file)
                        deleted_files.append(associated_file)
                
                # Delete from database
                cursor.execute("DELETE FROM blanks WHERE recording_id = ?", (recording_id,))
                cursor.execute("DELETE FROM transcriptions WHERE recording_id = ?", (recording_id,))
                cursor.execute("DELETE FROM recordings WHERE id = ?", (recording_id,))
                
                print(f"🗑️ Deleted: {filename}")
                
            except Exception as e:
                print(f"❌ Error deleting {filename}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Deleted {len(deleted_files)} file(s) older than {days} days")
        return deleted_files
    
    def get_storage_stats(self):
        """Get storage statistics"""
        storage_path = self.config["storage"]["path"]
        
        if not os.path.exists(storage_path):
            return None
        
        # Get disk usage
        total, used, free = shutil.disk_usage(storage_path)
        
        # Get recordings stats
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(file_size), SUM(duration) FROM recordings")
        count, total_size, total_duration = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM recordings WHERE has_abnormal_blanks = 1")
        abnormal_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "storage_path": storage_path,
            "disk_total_gb": total / (1024**3),
            "disk_used_gb": used / (1024**3),
            "disk_free_gb": free / (1024**3),
            "disk_usage_percent": (used / total) * 100,
            "total_recordings": count or 0,
            "total_size_mb": (total_size or 0) / (1024**2),
            "total_duration_hours": (total_duration or 0) / 3600,
            "recordings_with_issues": abnormal_count or 0
        }
    
    def export_report(self, output_file="report.json"):
        """Export comprehensive report"""
        recordings = self.get_all_recordings()
        stats = self.get_storage_stats()
        
        report = {
            "generated_date": datetime.now().isoformat(),
            "statistics": stats,
            "recordings": recordings
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Report exported: {output_file}")
        return output_file
    
    def cleanup_orphaned_files(self):
        """Remove files not in database"""
        storage_path = self.config["storage"]["path"]
        
        if not os.path.exists(storage_path):
            return []
        
        # Get all files in database
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT filepath FROM recordings")
        db_files = set(row[0] for row in cursor.fetchall())
        conn.close()
        
        # Get all audio files in storage
        audio_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
        actual_files = []
        
        for ext in audio_extensions:
            actual_files.extend(Path(storage_path).rglob(f"*{ext}"))
        
        # Find orphaned files
        orphaned = []
        for file_path in actual_files:
            if str(file_path) not in db_files:
                orphaned.append(str(file_path))
        
        # Delete orphaned files
        for filepath in orphaned:
            try:
                os.remove(filepath)
                print(f"🗑️ Removed orphaned file: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"❌ Error removing {filepath}: {e}")
        
        return orphaned


# CLI Interface
if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("📁 FILE MANAGER")
    print("=" * 80)
    
    manager = FileManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            recordings = manager.get_all_recordings()
            print(f"\n📂 Total recordings: {len(recordings)}\n")
            for rec in recordings[:10]:  # Show first 10
                print(f"  • {rec['filename']}")
                print(f"    Created: {rec['created_date']}")
                print(f"    Size: {rec['file_size'] / 1024:.1f} KB")
                print()
        
        elif command == "stats":
            stats = manager.get_storage_stats()
            if stats:
                print(f"\n📊 STORAGE STATISTICS")
                print(f"  Total Recordings: {stats['total_recordings']}")
                print(f"  Total Size: {stats['total_size_mb']:.2f} MB")
                print(f"  Total Duration: {stats['total_duration_hours']:.2f} hours")
                print(f"  Recordings with Issues: {stats['recordings_with_issues']}")
                print(f"\n💾 DISK USAGE")
                print(f"  Free Space: {stats['disk_free_gb']:.2f} GB")
                print(f"  Used: {stats['disk_usage_percent']:.1f}%")
        
        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            deleted = manager.delete_old_recordings(days)
            print(f"\n🗑️ Deleted {len(deleted)} file(s)")
        
        elif command == "export":
            output = sys.argv[2] if len(sys.argv) > 2 else "report.json"
            manager.export_report(output)
        
        else:
            print(f"\nUsage:")
            print(f"  python file_manager.py list        - List recordings")
            print(f"  python file_manager.py stats       - Show statistics")
            print(f"  python file_manager.py cleanup [days] - Delete old files")
            print(f"  python file_manager.py export [file]  - Export report")
    else:
        # Interactive mode
        stats = manager.get_storage_stats()
        if stats:
            print(f"\n📊 STORAGE STATISTICS")
            print(f"  Path: {stats['storage_path']}")
            print(f"  Total Recordings: {stats['total_recordings']}")
            print(f"  Total Size: {stats['total_size_mb']:.2f} MB")
            print(f"  Free Space: {stats['disk_free_gb']:.2f} GB")
