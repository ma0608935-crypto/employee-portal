"""
modules/drive_apps_script.py
Google Drive backup using Google Apps Script Web App
"""

import streamlit as st
import os
import base64
import requests
from datetime import datetime


def upload_to_drive_apps_script(file_path, web_app_url, folder_id=None):
    """
    Upload file to Google Drive using Google Apps Script Web App.
    
    Args:
        file_path: Path to the file to upload
        web_app_url: URL of the Google Apps Script Web App
        folder_id: Google Drive folder ID (optional, default: root)
    
    Returns:
        (success, message)
    """
    try:
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Encode to base64
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        # Prepare payload
        payload = {
            'fileName': os.path.basename(file_path),
            'fileContent': file_base64,
            'folderId': folder_id or 'root'
        }
        
        # Send to Apps Script
        response = requests.post(web_app_url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return True, result.get('message', 'Uploaded successfully')
            else:
                return False, result.get('message', 'Unknown error')
        else:
            return False, f"HTTP Error: {response.status_code}"
            
    except Exception as e:
        return False, str(e)


def backup_to_drive_apps_script():
    """Create backup and upload to Google Drive using Apps Script."""
    from modules.backup_utils import create_backup, get_backup_list
    
    # Check configuration
    web_app_url = st.secrets.get("drive_apps_script", {}).get("web_app_url", None)
    if not web_app_url:
        return False, "Google Apps Script URL not configured in secrets.toml"
    
    folder_id = st.secrets.get("drive_apps_script", {}).get("folder_id", None)
    
    # Create backup
    success, msg, link = create_backup(upload_to_drive_flag=False)
    if not success:
        return False, msg
    
    # Get latest backup
    backups = get_backup_list()
    if not backups:
        return False, "No backup found"
    
    latest = backups[0]
    backup_path = latest["path"]
    
    # Upload to Google Drive
    return upload_to_drive_apps_script(backup_path, web_app_url, folder_id)
