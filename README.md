# Fyers Trading Strategies

A Streamlit-based web application for running multiple trading strategies on Fyers platform.

## Features

- Multiple trading strategies:
  - Bar Up Down Strategy
  - EMA TSI Strategy
  - Instant Buy Strategy
- Real-time market data
- Paper trading and live trading modes
- User authentication and management
- Interactive charts and analysis

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fyerfighter.git
cd fyerfighter
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with your Fyers credentials:
```
FYERS_CLIENT_ID=your_client_id
FYERS_SECRET_KEY=your_secret_key
FYERS_REDIRECT_URI=your_redirect_uri
```

5. Run the application:
```bash
streamlit run app/Home.py
```

## Deployment

The application is configured for deployment on Render. Follow these steps:

1. Fork this repository
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app/Home.py --logger.level=error --client.showErrorDetails=false`
   - Add environment variables from your `.env` file

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 