# data_downloader.py
from datetime import timedelta
import pandas as pd
from common.config import DEFAULT_INTERVAL
from common.utils import to_local

def map_resolution(gui_resolution):
    mapping = {
        "1wk": "W",
        "1d": "D",
        "1h": "60",
        "15m": "15",
        "5m": "5",
        "3m": "3",
        "2m": "2",
        "1m": "1",
    }
    return mapping.get(gui_resolution, gui_resolution)

def download_data_fyers(symbol, start_date, end_date, period_days=60, gui_resolution='1d', fyers=None):
    """
    Downloads historical data from Fyers API in chunks.
    Returns a DataFrame with columns: ['open', 'high', 'low', 'close', 'volume'] and a datetime index.
    """
    resolution = map_resolution(gui_resolution)
    
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # If end date is a weekend or holiday, look back for the most recent trading day
    max_lookback = 5  # Maximum days to look back
    lookback_count = 0
    while lookback_count < max_lookback:
        # Check if current end date is a weekend
        if end_dt.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            end_dt = end_dt - timedelta(days=1)
            lookback_count += 1
            continue
            
        # Try to get data for this date
        test_data = {
            "symbol": symbol,
            "resolution": str(resolution),
            "date_format": "1",
            "range_from": end_dt.strftime("%Y-%m-%d"),
            "range_to": end_dt.strftime("%Y-%m-%d"),
            "cont_flag": "0"
        }
        test_response = fyers.history(data=test_data)
        
        # If we got data, this is a trading day
        if test_response.get("candles"):
            break
            
        # If no data, this might be a holiday, look back one more day
        end_dt = end_dt - timedelta(days=1)
        lookback_count += 1
    
    all_data = []
    current_start = start_dt

    while current_start < end_dt:
        current_end = min(current_start + timedelta(days=period_days), end_dt)
        rfrom = current_start.strftime("%Y-%m-%d")
        rto = current_end.strftime("%Y-%m-%d")
        print(f"Downloading data from {rfrom} to {rto}")

        cdata = {
            "symbol": symbol,
            "resolution": str(resolution),
            "date_format": "1",
            "range_from": rfrom,
            "range_to": rto,
            "cont_flag": "0"
        }
        response = fyers.history(data=cdata)
        print("Fyers response:", response)
        if response.get("candles"):
            data_chunk = pd.DataFrame.from_dict(response['candles'])
            cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            data_chunk.columns = cols
            data_chunk['datetime'] = pd.to_datetime(data_chunk['datetime'], unit='s')
            # Timezone conversion as needed
            data_chunk['datetime'] = data_chunk['datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            data_chunk = data_chunk.set_index('datetime')
            all_data.append(data_chunk)
        else:
            print("No candle data available for this period or error occurred:", response)
        current_start = current_end

    if all_data:
        final_df = pd.concat(all_data)
        final_df = final_df[~final_df.index.duplicated(keep='first')]
        return final_df
    else:
        return pd.DataFrame()

if __name__ == '__main__':
    # For testing purposes only: requires a Fyers client instance.
    from login import initialize_fyers_client
    fyers = initialize_fyers_client()
    df = download_data_fyers("NSE:SBIN-EQ", "2022-01-01", "2022-06-01", gui_resolution="1d", fyers=fyers)
    print(df.head())
