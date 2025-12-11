import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from barupdown.Hr_strategy import backtest_strategy, should_enter_trade, should_exit_trade, get_condition_values
    print("OK: All barupdown functions imported successfully")
except Exception as e:
    print(f"ERROR: Import error: {e}")
    import traceback
    traceback.print_exc()
    
try:
    from common.data_downloader import download_data_fyers
    from common.indicators import heikin_ashi
    from common.utils import to_local
    print("OK: All common utilities imported successfully")
except Exception as e:
    print(f"ERROR: Import error: {e}")
    import traceback
    traceback.print_exc()
