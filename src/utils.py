import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

@st.cache_data
def fetch_data(tickers, start_date, end_date):
    try:
        data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            auto_adjust=True,
            progress=False
        )

        if data.empty:
            return pd.DataFrame()

        # Extract Close prices
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"]
        else:
            prices = data[["Close"]]
            prices.columns = tickers if len(tickers) == 1 else prices.columns

        # Remove empty columns and rows
        prices = prices.dropna(axis=1, how="all")
        prices = prices.dropna(how="all")

        return prices

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

@st.cache_data
def get_fundamentals(tickers):
    """Fetches fundamental data for tickers."""
    fundamentals = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            fundamentals.append({
                "Ticker": ticker,
                "Market Cap": info.get("marketCap", "N/A"),
                "P/E Ratio": info.get("trailingPE", "N/A"),
                "Forward P/E": info.get("forwardPE", "N/A"),
                "Dividend Yield": info.get("dividendYield", "N/A"),
                "Sector": info.get("sector", "N/A"),
                "Beta": info.get("beta", "N/A")
            })
        except Exception:
            continue
    return pd.DataFrame(fundamentals)

def calculate_portfolio_returns(returns, weights):
    if returns.empty:
        return pd.Series(dtype=float)

    if len(weights) != returns.shape[1]:
        raise ValueError(
            f"{len(weights)} weights supplied for {returns.shape[1]} assets."
        )

    weights = np.asarray(weights)

    return pd.Series(
        returns.to_numpy() @ weights,
        index=returns.index,
        name="Portfolio"
    )

def run_monte_carlo(returns, num_simulations=1000, days=252):
    """Runs a Monte Carlo simulation for portfolio projection (Vectorized)."""
    mean_daily_return = returns.mean()
    volatility = returns.std()
    
    # Generate all random returns at once: (days, num_simulations)
    daily_returns = np.random.normal(mean_daily_return, volatility, (days, num_simulations))
    
    # Calculate price paths using cumulative product
    # Start with 1.0
    price_paths = np.vstack([np.ones((1, num_simulations)), 1 + daily_returns])
    price_paths = np.cumprod(price_paths, axis=0)
    
    # Create DataFrame
    simulation_df = pd.DataFrame(price_paths, columns=[f"Sim {x}" for x in range(num_simulations)])
        
    return simulation_df

def optimize_portfolio(returns, risk_free_rate=0.0):
    """
    Optimizes portfolio weights for Maximum Sharpe Ratio using Scipy.
    Returns: (optimal_weights, optimized_sharpe)
    """
    from scipy.optimize import minimize
    
    n_assets = returns.shape[1]
    
    # Initial Guess: Equal weights
    init_guess = np.repeat(1/n_assets, n_assets)
    
    # Constraints: Sum of weights = 1
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    
    # Bounds: 0 <= weight <= 1
    bounds = tuple((0.0, 1.0) for _ in range(n_assets))
    
    def neg_sharpe(weights):
        # Calculate annualized return and volatility
        portfolio_return = np.sum(returns.mean() * weights) * 252
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        
        sharpe = (portfolio_return - risk_free_rate) / portfolio_volatility
        return -sharpe
    
    result = minimize(neg_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
    
    return result.x, -result.fun

def generate_insights(portfolio_returns, benchmark_returns=None):
    import quantstats as qs

    portfolio_returns = portfolio_returns.dropna()

    if portfolio_returns.empty:
        return ["⚠️ No portfolio return data available."]

    insights = []

    sharpe = qs.stats.sharpe(portfolio_returns)
    cagr = qs.stats.cagr(portfolio_returns)
    volatility = qs.stats.volatility(portfolio_returns)

    
    
    # Sharpe Insights
    if sharpe > 1.2:
        insights.append("✅ **Excellent Risk-Adjusted Returns**: Your Sharpe Ratio is high (>1.2), indicating great efficiency.")
    elif sharpe < 0.5:
        insights.append("⚠️ **Low Efficiency**: Your Sharpe Ratio is below 0.5. Consider diversifying to reduce risk.")
        
    # Volatility Insights
    if volatility > 0.30:
        insights.append("⚡ **High Volatility**: Your portfolio is fluctuating significantly. Ensure this aligns with your risk tolerance.")
    elif volatility < 0.15:
        insights.append("🛡️ **Stable Portfolio**: Low volatility indicates a conservative allocation.")
        
    # Benchmark Comparison
    if benchmark_returns is not None and not benchmark_returns.empty:
        excess_return = cagr - qs.stats.cagr(benchmark_returns)
        if excess_return > 0:
            insights.append(f"🏆 **Beating the Market**: You are outperforming the benchmark by {excess_return*100:.2f}%.")
        else:
            insights.append(f"📉 **Underperforming**: You are trailing the benchmark by {abs(excess_return)*100:.2f}%.")
            
    return insights

@st.cache_data
def fetch_market_data(tickers, period="6mo"):
    """Fetches batch data for scanner."""
    try:
        data = yf.download(tickers, period=period, group_by='ticker')
        return data
    except Exception as e:
        st.error(f"Scanner Data Error: {e}")
        return pd.DataFrame()

def calculate_technical_signals(ticker, df):
    """Calculates technical indicators and signals for a single stock."""
    # Ensure we have data
    if df.empty: return None
    
    # Extract Close series (handle multi-index if needed)
    try:
        close = df['Close']
        if isinstance(close, pd.DataFrame): 
             close = close.iloc[:, 0] # Handle case where ticker is column name
    except:
        return None
        
    # Calculate Indicators
    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # SMAs
    sma_50 = close.rolling(window=50).mean()
    sma_200 = close.rolling(window=200).mean()
    
    # Volume (if available)
    try:
        volume = df['Volume']
        if isinstance(volume, pd.DataFrame): volume = volume.iloc[:, 0]
        vol_avg = volume.rolling(window=10).mean()
    except:
        volume = pd.Series(0, index=close.index)
        vol_avg = pd.Series(0, index=close.index)

    # Get latest values
    latest_close = close.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    latest_sma50 = sma_50.iloc[-1]
    latest_sma200 = sma_200.iloc[-1]
    
    # Signals
    signal = "NEUTRAL"
    rationale = []
    
    # RSI Signals
    if latest_rsi < 30:
        signal = "BUY"
        rationale.append("Oversold (RSI < 30)")
    elif latest_rsi > 70:
        signal = "SELL"
        rationale.append("Overbought (RSI > 70)")
        
    # Trend Signals
    if latest_close > latest_sma200:
        rationale.append("Uptrend (Above SMA200)")
        if latest_sma50 > latest_sma200 and sma_50.iloc[-2] <= sma_200.iloc[-2]:
             signal = "STRONG BUY"
             rationale.append("Golden Cross (50 > 200)")
    else:
        rationale.append("Downtrend (Below SMA200)")
        if latest_sma50 < latest_sma200 and sma_50.iloc[-2] >= sma_200.iloc[-2]:
             signal = "STRONG SELL"
             rationale.append("Death Cross (50 < 200)")

    return {
        "Ticker": ticker,
        "Price": round(latest_close, 2),
        "RSI": round(latest_rsi, 2),
        "SMA_50": round(latest_sma50, 2),
        "SMA_200": round(latest_sma200, 2),
        "Signal": signal,
        "Rationale": ", ".join(rationale)
    }

def scan_market(tickers):
    """Scans list of tickers and returns analysis dataframe."""
    data = fetch_market_data(tickers)
    results = []
    
    for ticker in tickers:
        try:
            # yfinance returns multi-index col (Ticker, PriceType)
            ticker_df = data[ticker]
            analysis = calculate_technical_signals(ticker, ticker_df)
            if analysis:
                results.append(analysis)
        except Exception:
            continue
            
    return pd.DataFrame(results)

@st.cache_data
def fetch_market_data(tickers, period="6mo"):
    """Fetches batch data for scanner."""
    try:
        data = yf.download(tickers, period=period, group_by='ticker')
        return data
    except Exception as e:
        st.error(f"Scanner Data Error: {e}")
        return pd.DataFrame()

def calculate_technical_signals(ticker, df):
    """Calculates technical indicators and signals for a single stock."""
    # Ensure we have data
    if df.empty: return None
    
    # Extract Close series (handle multi-index if needed)
    try:
        close = df['Close']
        if isinstance(close, pd.DataFrame): 
             close = close.iloc[:, 0] # Handle case where ticker is column name
    except:
        return None
        
    # Calculate Indicators
    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # SMAs
    sma_50 = close.rolling(window=50).mean()
    sma_200 = close.rolling(window=200).mean()
    
    # Volume (if available)
    try:
        volume = df['Volume']
        if isinstance(volume, pd.DataFrame): volume = volume.iloc[:, 0]
        vol_avg = volume.rolling(window=10).mean()
    except:
        volume = pd.Series(0, index=close.index)
        vol_avg = pd.Series(0, index=close.index)

    # Get latest values
    latest_close = close.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    latest_sma50 = sma_50.iloc[-1]
    latest_sma200 = sma_200.iloc[-1]
    
    # Signals
    signal = "NEUTRAL"
    rationale = []
    
    # RSI Signals
    if latest_rsi < 30:
        signal = "BUY"
        rationale.append("Oversold (RSI < 30)")
    elif latest_rsi > 70:
        signal = "SELL"
        rationale.append("Overbought (RSI > 70)")
        
    # Trend Signals
    if latest_close > latest_sma200:
        rationale.append("Uptrend (Above SMA200)")
        if latest_sma50 > latest_sma200 and sma_50.iloc[-2] <= sma_200.iloc[-2]:
             signal = "STRONG BUY"
             rationale.append("Golden Cross (50 > 200)")
    else:
        rationale.append("Downtrend (Below SMA200)")
        if latest_sma50 < latest_sma200 and sma_50.iloc[-2] >= sma_200.iloc[-2]:
             signal = "STRONG SELL"
             rationale.append("Death Cross (50 < 200)")

    return {
        "Ticker": ticker,
        "Price": round(latest_close, 2),
        "RSI": round(latest_rsi, 2),
        "SMA_50": round(latest_sma50, 2),
        "SMA_200": round(latest_sma200, 2),
        "Signal": signal,
        "Rationale": ", ".join(rationale)
    }

def scan_market(tickers):
    """Scans list of tickers and returns analysis dataframe."""
    data = fetch_market_data(tickers)
    results = []
    
    for ticker in tickers:
        try:
            # yfinance returns multi-index col (Ticker, PriceType)
            ticker_df = data[ticker]
            analysis = calculate_technical_signals(ticker, ticker_df)
            if analysis:
                results.append(analysis)
        except Exception:
            continue
            
    return pd.DataFrame(results)
