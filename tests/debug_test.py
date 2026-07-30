import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import utils
import pandas as pd
import quantstats as qs

print("--- Testing Data Fetching ---")
tickers = ["RELIANCE.NS", "TCS.NS"]
start = "2023-01-01"
end = "2023-12-31"

try:
    data = utils.fetch_data(tickers, start, end)
    print(f"Data Shape: {data.shape}")
    print(f"Columns: {data.columns}")
    print(data.head())
    
    if data.empty:
        print("CRITICAL: Data is empty!")
except Exception as e:
    print(f"CRITICAL ERROR in fetch_data: {e}")

print("\n--- Testing Returns Calculation ---")
try:
    weights = [0.5, 0.5]
    returns = data.pct_change().dropna()
    print("Returns head:")
    print(returns.head())
    
    port_returns = utils.calculate_portfolio_returns(returns, weights)
    print(f"Portfolio Returns Shape: {port_returns.shape}")
    print(port_returns.head())
except Exception as e:
    print(f"CRITICAL ERROR in calculations: {e}")

print("\n--- Testing Optimization ---")
try:
    opt_w, opt_s = utils.optimize_portfolio(returns)
    print(f"Optimized Weights: {opt_w}")
    print(f"Optimized Sharpe: {opt_s}")
except Exception as e:
    print(f"CRITICAL ERROR in optimization: {e}")
