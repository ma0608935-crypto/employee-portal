"""
modules/drive_backup.py
Google Drive backup using Google Apps Script
"""

import streamlit as st
import os
import base64
import requests
import json
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "portal.db")


def get_apps_script_url():
    """Get Apps Script URL from secrets."""
    try:
        return st.secrets.get("drive_apps_script", {}).get("web_app_url", None)
    except:
        return None


def backup_to_google_drive(folder_id=None):
    """
    Backup database to Google Drive using Apps Script.
    """
    apps_script_url = get_apps_script_url()
    if not apps_script_url:
        return False, "❌ Google Apps Script not configured"
    
    if not os.path.exists(DB_PATH):
        return False, "❌ Database file not found"
    
    try:
        # Read database file
        with open(DB_PATH, "rb") as f:
            file_data = f.read()
        
        # Encode to base64
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        # Prepare payload
        payload = {
            'action': 'backup_database',
            'data': {
                'fileName': f'portal_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db',
                'fileContent': file_base64,
                'folderId': folder_id or 'root'
            }
        }
        
        # Send to Apps Script
        response = requests.post(apps_script_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return True, result.get('message', '✅ Backup saved to Google Drive')
            else:
                return False, result.get('message', '❌ Backup failed')
        else:
            return False, f"❌ HTTP Error: {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def restore_from_google_drive(folder_id=None, filename=None):
    """
    Restore database from Google Drive using Apps Script.
    """
    apps_script_url = get_apps_script_url()
    if not apps_script_url:
        return False, "❌ Google Apps Script not configured"
    
    try:
        # Prepare payload
        payload = {
            'action': 'restore_database',
            'data': {
                'fileName': filename or 'portal_backup.db',
                'folderId': folder_id or 'root'
            }
        }
        
        # Send to Apps Script
        response = requests.post(apps_script_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                # Decode file content
                file_content = base64.b64decode(result.get('data', ''))
                
                # Save to local
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                with open(DB_PATH, "wb") as f:
                    f.write(file_content)
                
                return True, result.get('message', '✅ Database restored')
            else:
                return False, result.get('message', '❌ Restore failed')
        else:
            return False, f"❌ HTTP Error: {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def list_backup_files(folder_id=None):
    """
    List backup files in Google Drive.
    """
    # This would need a separate Apps Script endpoint
    # For simplicity, we'll return a placeholder
    return [
        {"name": "portal_backup_20240812_143022.db", "size": "245 KB", "date": "2024-08-12 14:30"},
        {"name": "portal_backup_20240811_090000.db", "size": "238 KB", "date": "2024-08-11 09:00"},
    ]
