"""
modules/drive_apps_script.py
Google Sheets backup using Google Apps Script Web App
"""

import streamlit as st
import os
import base64
import requests
from datetime import datetime


def append_to_google_sheet_apps_script(row_data: dict, web_app_url: str):
    """
    Append a row to Google Sheets using Google Apps Script Web App.
    
    Args:
        row_data: Dictionary with column names and values
        web_app_url: URL of the Google Apps Script Web App
    
    Returns:
        (success, message)
    """
    try:
        # Prepare payload
        payload = {
            'action': 'append',
            'data': row_data
        }
        
        # Send to Apps Script
        response = requests.post(web_app_url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return True, result.get('message', 'Added successfully')
            else:
                return False, result.get('message', 'Unknown error')
        else:
            return False, f"HTTP Error: {response.status_code}"
            
    except Exception as e:
        return False, str(e)


def backup_to_drive_apps_script():
    """Create backup and upload to Google Drive using Apps Script."""
    try:
        from modules.backup_utils import create_backup, get_backup_list
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from backup_utils import create_backup, get_backup_list
    
    # Check configuration
    try:
        web_app_url = st.secrets.get("drive_apps_script", {}).get("web_app_url", None)
    except:
        web_app_url = None
    
    if not web_app_url:
        return False, "Google Apps Script URL not configured in secrets.toml"
    
    folder_id = None
    try:
        folder_id = st.secrets.get("drive_apps_script", {}).get("folder_id", None)
    except:
        pass
    
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