# utils.py
import os
import json
import pandas as pd
from tkinter import messagebox

def to_local(dt):
    # Ensure dt is timezone-aware if needed
    if dt.tzinfo is None:
        dt = dt.tz_localize('UTC')
    return dt.tz_convert("Asia/Kolkata")

def export_to_excel(trade_history_df):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    file_path = os.path.join(desktop, "Trade_Details.xlsx")
    trade_history_df.to_excel(file_path, index=False)
    print(f"Trade details exported to {file_path}")
    messagebox.showinfo("Success", f"Trade details exported to {file_path}")
    