# strategy.py
from datetime import timedelta
import pandas as pd
import numpy as np
from common.data_downloader import download_data_fyers
from common.indicators import heikin_ashi, ema_lows, ema_highs, calculate_tsi
from common.utils import to_local

def backtest_strategy(ticker, start_date, end_date, fyers, stoploss=5, target=10, initial_capital=10000, interval='1d', ema_period=5, tsi_r_period=30):
    # Download intraday and daily data
    data = download_data_fyers(ticker, start_date, end_date, period_days=60, gui_resolution=interval, fyers=fyers)
    if data.empty:
        print("No data found for", ticker)
        return None, None, None, None, None, None

    daily_data = download_data_fyers(ticker, start_date, end_date, period_days=30, gui_resolution="1d", fyers=fyers)
    
    ha_data = heikin_ashi(data)
    D_Data = heikin_ashi(daily_data)
    
    # Calculate EMA of Heikin-Ashi lows and highs with period=5
    ha_data['EMA_Lows'] = ema_lows(ha_data, period=ema_period)
    ha_data['EMA_Highs'] = ema_highs(ha_data, period=ema_period)
    
    # Calculate TSI and TSI signal
    ha_data['TSI'], ha_data['TSI_Signal'] = calculate_tsi(ha_data['HA_Close'], r=tsi_r_period, s=13, signal_period=13)
    
    print("Daily HA data head:")
    print(D_Data.head())
    print(ha_data.tail())

    # Prepare signals and positions
    ha_data['Signal'] = 0
    ha_data['Position'] = 0

    capital = float(initial_capital)
    position = 0
    shares = 0.0
    entry_price = None
    trades = []
    account_value_history = []

    for i in range(1, len(ha_data)):
        row = ha_data.iloc[i]
        price = float(row['HA_Close'])
        date = ha_data.index[i]
        local_date = to_local(date)

        prev_candle = ha_data.iloc[i - 1]
        prev_open = float(prev_candle["HA_Open"])
        prev_close = float(prev_candle["HA_Close"])
        prev_low = float(prev_candle["HA_Low"])
        prev_ema_low = float(prev_candle["EMA_Lows"])
        prev_ema_high = float(prev_candle["EMA_Highs"])

        # Retrieve previous day's HA Open from daily data
        # yesterday_date = date.date() - timedelta(days=1)
        # daily_row = D_Data[D_Data.index.date == yesterday_date]
        # if not daily_row.empty:
        #     yest_ha_open = float(daily_row["HA_Open"].iloc[0])
        # else:
        #     yest_ha_open = None

        # Retrieve the last available daily HA_Open before today
        prev_daily = D_Data.loc[:date - pd.Timedelta(days=1)]
        if not prev_daily.empty:
            yest_ha_open = float(prev_daily['HA_Open'].iloc[-1])
        else:
            yest_ha_open = None

        # Entry Condition (example: current price > previous candle open and candle was bearish)
        if position == 0:
            # Skip the yest_ha_open check if it's None
            tsi_value = float(row['TSI'])
            tsi_signal_value = float(row['TSI_Signal'])
            tsi_diff = tsi_value - tsi_signal_value
            
            #if (price > prev_open) and (prev_open > prev_close) and 
            if (prev_low <= prev_ema_low) and (tsi_diff > 0):
                entry_price = price
                quantity = capital/price  # Example fixed quantity; change this to accept user-qty from gui_trade.py 
                trade_cost = quantity * price
                capital = 0  # fully invested
                shares = quantity
                position = 1
                ha_data.at[date, 'Signal'] = 1
                trades.append((local_date, local_date.strftime("%H:%M"), "BUY", price, quantity, trade_cost))
        else:
            exit_condition = False
            # Get TSI values for current candle
            tsi_value = float(row['TSI'])
            tsi_signal_value = float(row['TSI_Signal'])
            tsi_diff = tsi_value - tsi_signal_value
            
            # if price < prev_low:
            #     exit_condition = True
            if price >= entry_price * (1 + target / 100):
                exit_condition = True
            elif price <= entry_price * (1 - stoploss / 100):
                exit_condition = True
            elif price >= prev_ema_high:
                exit_condition = True
            # New exit condition: if (tsi - tsi_signal) < 0
            elif tsi_diff < 0:
                exit_condition = True

            if exit_condition:
                trade_value = shares * price
                capital = trade_value
                quantity = shares
                shares = 0.0
                position = 0
                ha_data.at[date, 'Signal'] = -1
                trades.append((local_date, local_date.strftime("%H:%M"), "SELL", price, quantity, trade_value))
                
        ha_data.at[date, 'Position'] = position
        current_value = shares * price if position == 1 else capital
        account_value_history.append((date, current_value))

    # Close any open position at the end
    if position == 1:
        last_date = ha_data.index[-1]
        local_last_date = to_local(last_date)
        last_price = float(ha_data['HA_Close'].iloc[-1])
        trade_value = shares * last_price
        capital += trade_value
        trades.append((local_last_date, local_last_date.strftime("%H:%M"), "SELL", last_price, shares, trade_value))
        ha_data.at[last_date, 'Signal'] = -1
        ha_data.at[last_date, 'Position'] = 0
        account_value_history.append((last_date, capital))
        position = 0

    total_return = (capital - initial_capital) / initial_capital * 100
    print(f"Initial Capital: ${initial_capital:.2f}")
    print(f"Final Capital: ${capital:.2f}")
    print(f"Total Return: {total_return:.2f}%")

    first_price = float(ha_data['HA_Close'].iloc[0])
    last_price = float(ha_data['HA_Close'].iloc[-1])
    buy_hold_return = (last_price / first_price - 1) * 100
    print(f"Buy and Hold Return: {buy_hold_return:.2f}%")

    account_df = pd.DataFrame(account_value_history, columns=['Date', 'AccountValue'])
    account_df.set_index('Date', inplace=True)
    running_max = account_df['AccountValue'].cummax()
    drawdown = (account_df['AccountValue'] - running_max) / running_max
    max_drawdown = drawdown.min() * 100
    print(f"Maximum Drawdown: {max_drawdown:.2f}%")

    # Compute trade return metrics
    trade_returns = []
    open_buy_price = None
    for trade in trades:
        if trade[2] == "BUY":
            open_buy_price = trade[3]
        elif trade[2] == "SELL" and open_buy_price is not None:
            ret = (trade[3] / open_buy_price - 1) * 100
            trade_returns.append(ret)
            open_buy_price = None

    num_trades = len(trade_returns)
    winning_trades = sum(1 for r in trade_returns if r > 0)
    losing_trades = sum(1 for r in trade_returns if r <= 0)
    win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0
    avg_trade_return = np.mean(trade_returns) if trade_returns else 0

    trade_history_df = pd.DataFrame(trades, columns=['Date', 'Hour', 'Signal', 'Price', 'Quantity', 'Value'])
    trade_history_df['Date'] = pd.to_datetime(trade_history_df['Date']).dt.strftime("%d-%b-%Y")
    trade_history_df['Price'] = trade_history_df['Price'].round(2)
    trade_history_df['Quantity'] = trade_history_df['Quantity'].round(4)
    trade_history_df['Value'] = trade_history_df['Value'].round(2)
    print("\nTrade History:")
    print(trade_history_df.to_string(index=False))

    # Return data, trade history, performance summaries, and the account DataFrame
    perf_summary = {
        "Initial Capital": initial_capital,
        "Final Capital": capital,
        "Total Return": total_return,
        "Buy & Hold Return": buy_hold_return
    }
    perf_metrics = {
        "Maximum Drawdown": max_drawdown,
        "No. of Trades": num_trades,
        "Winning Trades": winning_trades,
        "Losing Trades": losing_trades,
        "Win Rate": win_rate,
        "Avg. Trade Return": avg_trade_return
    }
    return ha_data, trades, perf_summary, perf_metrics, trade_history_df, account_df


def should_enter_trade(fyers, ticker, live_price, interval="1m", ema_period=5, tsi_r_period=30):
    from datetime import datetime, timedelta
    # Download recent historical data to compute previous candle's HA values.
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    df = download_data_fyers(ticker, start_date, end_date, period_days=7, gui_resolution=interval, fyers=fyers)
    if df is None or len(df) < 2:
        return False
    ha_df = heikin_ashi(df)
    if len(ha_df) < 2:
        return False
    
    # Calculate EMA of Heikin-Ashi lows
    ha_df['EMA_Lows'] = ema_lows(ha_df, period=ema_period)
    
    # Calculate TSI and TSI signal
    ha_df['TSI'], ha_df['TSI_Signal'] = calculate_tsi(ha_df['HA_Close'], r=tsi_r_period, s=13, signal_period=13)
    
    # Use the previous candle from the HA calculations.
    prev_candle = ha_df.iloc[-2]
    prev_open = prev_candle['HA_Open']
    prev_close = prev_candle['HA_Close']
    prev_low = prev_candle['HA_Low']
    prev_ema_low = prev_candle['EMA_Lows']
    
    # Get current TSI values
    curr_candle = ha_df.iloc[-1]
    tsi_value = curr_candle['TSI']
    tsi_signal_value = curr_candle['TSI_Signal']
    tsi_diff = tsi_value - tsi_signal_value
    
    # Use the passed-in live_price instead of curr_candle['HA_Close']
    # Added new conditions: prev_low <= prev_ema_low and (tsi - tsi_signal) > 0
    if (prev_open > prev_close) and (live_price > prev_open) and (prev_low <= prev_ema_low) and (tsi_diff > 0):
        return True
    return False

def should_exit_trade(fyers, ticker, entry_price, stoploss, target, live_price, interval="1m", ema_period=5, tsi_r_period=30):
    from datetime import datetime, timedelta
    # Download recent historical data to compute previous candle's HA values.
    start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    df = download_data_fyers(ticker, start_date, end_date, period_days=2, gui_resolution=interval, fyers=fyers)
    if df is None or len(df) < 2:
        return False
    ha_df = heikin_ashi(df)
    if len(ha_df) < 2:
        return False
    
    # Calculate EMA of Heikin-Ashi highs
    ha_df['EMA_Highs'] = ema_highs(ha_df, period=ema_period)
    
    # Calculate TSI and TSI signal
    ha_df['TSI'], ha_df['TSI_Signal'] = calculate_tsi(ha_df['HA_Close'], r=tsi_r_period, s=13, signal_period=13)
    
    prev_candle = ha_df.iloc[-2]
    prev_low = prev_candle['HA_Low']
    prev_ema_high = prev_candle['EMA_Highs']
    
    # Get current TSI values
    curr_candle = ha_df.iloc[-1]
    tsi_value = curr_candle['TSI']
    tsi_signal_value = curr_candle['TSI_Signal']
    tsi_diff = tsi_value - tsi_signal_value
    
    # Use the live_price for checks.
    if live_price < prev_low:
        return True

    target_price = entry_price * (1 + target / 100)
    if live_price >= target_price:
        return True
    
    stop_price = entry_price * (1 - stoploss / 100)
    if live_price <= stop_price:
        return True
    
    # New exit condition: if price >= previous ema_highs
    if live_price >= prev_ema_high:
        return True
    
    # New exit condition: if (tsi - tsi_signal) < 0
    if tsi_diff < 0:
        return True
    
    return False

if __name__ == '__main__':
    # For testing your strategy; requires a Fyers client.
    from common.login import initialize_fyers_client
    fyers = initialize_fyers_client()
    result = backtest_strategy("NSE:SBIN-EQ", "2022-01-01", "2022-06-01", fyers, interval="15m")
    if result:
        ha_data, trades, perf_summary, perf_metrics, trade_history_df, account_df = result
