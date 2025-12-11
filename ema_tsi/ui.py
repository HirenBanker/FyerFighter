import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from common.data_downloader import download_data_fyers
from common.indicators import heikin_ashi, ema_lows, ema_highs, calculate_tsi
from common.utils import to_local
from ema_tsi.strategy import backtest_strategy, should_enter_trade, should_exit_trade

def initialize_trading_state():
    if 'ema_tsi_position' not in st.session_state:
        st.session_state.ema_tsi_position = 0
    if 'ema_tsi_entry_price' not in st.session_state:
        st.session_state.ema_tsi_entry_price = None
    if 'ema_tsi_entry_time' not in st.session_state:
        st.session_state.ema_tsi_entry_time = None
    if 'ema_tsi_trade_log' not in st.session_state:
        st.session_state.ema_tsi_trade_log = []
    if 'ema_tsi_running' not in st.session_state:
        st.session_state.ema_tsi_running = False

def get_latest_price(fyers, ticker):
    try:
        response = fyers.quotes({"symbols": ticker})
        if (response and "d" in response and len(response["d"]) > 0 and 
            "v" in response["d"][0] and "lp" in response["d"][0]["v"]):
            price = float(response["d"][0]["v"]["lp"])
            if price > 0:
                return price
        return None
    except Exception as e:
        return None

def export_trades(ticker, trade_log):
    if not trade_log:
        return False
    
    try:
        df_new = pd.DataFrame(
            trade_log,
            columns=["Timestamp", "Signal", "Price", "Quantity", "PnL"]
        )
        
        df_new['Date'] = pd.to_datetime(df_new['Timestamp']).dt.date
        df_new['Time'] = pd.to_datetime(df_new['Timestamp']).dt.time
        df_new = df_new.drop('Timestamp', axis=1)
        df_new = df_new[['Date', 'Time', 'Signal', 'Price', 'Quantity', 'PnL']]
        df_new['Ticker'] = ticker
        
        file_path = os.path.join(
            os.path.expanduser("~"),
            "Desktop",
            "EMA_TSI_Trades.xlsx"
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if os.path.exists(file_path):
            df_existing = pd.read_excel(file_path, parse_dates=['Date'])
            df_existing['Date'] = pd.to_datetime(df_existing['Date']).dt.date
            df_to_save = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_to_save = df_new
        
        with pd.ExcelWriter(file_path, engine='openpyxl', datetime_format='YYYY-MM-DD') as writer:
            df_to_save.to_excel(writer, index=False)
        
        st.session_state.ema_tsi_trade_log = []
        return True
    except Exception as e:
        st.error(f"Error exporting trades: {e}")
        return False

def get_condition_values(fyers, ticker, live_price, interval, ema_period=5, tsi_r_period=30):
    """Get all condition values for display in GUI"""
    try:
        start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        df = download_data_fyers(ticker, start_date, end_date, period_days=2, gui_resolution=interval, fyers=fyers)
        if df is None or len(df) < 2:
            return {
                'prev_open': 0,
                'prev_close': 0,
                'prev_low': 0,
                'prev_ema_low': 0,
                'prev_ema_high': 0,
                'tsi_value': 0,
                'tsi_signal': 0
            }
        
        ha_df = heikin_ashi(df)
        if len(ha_df) < 2:
            return {
                'prev_open': 0,
                'prev_close': 0,
                'prev_low': 0,
                'prev_ema_low': 0,
                'prev_ema_high': 0,
                'tsi_value': 0,
                'tsi_signal': 0
            }
        
        ha_df['EMA_Lows'] = ema_lows(ha_df, period=ema_period)
        ha_df['EMA_Highs'] = ema_highs(ha_df, period=ema_period)
        ha_df['TSI'], ha_df['TSI_Signal'] = calculate_tsi(ha_df['HA_Close'], r=tsi_r_period, s=13, signal_period=13)
        
        prev_candle = ha_df.iloc[-2]
        prev_open = float(prev_candle['HA_Open'])
        prev_close = float(prev_candle['HA_Close'])
        prev_low = float(prev_candle['HA_Low'])
        prev_ema_low = float(prev_candle['EMA_Lows'])
        prev_ema_high = float(prev_candle['EMA_Highs'])
        
        curr_candle = ha_df.iloc[-1]
        tsi_value = float(curr_candle['TSI'])
        tsi_signal = float(curr_candle['TSI_Signal'])
        
        return {
            'prev_open': prev_open,
            'prev_close': prev_close,
            'prev_low': prev_low,
            'prev_ema_low': prev_ema_low,
            'prev_ema_high': prev_ema_high,
            'tsi_value': tsi_value,
            'tsi_signal': tsi_signal
        }
    except Exception as e:
        return {
            'prev_open': 0,
            'prev_close': 0,
            'prev_low': 0,
            'prev_ema_low': 0,
            'prev_ema_high': 0,
            'tsi_value': 0,
            'tsi_signal': 0
        }

def show_trade():
    st.subheader("EMA TSI Strategy - Live Trading")
    
    if not st.session_state.authenticated_user or not st.session_state.fyers_client:
        st.warning("Please log in and configure your Fyers API credentials to use this strategy.")
        return
    
    initialize_trading_state()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Strategy Configuration")
        symbol = st.text_input("Ticker Symbol", value="NSE:SBIN-EQ", key="ema_tsi_symbol")
        interval = st.selectbox("Interval", ["1m", "2m", "3m", "5m", "15m", "30m", "1h", "1d"], key="ema_tsi_interval")
        ema_period = st.number_input("EMA Period", min_value=1, value=5, step=1, key="ema_tsi_ema_period")
        tsi_r_period = st.number_input("TSI R Period", min_value=1, value=30, step=1, key="ema_tsi_tsi_r_period")
        stoploss = st.number_input("Stoploss (%)", min_value=0.1, value=5.0, key="ema_tsi_stoploss")
        target = st.number_input("Target (%)", min_value=0.1, value=10.0, key="ema_tsi_target")
        qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="ema_tsi_qty")
        trading_mode = st.radio("Trading Mode", ["Paper Trade", "Live Trade"], key="ema_tsi_mode")
    
    with col2:
        st.markdown("### Current Status")
        status_placeholder = st.empty()
        price_placeholder = st.empty()
        entry_placeholder = st.empty()
        pnl_placeholder = st.empty()
        
        conditions_placeholder = st.empty()
    
    if st.session_state.ema_tsi_running:
        st.session_state.ema_tsi_running = True
        
        if st.button("Stop Trading", key="ema_tsi_stop"):
            st.session_state.ema_tsi_running = False
            if st.session_state.ema_tsi_position == 1:
                price = get_latest_price(st.session_state.fyers_client, symbol.upper())
                if price:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    pnl = (price - st.session_state.ema_tsi_entry_price) * st.session_state.ema_tsi_qty
                    st.session_state.ema_tsi_trade_log.append([dt, "SELL", price, st.session_state.ema_tsi_qty, round(pnl, 2)])
                    st.session_state.ema_tsi_position = 0
            export_trades(symbol.upper(), st.session_state.ema_tsi_trade_log)
            st.rerun()
        
        trading_status = "Running"
        if trading_mode == "Live Trade":
            trading_status += " (LIVE)"
        else:
            trading_status += " (PAPER)"
        
        status_placeholder.info(f"Status: {trading_status}")
        
        progress_bar = st.progress(0)
        update_count = 0
        max_updates = 60
        
        while st.session_state.ema_tsi_running and update_count < max_updates:
            try:
                price = get_latest_price(st.session_state.fyers_client, symbol.upper())
                
                if price is None:
                    status_placeholder.warning("Waiting for valid market data...")
                    time.sleep(1)
                    update_count += 1
                    progress_bar.progress(min(update_count / max_updates, 0.99))
                    continue
                
                now = datetime.now().strftime("%H:%M:%S")
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                price_placeholder.metric("Current Price", f"₹{price:.2f}")
                
                if st.session_state.ema_tsi_position == 0:
                    if should_enter_trade(st.session_state.fyers_client, symbol.upper(), price, interval, ema_period, tsi_r_period):
                        st.session_state.ema_tsi_entry_price = price
                        st.session_state.ema_tsi_entry_time = now
                        st.session_state.ema_tsi_qty = qty
                        st.session_state.ema_tsi_position = 1
                        st.session_state.ema_tsi_trade_log.append([dt, "BUY", price, qty, 0.0])
                        export_trades(symbol.upper(), st.session_state.ema_tsi_trade_log)
                        status_placeholder.success(f"BUY executed at ₹{price:.2f}")
                        entry_placeholder.metric("Entry Price", f"₹{st.session_state.ema_tsi_entry_price:.2f}", delta=f"@ {st.session_state.ema_tsi_entry_time}")
                    else:
                        status_placeholder.info("Waiting for entry signal...")
                else:
                    if should_exit_trade(st.session_state.fyers_client, symbol.upper(), st.session_state.ema_tsi_entry_price, stoploss, target, price, interval, ema_period, tsi_r_period):
                        pnl = (price - st.session_state.ema_tsi_entry_price) * qty
                        st.session_state.ema_tsi_trade_log.append([dt, "SELL", price, qty, round(pnl, 2)])
                        export_trades(symbol.upper(), st.session_state.ema_tsi_trade_log)
                        pnl_placeholder.metric("P&L", f"₹{pnl:.2f}", delta=f"{((pnl / (st.session_state.ema_tsi_entry_price * qty)) * 100):.2f}%")
                        status_placeholder.success(f"SELL executed at ₹{price:.2f} | P&L: ₹{pnl:.2f}")
                        st.session_state.ema_tsi_position = 0
                        st.session_state.ema_tsi_entry_price = None
                        st.session_state.ema_tsi_entry_time = None
                        st.session_state.ema_tsi_running = False
                        st.info("Exit triggered. Trading stopped.")
                        break
                    else:
                        entry_placeholder.metric("Entry Price", f"₹{st.session_state.ema_tsi_entry_price:.2f}", delta=f"@ {st.session_state.ema_tsi_entry_time}")
                        if st.session_state.ema_tsi_position == 1:
                            current_pnl = (price - st.session_state.ema_tsi_entry_price) * qty
                            pnl_placeholder.metric("Current P&L", f"₹{current_pnl:.2f}", delta=f"{((current_pnl / (st.session_state.ema_tsi_entry_price * qty)) * 100):.2f}%")
                
                conditions = get_condition_values(st.session_state.fyers_client, symbol.upper(), price, interval, ema_period, tsi_r_period)
                with conditions_placeholder.container():
                    st.markdown("#### Condition Values")
                    cond_col1, cond_col2, cond_col3 = st.columns(3)
                    with cond_col1:
                        st.write(f"Prev Open: ₹{conditions['prev_open']:.2f}")
                        st.write(f"Prev Close: ₹{conditions['prev_close']:.2f}")
                        st.write(f"Prev Low: ₹{conditions['prev_low']:.2f}")
                    with cond_col2:
                        st.write(f"EMA Low: ₹{conditions['prev_ema_low']:.2f}")
                        st.write(f"EMA High: ₹{conditions['prev_ema_high']:.2f}")
                    with cond_col3:
                        st.write(f"TSI: {conditions['tsi_value']:.4f}")
                        st.write(f"TSI Signal: {conditions['tsi_signal']:.4f}")
                
                time.sleep(1)
                update_count += 1
                progress_bar.progress(min(update_count / max_updates, 0.99))
            
            except Exception as e:
                status_placeholder.error(f"Error: {e}")
                break
        
        progress_bar.empty()
    else:
        if st.button("Start Trading", key="ema_tsi_start"):
            st.session_state.ema_tsi_running = True
            st.rerun()

def show_backtest():
    st.subheader("EMA TSI Backtest")
    
    if not st.session_state.fyers_client:
        st.warning("Please configure your Fyers API credentials to run backtest.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        symbol = st.text_input("Ticker Symbol", value="NSE:SBIN-EQ", key="ema_tsi_bt_symbol")
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=365), key="ema_tsi_bt_start")
        end_date = st.date_input("End Date", value=datetime.now(), key="ema_tsi_bt_end")
        interval = st.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], key="ema_tsi_bt_interval")
    
    with col2:
        ema_period = st.number_input("EMA Period", min_value=1, value=5, step=1, key="ema_tsi_bt_ema_period")
        tsi_r_period = st.number_input("TSI R Period", min_value=1, value=30, step=1, key="ema_tsi_bt_tsi_r_period")
        stoploss = st.number_input("Stoploss (%)", min_value=0.1, value=5.0, key="ema_tsi_bt_stoploss")
        target = st.number_input("Target (%)", min_value=0.1, value=10.0, key="ema_tsi_bt_target")
        initial_capital = st.number_input("Initial Capital", min_value=1000, value=10000, step=1000, key="ema_tsi_bt_capital")
    
    if st.button("Run Backtest", key="ema_tsi_run_backtest"):
        with st.spinner("Running backtest..."):
            result = backtest_strategy(
                symbol.upper(),
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                st.session_state.fyers_client,
                stoploss=stoploss,
                target=target,
                initial_capital=initial_capital,
                interval=interval,
                ema_period=ema_period,
                tsi_r_period=tsi_r_period
            )
            
            if result and result[0] is not None:
                ha_data, trades, perf_summary, perf_metrics, trade_history_df, account_df = result
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Performance Summary")
                    st.metric("Initial Capital", f"₹{perf_summary['Initial Capital']:.2f}")
                    st.metric("Final Capital", f"₹{perf_summary['Final Capital']:.2f}")
                    st.metric("Total Return", f"{perf_summary['Total Return']:.2f}%")
                    st.metric("Buy & Hold Return", f"{perf_summary['Buy & Hold Return']:.2f}%")
                
                with col2:
                    st.markdown("### Performance Metrics")
                    st.metric("Maximum Drawdown", f"{perf_metrics['Maximum Drawdown']:.2f}%")
                    st.metric("Number of Trades", int(perf_metrics['No. of Trades']))
                    st.metric("Winning Trades", int(perf_metrics['Winning Trades']))
                    st.metric("Win Rate", f"{perf_metrics['Win Rate']:.2f}%")
                
                st.markdown("### Trade History")
                st.dataframe(trade_history_df, width='stretch')
                
                st.markdown("### Backtest Chart")
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                fig.add_trace(
                    go.Scatter(x=ha_data.index, y=ha_data['HA_Close'], name="Price (HA Close)", line=dict(color='black')),
                    secondary_y=False,
                )

                fig.add_trace(
                    go.Scatter(x=account_df.index, y=account_df['AccountValue'], name="Account Value", line=dict(color='blue', dash='dash')),
                    secondary_y=True,
                )

                buy_signals = ha_data[ha_data['Signal'] == 1]
                fig.add_trace(
                    go.Scatter(
                        x=buy_signals.index, 
                        y=buy_signals['HA_Close'], 
                        name='Buy Signal', 
                        mode='markers', 
                        marker=dict(symbol='triangle-up', color='green', size=10)
                    ),
                    secondary_y=False,
                )

                sell_signals = ha_data[ha_data['Signal'] == -1]
                fig.add_trace(
                    go.Scatter(
                        x=sell_signals.index, 
                        y=sell_signals['HA_Close'], 
                        name='Sell Signal', 
                        mode='markers', 
                        marker=dict(symbol='triangle-down', color='red', size=10)
                    ),
                    secondary_y=False,
                )

                fig.update_layout(
                    title_text="Backtest Results",
                    xaxis_title="Date",
                )

                fig.update_yaxes(title_text="Price", secondary_y=False)
                fig.update_yaxes(title_text="Account Value", secondary_y=True)

                st.plotly_chart(fig, width='stretch')
            else:
                st.error("Backtest failed. Please check your inputs and Fyers connection.")
