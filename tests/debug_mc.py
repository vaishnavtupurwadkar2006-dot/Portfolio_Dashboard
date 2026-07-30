import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import utils
import pandas as pd
import numpy as np
import time

# Mock returns data
dates = pd.date_range("2023-01-01", periods=252)
returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)

print("Starting Monte Carlo Simulation Benchmark...")
start_time = time.time()

try:
    sim_df = utils.run_monte_carlo(returns, num_simulations=1000, days=252)
    end_time = time.time()
    
    print(f"Simulation completed in {end_time - start_time:.4f} seconds")
    print(f"Shape: {sim_df.shape}")
    print(sim_df.head())
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
