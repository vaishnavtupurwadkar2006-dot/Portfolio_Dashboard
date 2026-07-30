import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def plot_interactive_chart(data, title, y_axis_label="Value", show_sma=False, show_ema=False):
    """Creates an interactive line chart with optional indicators."""
    fig = go.Figure()
    
    # Check if data is a DataFrame or Series
    if isinstance(data, pd.Series):
        fig.add_trace(go.Scatter(x=data.index, y=data, mode='lines', name=title))
        
        if show_sma:
            sma = data.rolling(window=50).mean()
            fig.add_trace(go.Scatter(x=data.index, y=sma, mode='lines', name='SMA (50)', line=dict(dash='dash', color='orange')))
            
        if show_ema:
            ema = data.ewm(span=20, adjust=False).mean()
            fig.add_trace(go.Scatter(x=data.index, y=ema, mode='lines', name='EMA (20)', line=dict(dash='dot', color='green')))

    else:
        for col in data.columns:
            fig.add_trace(go.Scatter(x=data.index, y=data[col], mode='lines', name=col))

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_axis_label,
        hovermode="x unified",
        template="plotly_dark"
    )
    return fig

def plot_correlation_matrix(returns):
    """Plots a correlation heatmap."""
    corr = returns.corr()
    fig = px.imshow(
        corr, 
        text_auto=True, 
        aspect="auto", 
        color_continuous_scale="RdBu_r",
        title="Asset Correlation Matrix"
    )
    return fig

def plot_monte_carlo(simulation_df):
    """Plots Monte Carlo simulation results."""
    fig = go.Figure()
    
    # Plot first 100 simulations to avoid lag
    for col in simulation_df.columns[:100]:
        fig.add_trace(go.Scatter(x=simulation_df.index, y=simulation_df[col], mode='lines', opacity=0.1, showlegend=False, line=dict(color='cyan')))
    
    # Plot Mean Path
    mean_path = simulation_df.mean(axis=1)
    fig.add_trace(go.Scatter(x=simulation_df.index, y=mean_path, mode='lines', name='Mean Projection', line=dict(color='red', width=3)))
    
    fig.update_layout(
        title="Monte Carlo Simulation (Projected Growth of $1)",
        xaxis_title="Trading Days",
        yaxis_title="Portfolio Value",
        template="plotly_dark"
    )
    return fig

def plot_drawdown(drawdown_series):
    """Plots underwater drawdown chart."""
    fig = px.area(drawdown_series, title="Portfolio Drawdown", markers=False)
    fig.update_layout(template="plotly_dark", yaxis_title="Drawdown %")
    return fig
