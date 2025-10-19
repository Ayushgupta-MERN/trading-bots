import requests
import pandas as pd
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, filename='trading_signals.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_market_data(symbol, interval='1d'):
    """Fetch real-time market data from Fyers API."""
    try:
        url = f"https://api.fyers.in/api/v2/data/{symbol}?interval={interval}"
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
        logging.info(f"Fetched data for {symbol}: {data}")
        return pd.DataFrame(data['data'])
    except Exception as e:
        logging.error(f"Error fetching market data: {e}")
        return None

def calculate_sma(data, period):
    """Calculate Simple Moving Average."""
    try:
        sma = data['close'].rolling(window=period).mean()
        logging.info(f"Calculated SMA for period {period}")
        return sma
    except Exception as e:
        logging.error(f"Error calculating SMA: {e}")
        return None

def generate_signals(data, short_window, long_window):
    """Generate BUY/SELL signals based on SMA crossover."""
    try:
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0
        
        signals['short_sma'] = calculate_sma(data, short_window)
        signals['long_sma'] = calculate_sma(data, long_window)
        
        signals['signal'][short_window:] = np.where(signals['short_sma'][short_window:] > signals['long_sma'][short_window:], 1.0, 0.0)  
        signals['positions'] = signals['signal'].diff()

        logging.info("Generated trading signals.")
        return signals
    except Exception as e:
        logging.error(f"Error generating signals: {e}")
        return None

def main():
    symbol = 'AAPL'  # Example symbol
    market_data = fetch_market_data(symbol)
    
    if market_data is not None:
        short_window = 20
        long_window = 50
        
        signals = generate_signals(market_data, short_window, long_window)
        print(signals)

if __name__ == "__main__":
    main()