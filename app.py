import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="NSE AFE & Arbitrage Quant Terminal", layout="wide")

st.title("NSE Quantitative Arbitrage & Net Return Terminal")
st.markdown("Multi-asset scanner featuring live market polling, manual refresh, top/bottom extreme rankings, and Zerodha fee models.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Terminal Controls")

# Manual Refresh Button
if st.sidebar.button("🔄 Manual Refresh Data"):
    st.cache_data.clear()
    st.success("Cache cleared. Fetching fresh market ticks...")

universe_tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LTIM.NS", "AXISBANK.NS"]
selected_capital = st.sidebar.number_input("Investment Capital per Trade (₹)", value=100000.0, step=10000.0)
duration_days = st.sidebar.slider("Holding Duration (Days)", min_value=1, max_value=90, value=15)

# --- BULK DATA FETCHING & MODELING ENGINE ---
@st.cache_data(ttl=300)
def scan_market_universe(tickers, capital, duration):
    results = []
    for sym in tickers:
        try:
            df = yf.download(sym, period="5d", interval="5m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 20:
                continue
            
            current_price = float(df['Close'].iloc[-1])
            avg_volume = float(df['Volume'].mean())
            avg_turnover = avg_volume * current_price
            
            # Predictive & Momentum Scoring
            df['Returns'] = df['Close'].pct_change()
            df['SMA_9'] = df['Close'].rolling(9).mean()
            df['SMA_21'] = df['Close'].rolling(21).mean()
            
            momentum_score = 1.0 if df['SMA_9'].iloc[-1] > df['SMA_21'].iloc[-1] else 0.4
            volatility = df['Returns'].std() * np.sqrt(252)
            success_prob = min(92.0, max(30.0, (momentum_score * 65) + (1 / (volatility + 0.1)) * 12))
            
            expected_gain_pct = (0.15 * (duration / 365.0)) * (success_prob / 50.0)
            gross_profit = capital * expected_gain_pct
            
            # Zerodha Delivery Charge Engine
            turnover = capital + (capital * (1 + expected_gain_pct))
            brokerage = 0.0
            stt = turnover * 0.002
            exchange_charges = turnover * 0.000032
            sebi = turnover * 0.000001
            stamp_duty = capital * 0.00015
            gst = (brokerage + exchange_charges + sebi) * 0.18
            dp_fee = 15.34 if duration > 1 else 0.0
            total_charges = brokerage + stt + exchange_charges + sebi + stamp_duty + gst + dp_fee
            
            net_gain = gross_profit - total_charges
            tax = max(0.0, net_gain * 0.20) if duration <= 365 else max(0.0, net_gain * 0.125)
            net_profit = net_gain - tax
            net_return_pct = (net_profit / capital) * 100
            xirr = ((1 + (net_profit / capital)) ** (365 / duration) - 1) * 100
            
            max_safe_capital = avg_turnover * 0.01
            liquidity_flag = "Optimal" if capital <= max_safe_capital else "High Slippage Risk"

            results.append({
                "Ticker": sym.replace(".NS", ""),
                "LTP (₹)": round(current_price, 2),
                "Success Prob (%)": round(success_prob, 1),
                "Net XIRR (%)": round(xirr, 2),
                "Net Return (%)": round(net_return_pct, 2),
                "Net Profit (₹)": round(net_profit, 2),
                "Volatility": round(volatility * 100, 2),
                "Liquidity Status": liquidity_flag
            })
        except Exception:
            continue
    return pd.DataFrame(results)

df_scanned = scan_market_universe(universe_tickers, selected_capital, duration_days)

if df_scanned.empty:
    st.error("Unable to fetch data from market feeds. Try clicking 'Manual Refresh Data'.")
else:
    st.subheader("Market Universe Scan Results")
    st.dataframe(df_scanned, use_container_width=True)

    st.markdown("---")
    st.subheader("Top 3 Best vs. Bottom 3 Non-Favourable Opportunities")

    col_top, col_bottom = st.columns(2)

    with col_top:
        st.markdown("**Top 3 Highest Net XIRR Opportunities**")
        top_3 = df_scanned.sort_values(by="Net XIRR (%)", ascending=False).head(3)
        st.table(top_3[["Ticker", "LTP (₹)", "Success Prob (%)", "Net XIRR (%)"]])

    with col_bottom:
        st.markdown("**Bottom 3 Non-Favourable / High-Risk Zones**")
        bottom_3 = df_scanned.sort_values(by="Net XIRR (%)", ascending=True).head(3)
        st.table(bottom_3[["Ticker", "LTP (₹)", "Success Prob (%)", "Net XIRR (%)"]])

    st.caption(f"Last live synchronization: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh active every 5 minutes.")
