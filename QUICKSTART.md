# Quick Start Guide - Fyers Fighter

## Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create .env File
```bash
cp .env.example .env
# Edit .env if using Supabase
```

### 3. Run the App
```bash
streamlit run app/Home.py
```

Visit: `http://localhost:8501`

---

## Using the Dashboard

### First Time Setup
1. **Register**: Click "Login / Register" tab → "Register" → Fill in details
2. **Login**: Use your credentials to log in
3. **Configure API**: In Account Details → "Update API" → Enter Fyers credentials

### Using Bar Up Down Strategy

#### Paper Trading (Risk-Free)
1. Select "Bar Up Down" from Strategies
2. Click "Live/Paper Trade" tab
3. Configure:
   - Ticker: `NSE:SBIN-EQ` (or your choice)
   - Interval: Choose timeframe
   - Stoploss & Target: Set your risk/reward
   - Quantity: Number of shares
   - Trading Mode: Select "Paper Trade"
4. Click "Start Trading"
5. Monitor the live trading display
6. Trades auto-export to Excel (Desktop)

#### Live Trading
⚠️ **WARNING**: Live trading executes real trades!

Same as Paper Trading but:
- Select "Live Trade" mode
- Trades will execute on actual market
- Have API credentials configured

#### Backtest
1. Click "Backtest" tab
2. Set parameters:
   - Date range: Historical period
   - Strategy parameters
   - Initial capital
3. Click "Run Backtest"
4. View performance metrics and charts

---

## File Locations

### User Data (Local Deployment)
- Users: `app/utils/users.json`
- Trade Logs: Desktop → `BarUpDown_Trades.xlsx`

### On Render/Cloud
- Trades stored locally (ephemeral)
- For persistence, configure Supabase

---

## Common Commands

```bash
# Run locally
streamlit run app/Home.py

# Run with custom port
streamlit run app/Home.py --server.port 8000

# Clear cache
streamlit cache clear

# Deploy to Render (after git push)
# Visit: render.com → Create Web Service
```

---

## Keyboard Shortcuts (Streamlit)

- `r` - Rerun script
- `c` - Clear cache
- `Ctrl+Shift+P` - Settings

---

## Troubleshooting

### App won't start
```bash
pip install --upgrade streamlit
pip install -r requirements.txt --upgrade
```

### Module not found errors
```bash
python -m pip install -r requirements.txt
```

### Clear cached data
```bash
streamlit cache clear
rm -rf ~/.streamlit  # Delete config
```

---

## Next Steps

1. ✅ Complete user registration and Fyers setup
2. ✅ Run a backtest to understand the strategy
3. ✅ Try paper trading first
4. ⚠️ Once confident, attempt live trading
5. 🚀 Deploy to Render for 24/7 access

---

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

---

**Last Updated**: December 2025
