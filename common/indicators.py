# indicators.py
import pandas as pd
import numpy as np

def heikin_ashi(df):
    """
    Convert standard OHLC candles into Heikin-Ashi candles.
    Returns a DataFrame with columns: HA_Open, HA_High, HA_Low, HA_Close.
    """
    df = df.copy()
    # Ensure numeric conversion
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].apply(pd.to_numeric, errors='coerce')
    
    ha = pd.DataFrame(index=df.index, columns=['HA_Open', 'HA_High', 'HA_Low', 'HA_Close'])
    ha['HA_Close'] = ((df['open'] + df['high'] + df['low'] + df['close']) / 4).astype(float)
    
    # For the first candle, extract scalar values using .item() to avoid deprecation warnings
    ha.iloc[0, ha.columns.get_loc('HA_Open')] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2

    for i in range(1, len(df)):
        ha.iloc[i, ha.columns.get_loc('HA_Open')] = (ha['HA_Open'].iloc[i-1] + ha['HA_Close'].iloc[i-1]) / 2

    ha['HA_High'] = pd.concat([
        df['high'].astype(float),
        ha['HA_Open'].astype(float),
        ha['HA_Close'].astype(float)
    ], axis=1).apply(lambda row: max(row), axis=1)
    
    ha['HA_Low'] = pd.concat([
        df['low'].astype(float),
        ha['HA_Open'].astype(float),
        ha['HA_Close'].astype(float)
    ], axis=1).apply(lambda row: min(row), axis=1)
    return ha

def ema(series, period=5):
    """
    Calculate Exponential Moving Average (EMA) for a given series.
    
    Parameters:
    -----------
    series : pandas.Series
        The data series to calculate EMA on.
    period : int, default=5
        The period for EMA calculation.
        
    Returns:
    --------
    pandas.Series
        Series containing the EMA values.
    """
    # Ensure numeric conversion
    series = pd.to_numeric(series, errors='coerce')
    
    # Calculate EMA using pandas ewm function
    ema_values = series.ewm(span=period, adjust=False).mean()
    
    return ema_values

def ema_lows(df, period=5):
    """
    Calculate Exponential Moving Average (EMA) of Heikin-Ashi lows.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing OHLC data to be converted to Heikin-Ashi.
        Or a DataFrame that already contains Heikin-Ashi data with 'HA_Low' column.
    period : int, default=5
        The period for EMA calculation.
        
    Returns:
    --------
    pandas.Series
        Series containing the EMA of Heikin-Ashi lows.
    """
    # Check if we need to convert to Heikin-Ashi first
    if 'HA_Low' not in df.columns:
        # Convert to Heikin-Ashi
        ha_df = heikin_ashi(df)
    else:
        # Already Heikin-Ashi data
        ha_df = df.copy()
    
    # Ensure numeric conversion
    ha_df['HA_Low'] = pd.to_numeric(ha_df['HA_Low'], errors='coerce')
    
    # Calculate EMA on Heikin-Ashi lows
    return ema(ha_df['HA_Low'], period)

def ema_highs(df, period=5):
    """
    Calculate Exponential Moving Average (EMA) of Heikin-Ashi highs.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing OHLC data to be converted to Heikin-Ashi.
        Or a DataFrame that already contains Heikin-Ashi data with 'HA_High' column.
    period : int, default=5
        The period for EMA calculation.
        
    Returns:
    --------
    pandas.Series
        Series containing the EMA of Heikin-Ashi highs.
    """
    # Check if we need to convert to Heikin-Ashi first
    if 'HA_High' not in df.columns:
        # Convert to Heikin-Ashi
        ha_df = heikin_ashi(df)
    else:
        # Already Heikin-Ashi data
        ha_df = df.copy()
    
    # Ensure numeric conversion
    ha_df['HA_High'] = pd.to_numeric(ha_df['HA_High'], errors='coerce')
    
    # Calculate EMA on Heikin-Ashi highs
    return ema(ha_df['HA_High'], period)

# ----------------------------
# TSI Calculation
# ----------------------------
def calculate_tsi(series, r=30, s=13, signal_period=13):
    """
    Calculate the True Strength Index (TSI) and its signal line.
    """
    diff = series.diff()
    abs_diff = diff.abs()
    ema1 = diff.ewm(span=r, adjust=False).mean()
    ema2 = ema1.ewm(span=s, adjust=False).mean()
    abs_ema1 = abs_diff.ewm(span=r, adjust=False).mean()
    abs_ema2 = abs_ema1.ewm(span=s, adjust=False).mean()
    tsi = 100 * (ema2 / abs_ema2)
    tsi_signal = tsi.ewm(span=signal_period, adjust=False).mean()
    return tsi, tsi_signal

if __name__ == '__main__':
    import pandas as pd
    # For testing purposes with dummy data:
    data = {
        "open": [100, 105, 102, 104, 103, 105, 107],
        "high": [110, 107, 108, 109, 106, 110, 112],
        "low": [95, 102, 101, 100, 101, 103, 105],
        "close": [108, 103, 107, 105, 104, 108, 110]
    }
    df = pd.DataFrame(data)
    
    # Test Heikin-Ashi
    ha = heikin_ashi(df)
    print("Heikin-Ashi Candles:")
    print(ha)
    
    # Test EMA of Heikin-Ashi lows and highs
    # Method 1: Pass original OHLC data (will be converted to HA internally)
    ema_low1 = ema_lows(df, period=5)
    ema_high1 = ema_highs(df, period=5)
    
    # Method 2: Pass already converted Heikin-Ashi data
    ema_low2 = ema_lows(ha, period=5)
    ema_high2 = ema_highs(ha, period=5)
    
    print("\nEMA of Heikin-Ashi Lows (period=5):")
    print(ema_low1)
    
    print("\nEMA of Heikin-Ashi Highs (period=5):")
    print(ema_high1)
    
    # Verify both methods produce the same result
    print("\nBoth methods produce the same results:")
    print(f"Lows: {ema_low1.equals(ema_low2)}")
    print(f"Highs: {ema_high1.equals(ema_high2)}")
