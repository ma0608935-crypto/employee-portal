"""
modules/backup_utils.py
Automatic backup utilities with Google Drive support
"""

import os
import shutil
import sqlite3
import json
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "portal.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def init_backup_dir():
    """Create backup directory if it doesn't exist."""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def get_drive_service():
    """Get Google Drive service using service account from secrets."""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        creds_dict = st.secrets.get("gcp_service_account", {})
        if not creds_dict:
            return None, "No GCP service account in secrets.toml"
        
        creds = Credentials.from_service_account_info(
            dict(creds_dict),
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build('drive', 'v3', credentials=creds)
        return service, None
    except Exception as e:
        return None, str(e)


def upload_to_drive(file_path, folder_id=None):
    """Upload a file to Google Drive."""
    service, error = get_drive_service()
    if error:
        return False, f"Drive error: {error}"
    
    try:
        from googleapiclient.http import MediaFileUpload
        
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id] if folder_id else []
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return True, file.get('webViewLink', '')
    except Exception as e:
        return False, str(e)


def list_drive_files(folder_id=None):
    """List files in Google Drive folder."""
    service, error = get_drive_service()
    if error:
        return []
    
    try:
        query = f"'{folder_id}' in parents" if folder_id else ""
        results = service.files().list(
            q=query,
            pageSize=50,
            fields="files(id, name, size, createdTime, webViewLink)"
        ).execute()
        return results.get('files', [])
    except Exception as e:
        return []


def delete_drive_file(file_id):
    """Delete a file from Google Drive."""
    service, error = get_drive_service()
    if error:
        return False, error
    
    try:
        service.files().delete(fileId=file_id).execute()
        return True, "File deleted successfully"
    except Exception as e:
        return False, str(e)


def create_backup(upload_to_drive_flag=True):
    """Create a backup of the database."""
    init_backup_dir()
    
    if not os.path.exists(DB_PATH):
        return False, "Database file not found."
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"portal_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # Copy the database file
        shutil.copy2(DB_PATH, backup_path)
        
        # Also export as CSV for easy viewing
        export_backup_as_csv(timestamp)
        
        # Upload to Google Drive if enabled
        drive_link = None
        if upload_to_drive_flag:
            folder_id = st.secrets.get("drive", {}).get("backup_folder_id", None)
            success, result = upload_to_drive(backup_path, folder_id)
            if success:
                drive_link = result
        
        # Clean old backups (keep last 30 days)
        clean_old_backups(days_to_keep=30)
        
        return True, f"Backup created: {backup_filename}", drive_link
    except Exception as e:
        return False, f"Backup failed: {str(e)}", None


def export_backup_as_csv(timestamp):
    """Export database tables to CSV files."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    backup_csv_dir = os.path.join(BACKUP_DIR, f"csv_{timestamp}")
    os.makedirs(backup_csv_dir, exist_ok=True)
    
    for table in tables:
        table_name = table[0]
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            df.to_csv(os.path.join(backup_csv_dir, f"{table_name}.csv"), index=False)
        except:
            pass
    
    conn.close()


def clean_old_backups(days_to_keep=30):
    """Delete backups older than specified days."""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Clean .db backups
    for file in os.listdir(BACKUP_DIR):
        if file.endswith(".db") and file.startswith("portal_backup_"):
            try:
                date_str = file.replace("portal_backup_", "").replace(".db", "")
                file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                if file_date < cutoff_date:
                    os.remove(os.path.join(BACKUP_DIR, file))
            except:
                pass
        
        # Clean CSV directories
        if file.startswith("csv_") and os.path.isdir(os.path.join(BACKUP_DIR, file)):
            try:
                date_str = file.replace("csv_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                if file_date < cutoff_date:
                    shutil.rmtree(os.path.join(BACKUP_DIR, file))
            except:
                pass


def get_backup_list():
    """Get list of available backups."""
    init_backup_dir()
    
    backups = []
    for file in os.listdir(BACKUP_DIR):
        if file.endswith(".db") and file.startswith("portal_backup_"):
            file_path = os.path.join(BACKUP_DIR, file)
            size = os.path.getsize(file_path) / 1024  # KB
            backups.append({
                "filename": file,
                "path": file_path,
                "size": f"{size:.1f} KB",
                "created": file.replace("portal_backup_", "").replace(".db", "")
            })
    
    return sorted(backups, key=lambda x: x["created"], reverse=True)


def restore_backup(backup_filename):
    """Restore a backup file."""
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    if not os.path.exists(backup_path):
        return False, "Backup file not found."
    
    # Create backup of current database
    create_backup(upload_to_drive_flag=False)
    
    # Restore
    try:
        shutil.copy2(backup_path, DB_PATH)
        return True, "Database restored successfully!"
    except Exception as e:
        return False, f"Restore failed: {str(e)}"
