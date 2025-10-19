import requests
import pandas as pd
import numpy as np
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

def calculate_atr(data, period=10):
    """Calculate Average True Range (ATR)."""
    try:
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        logging.info(f"Calculated ATR for period {period}")
        return atr
    except Exception as e:
        logging.error(f"Error calculating ATR: {e}")
        return None

def calculate_supertrend(data, atr_period=10, atr_multiplier=3):
    """
    Calculate Supertrend indicator.
    
    Parameters:
    - data: DataFrame with 'high', 'low', 'close' columns
    - atr_period: Period for ATR calculation (default: 10)
    - atr_multiplier: Multiplier for ATR (default: 3)
    
    Returns:
    - DataFrame with 'supertrend' and 'supertrend_direction' columns
    """
    try:
        df = data.copy()
        
        # Calculate ATR
        atr = calculate_atr(df, period=atr_period)
        
        # Calculate basic upper and lower bands
        hl_avg = (df['high'] + df['low']) / 2
        upper_band = hl_avg + (atr_multiplier * atr)
        lower_band = hl_avg - (atr_multiplier * atr)
        
        # Initialize Supertrend columns
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=float)
        
        # Calculate Supertrend
        for i in range(atr_period, len(df)):
            if i == atr_period:
                # Initial values
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                # Update upper and lower bands
                if lower_band.iloc[i] > lower_band.iloc[i-1] or df['close'].iloc[i-1] < lower_band.iloc[i-1]:
                    final_lower = lower_band.iloc[i]
                else:
                    final_lower = lower_band.iloc[i-1]
                    
                if upper_band.iloc[i] < upper_band.iloc[i-1] or df['close'].iloc[i-1] > upper_band.iloc[i-1]:
                    final_upper = upper_band.iloc[i]
                else:
                    final_upper = upper_band.iloc[i-1]
                
                # Determine Supertrend value and direction
                if direction.iloc[i-1] == -1 and df['close'].iloc[i] <= final_upper:
                    supertrend.iloc[i] = final_upper
                    direction.iloc[i] = -1
                elif direction.iloc[i-1] == -1 and df['close'].iloc[i] > final_upper:
                    supertrend.iloc[i] = final_lower
                    direction.iloc[i] = 1
                elif direction.iloc[i-1] == 1 and df['close'].iloc[i] >= final_lower:
                    supertrend.iloc[i] = final_lower
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = final_upper
                    direction.iloc[i] = -1
        
        logging.info(f"Calculated Supertrend with ATR period={atr_period}, multiplier={atr_multiplier}")
        return supertrend, direction
    except Exception as e:
        logging.error(f"Error calculating Supertrend: {e}")
        return None, None

def generate_signals(data, atr_period=10, atr_multiplier=3, use_slow_supertrend=True):
    """
    Generate BUY/SELL signals based on Supertrend indicator.
    
    Parameters:
    - data: DataFrame with OHLC data
    - atr_period: Period for ATR calculation (default: 10)
    - atr_multiplier: Multiplier for ATR (default: 3)
    - use_slow_supertrend: Whether to use slow Supertrend with multiplier=4 (default: True)
    
    Returns:
    - DataFrame with trading signals
    """
    try:
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0
        
        # Calculate default Supertrend
        supertrend, direction = calculate_supertrend(data, atr_period, atr_multiplier)
        signals['supertrend'] = supertrend
        signals['supertrend_direction'] = direction
        
        # Calculate slow Supertrend if enabled
        if use_slow_supertrend:
            slow_supertrend, slow_direction = calculate_supertrend(data, atr_period, atr_multiplier=4)
            signals['slow_supertrend'] = slow_supertrend
            signals['slow_supertrend_direction'] = slow_direction
            
            # Generate signals based on both Supertrends
            # BUY when both Supertrends are bullish (direction = 1)
            # SELL when both Supertrends are bearish (direction = -1)
            signals['signal'] = np.where(
                (direction == 1) & (slow_direction == 1), 1.0,
                np.where((direction == -1) & (slow_direction == -1), -1.0, 0.0)
            )
        else:
            # Generate signals based on single Supertrend
            # BUY when Supertrend is bullish (direction = 1)
            # SELL when Supertrend is bearish (direction = -1)
            signals['signal'] = np.where(direction == 1, 1.0, np.where(direction == -1, -1.0, 0.0))
        
        # Calculate position changes (crossover points)
        signals['positions'] = signals['signal'].diff()
        
        logging.info(f"Generated trading signals using Supertrend (ATR period={atr_period}, multiplier={atr_multiplier})")
        return signals
    except Exception as e:
        logging.error(f"Error generating signals: {e}")
        return None

def main():
    symbol = 'AAPL'  # Example symbol
    market_data = fetch_market_data(symbol)
    
    if market_data is not None:
        # Configurable Supertrend parameters
        atr_period = 10  # ATR period
        atr_multiplier = 3  # Default ATR multiplier
        use_slow_supertrend = True  # Use slow Supertrend with multiplier=4
        
        signals = generate_signals(market_data, atr_period, atr_multiplier, use_slow_supertrend)
        
        if signals is not None:
            print("Trading Signals based on Supertrend Indicator:")
            print(signals)
            
            # Display BUY/SELL signals
            buy_signals = signals[signals['positions'] > 0]
            sell_signals = signals[signals['positions'] < 0]
            
            print("\nBUY Signals:")
            print(buy_signals[['signal', 'supertrend', 'supertrend_direction']])
            print("\nSELL Signals:")
            print(sell_signals[['signal', 'supertrend', 'supertrend_direction']])

if __name__ == "__main__":
    main()