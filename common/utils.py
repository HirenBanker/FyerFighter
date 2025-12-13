# utils.py
import os
import json
import pandas as pd
import io

def get_download_path():
    """Returns the default downloads path for linux or windows"""
    if os.name == 'nt':
        return os.path.join(os.path.expanduser('~'), 'Downloads')
    else:
        return os.path.join(os.path.expanduser('~'), 'downloads')

def to_local(dt):
    # Ensure dt is timezone-aware if needed
    if dt.tzinfo is None:
        dt = dt.tz_localize('UTC')
    return dt.tz_convert("Asia/Kolkata")

def export_to_excel(trade_history_df):
    """
    Returns a BytesIO object containing the Excel file.
    This is designed to be used with st.download_button.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        trade_history_df.to_excel(writer, index=False)
    output.seek(0)
    return output
    