# Deployment Guide

## Local Development

### Prerequisites
- Python 3.10+
- pip package manager
- Fyers API credentials

### Setup

1. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
Create a `.env` file in the project root:
```
USE_SUPABASE=false
# If using Supabase:
# SUPABASE_URL=your_supabase_url
# SUPABASE_KEY=your_supabase_anon_key
```

4. **Run the application**
```bash
streamlit run app/Home.py
```

The app will be available at `http://localhost:8501`

---

## Deployment on Render

### Prerequisites
- GitHub repository with this code
- Render account (render.com)

### Steps

1. **Push code to GitHub**
```bash
git add .
git commit -m "Deploy to Render"
git push origin main
```

2. **Create Web Service on Render**
   - Go to render.com and sign in
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository branch (main)

3. **Configure Service**
   - Name: `fyers-fighter` (or your choice)
   - Environment: Python 3.11
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app/Home.py --logger.level=error --client.showErrorDetails=false`

4. **Set Environment Variables**
   - In the Environment tab, add:
     - `USE_SUPABASE`: `false` (or `true` if using Supabase)
     - `STREAMLIT_SERVER_HEADLESS`: `true`
     - `STREAMLIT_SERVER_PORT`: `10000`
     - `ENCRYPTION_MASTER_KEY`: Generate one using `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your app

### Important Notes for Render Deployment

- **Memory Usage**: The free tier has limited memory. For live trading, consider upgrading to a paid plan.
- **Persistent Storage**: Render provides ephemeral storage. Trade logs will be saved locally and not persist between deployments.
- **Timeouts**: Free tier services timeout after 15 minutes of inactivity. For continuous live trading, use paid plans.
- **API Rate Limits**: Be aware of Fyers API rate limits during live trading.

---

## Alternative Platforms

### Heroku (Legacy)
Note: Heroku discontinued free tier in November 2022.

### Railway
Similar setup to Render. Use `railway.app` instead.

### Vercel
Not recommended - designed for serverless functions, not streaming apps.

### DigitalOcean App Platform
Similar to Render. Use the Streamlit Community Cloud option.

---

## File Structure for Deployment

```
fyerfighter/
├── app/
│   ├── Home.py          # Main Streamlit app
│   ├── auth.py          # Authentication module
│   └── utils/
│       └── users.json    # User database (local)
├── barupdown/
│   ├── streamlit_app.py  # Bar Up Down Streamlit UI
│   ├── Hr_strategy.py    # Core strategy logic
│   ├── Hr_live_trade.py  # Live trading
│   ├── Hr_paper_trade.py # Paper trading
│   └── __init__.py
├── common/
│   ├── data_downloader.py
│   ├── indicators.py
│   ├── login.py
│   └── utils.py
├── .streamlit/
│   └── config.toml       # Streamlit configuration
├── .env.example          # Environment variables template
├── requirements.txt      # Project dependencies
├── render.yaml          # Render deployment config
└── DEPLOYMENT.md        # This file
```

---

## Troubleshooting

### Issue: "Fyers client not initialized"
- Make sure you've configured Fyers API credentials in Account Details
- Check your internet connection
- Verify Fyers API status

### Issue: Trades not exporting
- On Render, Desktop path doesn't exist
- Modify export path in code or use Supabase for data persistence

### Issue: Live trading stops abruptly
- Free tier services timeout after inactivity
- Upgrade to paid plan for continuous trading
- Check Fyers API rate limits

### Issue: Import errors
- Ensure all dependencies are in requirements.txt
- Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`
- Reinstall packages: `pip install --upgrade -r requirements.txt`

---

## Performance Tips

1. **Optimize data downloads**: Use smaller time intervals for historical data
2. **Cache data**: Use Streamlit's `@st.cache_data` decorator where possible
3. **Reduce API calls**: Batch API requests when possible
4. **Monitor memory**: Use Streamlit's native widgets instead of heavy visualizations

---

## Security Considerations

1. **Never commit secrets**: Use `.env` files and environment variables
2. **Database security**: If using JSON file backend, ensure proper file permissions
3. **API credentials**: Store encrypted in Supabase or secure backends
4. **HTTPS only**: Always use HTTPS in production
5. **Rate limiting**: Implement rate limiting for public deployments

---

## Continuous Deployment

### GitHub Actions (Optional)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Render
        run: curl https://api.render.com/deploy/srv-${{ secrets.RENDER_SERVICE_ID }}?key=${{ secrets.RENDER_API_KEY }}
```

Set `RENDER_SERVICE_ID` and `RENDER_API_KEY` in GitHub secrets.

---

## Support

For issues:
1. Check Fyers API documentation: https://docs.fyers.in/
2. Review Streamlit documentation: https://docs.streamlit.io/
3. Check Render documentation: https://render.com/docs

---

Last updated: December 2025
