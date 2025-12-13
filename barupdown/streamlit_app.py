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
from common.indicators import heikin_ashi
from common.utils import to_local, get_download_path, export_to_excel
from barupdown.Hr_strategy import backtest_strategy, should_enter_trade, should_exit_trade, get_condition_values

def initialize_trading_state():
    if 'barupdown_position' not in st.session_state:
        st.session_state.barupdown_position = 0
    if 'barupdown_entry_price' not in st.session_state:
        st.session_state.barupdown_entry_price = None
    if 'barupdown_entry_time' not in st.session_state:
        st.session_state.barupdown_entry_time = None
    if 'barupdown_qty' not in st.session_state:
        st.session_state.barupdown_qty = 0
    if 'barupdown_trade_log' not in st.session_state:
        st.session_state.barupdown_trade_log = []
    if 'barupdown_running' not in st.session_state:
        st.session_state.barupdown_running = False

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

def show_barupdown():
    st.subheader("Bar Up Down Strategy")
    
    if not st.session_state.authenticated_user or not st.session_state.fyers_client:
        st.warning("Please log in and configure your Fyers API credentials to use this strategy.")
        return
    
    initialize_trading_state()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Strategy Configuration")
        symbol = st.text_input("Ticker Symbol", value="NSE:SBIN-EQ", key="bu_symbol")
        interval = st.selectbox("Interval", ["1m", "2m", "3m", "5m", "15m", "30m", "1h", "1d"], key="bu_interval")
        stoploss = st.number_input("Stoploss (%)", min_value=0.1, value=5.0, key="bu_stoploss")
        target = st.number_input("Target (%)", min_value=0.1, value=10.0, key="bu_target")
        qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="bu_qty")
        trading_mode = st.radio("Trading Mode", ["Paper Trade", "Live Trade"], key="bu_mode")
    
    with col2:
        st.markdown("### Current Status")
        status_placeholder = st.empty()
        price_placeholder = st.empty()
        entry_placeholder = st.empty()
        pnl_placeholder = st.empty()
        
        conditions_placeholder = st.empty()
    
    if st.session_state.barupdown_running:
        st.session_state.barupdown_running = True
        
        if st.button("Stop Trading", key="bu_stop"):
            st.session_state.barupdown_running = False
            if st.session_state.barupdown_position == 1:
                price = get_latest_price(st.session_state.fyers_client, symbol.upper())
                if price:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    pnl = (price - st.session_state.barupdown_entry_price) * st.session_state.barupdown_qty
                    st.session_state.barupdown_trade_log.append([dt, "SELL", price, st.session_state.barupdown_qty, round(pnl, 2)])
                    st.session_state.barupdown_position = 0
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
        
        while st.session_state.barupdown_running and update_count < max_updates:
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
                
                if st.session_state.barupdown_position == 0:
                    if should_enter_trade(st.session_state.fyers_client, symbol.upper(), price, interval):
                        st.session_state.barupdown_entry_price = price
                        st.session_state.barupdown_entry_time = now
                        st.session_state.barupdown_qty = qty
                        st.session_state.barupdown_position = 1
                        st.session_state.barupdown_trade_log.append([dt, "BUY", price, qty, 0.0])
                        status_placeholder.success(f"BUY executed at ₹{price:.2f}")
                        entry_placeholder.metric("Entry Price", f"₹{st.session_state.barupdown_entry_price:.2f}", delta=f"@ {st.session_state.barupdown_entry_time}")
                    else:
                        status_placeholder.info("Waiting for entry signal...")
                else:
                    if should_exit_trade(st.session_state.fyers_client, symbol.upper(), st.session_state.barupdown_entry_price, stoploss, target, price, interval):
                        pnl = (price - st.session_state.barupdown_entry_price) * qty
                        st.session_state.barupdown_trade_log.append([dt, "SELL", price, qty, round(pnl, 2)])
                        pnl_placeholder.metric("P&L", f"₹{pnl:.2f}", delta=f"{((pnl / (st.session_state.barupdown_entry_price * qty)) * 100):.2f}%")
                        status_placeholder.success(f"SELL executed at ₹{price:.2f} | P&L: ₹{pnl:.2f}")
                        st.session_state.barupdown_position = 0
                        st.session_state.barupdown_entry_price = None
                        st.session_state.barupdown_entry_time = None
                        st.session_state.barupdown_running = False
                        st.info("Exit triggered. Trading stopped.")
                        break
                    else:
                        entry_placeholder.metric("Entry Price", f"₹{st.session_state.barupdown_entry_price:.2f}", delta=f"@ {st.session_state.barupdown_entry_time}")
                        if st.session_state.barupdown_position == 1:
                            current_pnl = (price - st.session_state.barupdown_entry_price) * qty
                            pnl_placeholder.metric("Current P&L", f"₹{current_pnl:.2f}", delta=f"{((current_pnl / (st.session_state.barupdown_entry_price * qty)) * 100):.2f}%")
                
                conditions = get_condition_values(st.session_state.fyers_client, symbol.upper(), price, interval, stoploss, target)
                with conditions_placeholder.container():
                    st.markdown("#### Condition Values")
                    cond_col1, cond_col2 = st.columns(2)
                    with cond_col1:
                        st.write(f"Prev Open: ₹{conditions['prev_open']:.2f}")
                        st.write(f"Prev Close: ₹{conditions['prev_close']:.2f}")
                        st.write(f"Prev Low: ₹{conditions['prev_low']:.2f}")
                    with cond_col2:
                        st.write(f"SL Price: ₹{conditions['stoploss_price']:.2f}")
                        st.write(f"Target Price: ₹{conditions['target_price']:.2f}")
                
                time.sleep(1)
                update_count += 1
                progress_bar.progress(min(update_count / max_updates, 0.99))
            
            except Exception as e:
                status_placeholder.error(f"Error: {e}")
                break
        
        progress_bar.empty()
    else:
        if st.button("Start Trading", key="bu_start"):
            st.session_state.barupdown_running = True
            st.rerun()
        
        # Add a section to view and download the trade log
        if st.session_state.barupdown_trade_log:
            st.markdown("### Session Trade Log")
            log_df = pd.DataFrame(
                st.session_state.barupdown_trade_log,
                columns=["Timestamp", "Signal", "Price", "Quantity", "PnL"]
            )
            st.dataframe(log_df)





def show_backtest():
    st.subheader("Bar Up Down Backtest")
    
    if not st.session_state.fyers_client:
        st.warning("Please configure your Fyers API credentials to run backtest.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        symbol = st.text_input("Ticker Symbol", value="NSE:SBIN-EQ", key="bu_bt_symbol")
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=365), key="bu_bt_start")
        end_date = st.date_input("End Date", value=datetime.now(), key="bu_bt_end")
        interval = st.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], key="bu_bt_interval")
    
    with col2:
        stoploss = st.number_input("Stoploss (%)", min_value=0.1, value=2.0, key="bu_bt_stoploss")
        target = st.number_input("Target (%)", min_value=0.1, value=5.0, key="bu_bt_target")
        initial_capital = st.number_input("Initial Capital", min_value=1000, value=10000, step=1000, key="bu_bt_capital")
    
    if st.button("Run Backtest"):
        with st.spinner("Running backtest..."):
            result = backtest_strategy(
                symbol.upper(),
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                st.session_state.fyers_client,
                stoploss=stoploss,
                target=target,
                initial_capital=initial_capital,
                interval=interval
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
                
                # Create figure with secondary y-axis
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Add Equity Curve (Price)
                fig.add_trace(
                    go.Scatter(x=ha_data.index, y=ha_data['HA_Close'], name="Price (HA Close)", line=dict(color='black')),
                    secondary_y=False,
                )

                # Add Account Value Curve
                fig.add_trace(
                    go.Scatter(x=account_df.index, y=account_df['AccountValue'], name="Account Value", line=dict(color='blue', dash='dash')),
                    secondary_y=True,
                )

                # Add Buy Signals
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

                # Add Sell Signals
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

                # Set titles
                fig.update_layout(
                    title_text="Backtest Results",
                    xaxis_title="Date",
                )

                # Set y-axes titles
                fig.update_yaxes(title_text="Price", secondary_y=False)
                fig.update_yaxes(title_text="Account Value", secondary_y=True)

                st.plotly_chart(fig, width='stretch')
            else:
                st.error("Backtest failed. Please check your inputs and Fyers connection.")
