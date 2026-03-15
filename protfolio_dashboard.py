#portfolio Dashboard 
import streamlit as st, yfinance as yf, pandas as pd, quantstats as qs, plotly.express as px
import tempfile, os

st.set_page_config(page_title="Portfolio Analytics Dashboard", layout="wide")
st.title("📊 Portfolio Analytics Dashboard using QuantStats")

st.sidebar.header("Portfolio Configuration")

nse_tickers = [ "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
               "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "BAJFINANCE.NS", "AXISBANK.NS",
               "LT.NS", "MARUTI.NS", "ITC.NS", "ASIANPAINT.NS", "HCLTECH.NS"]
tickers = st.sidebar.multiselect("Select NSE Stock ", options=nse_tickers, default=["RELIANCE.NS",    "TCS.NS", "HDFCBANK.NS"])

weights = []

if tickers:
    st.sidebar.markdown("### Assign Portfolio Weights")
    for t in tickers:
        w = st.sidebar.slider(f"Weight for {t}", min_value=0.0, max_value=1.0, value=round(1.0/len(tickers), 2), step=0.01)
        weights.append(w)
    total = sum(weights)    
    if total != 1 and total != 0:
        weights = [w/total for w in weights]


start_date, end_date = st.sidebar.date_input(
    "Select Date Range:", 
    value=(pd.to_datetime("2020-01-01"), pd.to_datetime("today")))

generate_btn = st.sidebar.button("Generate Portfolio Analysis")

#  Main Logic
if generate_btn:
    if not tickers:
        st.error("Please select at least one stock ticker.")
        st.stop()
    if len(tickers) != len(weights):
        st.error("Number of tickers and weights must match.")
        st.stop()
    
    with st.spinner("Fetching data and computing analytics..."):
        price_data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True)["Close"]
        price_data = price_data.dropna()

        returns = price_data.pct_change().dropna()

        portfolio_returns = (returns * weights).sum(axis=1)
        portfolio_returns = portfolio_returns.dropna()

        if portfolio_returns.empty:
            st.error("No valid portfolio returns data. Please adjust your selection.")
            st.stop()

        #Display Metrics
        st.subheader("Portfolio Performance Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Sharpe Ratio", f"{qs.stats.sharpe(portfolio_returns):.2f}")
        col2.metric("Max Drawdown", f"{qs.stats.max_drawdown(portfolio_returns)*100:.2f}%")
        col3.metric("CAGR", f"{qs.stats.cagr(portfolio_returns)*100:.2f}%")
        col4.metric("Volatility", f"{qs.stats.volatility(portfolio_returns)*100:.2f}%")

        st.subheader("Portfolio Weights")
        fig_pie = px.pie(
            names=tickers, 
            values=weights,
            title="Portfolio Allocation")
        st.plotly_chart(fig_pie, use_container_width=True)

        # Monthly Returns
        st.subheader("Monthly Returns Heatmap")
        monthly_returns = qs.stats.monthly_returns(portfolio_returns)
        st.dataframe(
         monthly_returns.style.format("{:.2%}")
        )
      
        # Cumulative Returns
        st.subheader("Cumulative Returns")
        st.line_chart((1 + portfolio_returns).cumprod())

        # End of the year return chart
        st.subheader("End-of-Year (EOY) Returns")
        eoy_returns = portfolio_returns.resample('Y').apply(lambda x: (1 + x).prod() - 1)
        st.bar_chart(eoy_returns)


        # Generate HTML Report
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = os.path.join(tmpdir, "portfolio_report.html")
            qs.reports.html(portfolio_returns, output=report_path, title="Portfolio Performance Report")
            with open(report_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            st.download_button(
                label="Download Full Quantstats Report",
                data=html_content,
                file_name="portfolio_report.html",
                mime="text/html")
            
            
    st.success("Analysis Complete! Explore your portfolio metrics above.")
