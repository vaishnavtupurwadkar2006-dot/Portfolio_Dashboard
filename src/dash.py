import streamlit as st
import pandas as pd
import quantstats as qs
import utils
import charts
import tempfile
import os
import plotly.express as px

# --- Configuration ---
st.set_page_config(page_title="Pro Portfolio Analytics", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
        text-align: center;
    }
    div[data-testid="stMetricValue"] {
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False
if "portfolio_data" not in st.session_state:
    st.session_state.portfolio_data = pd.DataFrame()
if "benchmark_data" not in st.session_state:
    st.session_state.benchmark_data = pd.DataFrame()

# --- Sidebar ---
st.sidebar.header("🔧 Configuration")

nse_tickers = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "BAJFINANCE.NS", "AXISBANK.NS",
    "LT.NS", "MARUTI.NS", "ITC.NS", "ASIANPAINT.NS", "HCLTECH.NS"
]

selected_tickers = st.sidebar.multiselect("Select Assets", options=nse_tickers, default=["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"])
benchmark_ticker = st.sidebar.selectbox("Benchmark", options=["^NSEI", "^BSESN", "SPY"], index=0)

start_date, end_date = st.sidebar.date_input("Date Range", value=(pd.to_datetime("2020-01-01"), pd.to_datetime("today")))

# Weights
weights = []
if selected_tickers:
    st.sidebar.markdown("### ⚖️ Portfolio Weights")
    for t in selected_tickers:
        w = st.sidebar.slider(f"Weight: {t}", 0.0, 1.0, round(1.0/len(selected_tickers), 2), 0.05)
        weights.append(w)
    
    total_weight = sum(weights)
    if total_weight > 0:
        weights = [w / total_weight for w in weights] # Normalize
    else:
        # Fallback if sum is 0
        weights = [1.0/len(weights) for _ in weights]

if st.sidebar.button("🚀 Analyze Portfolio"):
    st.session_state.analyzed = True
    with st.spinner("Crunching numbers..."):
        # Fetch Data and store in session state
        st.session_state.portfolio_data = utils.fetch_data(selected_tickers, start_date, end_date)
        st.session_state.benchmark_data = utils.fetch_data([benchmark_ticker], start_date, end_date)

# --- Dashboard Output ---
if st.session_state.analyzed:
    portfolio_data = st.session_state.portfolio_data
    benchmark_data = st.session_state.benchmark_data
    
    if portfolio_data.empty:
        st.error("No data found. Please check tickers/dates.")
    else:
        # Returns
        returns = portfolio_data.pct_change().dropna()
        portfolio_returns = utils.calculate_portfolio_returns(returns, weights)
        benchmark_returns = benchmark_data.pct_change().dropna().iloc[:, 0] if not benchmark_data.empty else pd.Series()
        
        # Align dates
        if not benchmark_returns.empty:
            common_index = portfolio_returns.index.intersection(benchmark_returns.index)
            portfolio_returns = portfolio_returns.loc[common_index]
            benchmark_returns = benchmark_returns.loc[common_index]
        
        # --- Dashboard Layout ---
        st.title("📊 Pro Portfolio Analytics")
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Overview", "🔍 Deep Dive", "🧠 AI Advisor", "📡 Market Scanner", "📊 Fundamentals", "🎲 Monte Carlo"])
        
        with tab1:
            st.subheader("Performance Summary")
            
            # Smart Insights (Top of Dashboard)
            with st.expander("💡 AI Insights", expanded=True):
                insights = utils.generate_insights(portfolio_returns, benchmark_returns)
                if not insights:
                    st.write("Insufficient data for insights.")
                for i in insights:
                    st.write(i)
            
            # Metrics
            sharpe = qs.stats.sharpe(portfolio_returns)
            cagr = qs.stats.cagr(portfolio_returns)
            try: return_volatility = qs.stats.volatility(portfolio_returns)
            except: return_volatility = 0
            max_dd = qs.stats.max_drawdown(portfolio_returns)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Sharpe Ratio", f"{sharpe:.2f}")
            col2.metric("CAGR", f"{cagr:.2%}")
            col3.metric("Volatility", f"{return_volatility:.2%}")
            col4.metric("Max Drawdown", f"{max_dd:.2%}", delta_color="inverse")
            
            # Cumulative Return Chart
            st.subheader("Portfolio Growth")
            cum_returns = (1 + portfolio_returns).cumprod()
            cum_benchmark = (1 + benchmark_returns).cumprod() if not benchmark_returns.empty else None
            
            fig = charts.plot_interactive_chart(cum_returns, "Portfolio Growth (vs Benchmark)")
            if cum_benchmark is not None:
                import plotly.graph_objects as go
                fig.add_trace(go.Scatter(x=cum_benchmark.index, y=cum_benchmark, mode='lines', name='Benchmark', line=dict(dash='dash')))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Statistical Analysis")
            
            col_dd, col_corr = st.columns(2)
            
            with col_dd:
                st.markdown("#### Drawdowns")
                drawdown = qs.stats.to_drawdown_series(portfolio_returns)
                st.plotly_chart(charts.plot_drawdown(drawdown), use_container_width=True)
                
            with col_corr:
                st.markdown("#### Correlation Matrix")
                st.plotly_chart(charts.plot_correlation_matrix(returns), use_container_width=True)
                
            st.markdown("#### Technical Indicators (Single Asset View)")
            if selected_tickers:
                asset_to_view = st.selectbox("Select Asset for Tech Analysis", options=selected_tickers)
                show_sma = st.checkbox("Show SMA (50)")
                show_ema = st.checkbox("Show EMA (20)")
                
                asset_data = portfolio_data[asset_to_view]
                fig_tech = charts.plot_interactive_chart(asset_data, f"{asset_to_view} Price History", show_sma=show_sma, show_ema=show_ema)
                st.plotly_chart(fig_tech, use_container_width=True)

        with tab3:
            st.subheader("🤖 AI Portfolio Optimization")
            st.markdown("Find the optimal asset allocation to maximize your Sharpe Ratio.")
            
            if st.button("✨ Optimize Portfolio"):
                with st.spinner("Optimizing..."):
                    try:
                        opt_weights, opt_sharpe = utils.optimize_portfolio(returns)
                        
                        st.success(f"Optimization Complete! Max Potential Sharpe Ratio: {opt_sharpe:.2f}")
                        
                        # Display Current vs Optimized
                        res_df = pd.DataFrame({
                            "Ticker": selected_tickers,
                            "Current Weight": weights,
                            "Optimized Weight": opt_weights
                        })
                        res_df["Difference"] = res_df["Optimized Weight"] - res_df["Current Weight"]
                        
                        st.dataframe(res_df.style.format({"Current Weight": "{:.2%}", "Optimized Weight": "{:.2%}", "Difference": "{:.2%}"}))
                        
                        # Pie Chart Comparison
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            st.markdown("**Current Allocation**")
                            st.plotly_chart(px.pie(names=selected_tickers, values=weights), use_container_width=True)
                        with col_p2:
                            st.markdown("**Optimized Allocation**")
                            st.plotly_chart(px.pie(names=selected_tickers, values=opt_weights), use_container_width=True)
                    except Exception as e:
                        st.error(f"Optimization failed: {e}")

            st.markdown("---")
            st.subheader("📉 Stress Test Simulation")
            scenario = st.selectbox("Select History Scenario", ["2020 COVID Crash", "2008 Financial Crisis"])
            
            if st.button("Run Stress Test"):
                with st.spinner("Simulating history..."):
                    if scenario == "2020 COVID Crash":
                        t_start, t_end = "2020-02-15", "2020-03-23"
                    elif scenario == "2008 Financial Crisis":
                        t_start, t_end = "2008-09-01", "2009-03-09"
                    
                    # Fetch data for specific period
                    stress_data = utils.fetch_data(selected_tickers, t_start, t_end)
                    if not stress_data.empty and not stress_data.isna().all().all():
                        stress_returns = stress_data.pct_change().dropna()
                        try:
                            # Re-normalize weights if needed or just use current
                            stress_port_returns = utils.calculate_portfolio_returns(stress_returns, weights)
                            cum_stress = (1 + stress_port_returns).cumprod()
                            
                            max_drop = qs.stats.max_drawdown(stress_port_returns)
                            st.error(f"During {scenario}, your portfolio would have dropped by {max_drop*100:.2f}%")
                            
                            fig_stress = charts.plot_interactive_chart(cum_stress, f"Performance during {scenario}")
                            st.plotly_chart(fig_stress, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error calculating stress metrics: {e}")
                    else:
                        st.warning("Data not available for this period (some tickers might be too new).")

        with tab4:
            st.subheader("📡 Market Scanner (Nifty 50)")
            col_search, col_btn = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("🔍 Quick Search Ticker", placeholder="e.g., RELIANCE")
            with col_btn:
                scan_btn = st.button("🔄 Scan Market", use_container_width=True)

            if scan_btn:
                with st.spinner("Scanning Nifty 50 Universe..."):
                    # Use a larger list for scanning
                    scan_tickers = nse_tickers + ["WIPRO.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "ONGC.NS", "TITAN.NS"]
                    scan_results = utils.scan_market(scan_tickers)
                    st.session_state['scan_results'] = scan_results

            if 'scan_results' in st.session_state and not st.session_state['scan_results'].empty:
                df = st.session_state['scan_results']
                if search_query:
                    df = df[df['Ticker'].str.contains(search_query.upper())]

                # Style the dataframe with data_editor for better visuals
                st.data_editor(
                    df,
                    column_config={
                        "Signal": st.column_config.TextColumn(
                            "Signal",
                            help="AI Generated Signal",
                            width="medium",
                        ),
                        "RSI": st.column_config.ProgressColumn(
                            "RSI (14)",
                            help="Relative Strength Index",
                            format="%.2f",
                            min_value=0,
                            max_value=100,
                        ),
                        "Price": st.column_config.NumberColumn(
                            "Price",
                            format="₹ %.2f"
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )
                        
                st.markdown("### 🤖 Signal Breakdown")
                col_buy, col_sell = st.columns(2)
                with col_buy:
                    buy_signals = df[df['Signal'].str.contains("BUY")]
                    if not buy_signals.empty:
                        st.success(f"🔥 **Potential Buys**: {', '.join(buy_signals['Ticker'].tolist())}")
                        for _, row in buy_signals.iterrows():
                             st.caption(f"**{row['Ticker']}**: {row['Rationale']}")
                with col_sell:
                    sell_signals = df[df['Signal'].str.contains("SELL")]
                    if not sell_signals.empty:
                        st.error(f"❄️ **Potential Sells**: {', '.join(sell_signals['Ticker'].tolist())}")
                        for _, row in sell_signals.iterrows():
                             st.caption(f"**{row['Ticker']}**: {row['Rationale']}")
            elif 'scan_results' in st.session_state:
                 st.warning("No results found.")

        with tab5:
            st.subheader("Fundamental Data")
            st.markdown("Key financial metrics for selected assets.")
            
            if not selected_tickers:
                st.warning("No tickers selected.")
            else:
                funds_df = utils.get_fundamentals(selected_tickers)
                st.dataframe(funds_df, use_container_width=True)

        with tab6:
            st.subheader("Monte Carlo Simulation")
            st.markdown("Projecting future portfolio value based on historical volatility (1000 Simulations).")
            
            if st.button("Run Simulation"):
                with st.spinner("Simulating future paths..."):
                    try:
                        sim_df = utils.run_monte_carlo(portfolio_returns)
                        st.plotly_chart(charts.plot_monte_carlo(sim_df), use_container_width=True)
                    except Exception as e:
                        st.error(f"Simulation failed: {e}")

        # Report Download
        st.sidebar.markdown("---")
        if st.sidebar.button("📄 Download Full Report"):
             with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    report_path = os.path.join(tmpdir, "report.html")
                    qs.reports.html(portfolio_returns, benchmark=benchmark_returns, output=report_path)
                    with open(report_path, "r", encoding="utf-8") as f:
                        st.sidebar.download_button("Download HTML", f.read(), "report.html", "text/html")
                except Exception as e:
                    st.error(f"Report generation failed: {e}")
