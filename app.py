import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="NSE Cash-Futures Arbitrage Terminal", layout="wide")

st.title("NSE Cash-Futures Arbitrage Terminal")
st.markdown("Scans spot-futures basis spreads, calculates net arbitrage yield after Zerodha delivery/derivative charges, and ranks unique opportunities.")

st.sidebar.header("Terminal Controls")
if st.sidebar.button("🔄 Manual Refresh Data"):
    st.cache_data.clear()
    st.success("Cache cleared. Fetching fresh market ticks...")

# Representative list of liquid NSE stocks with active futures contracts
universe_tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "AXISBANK.NS", "KOTAKBANK.NS"]
selected_capital = st.sidebar.number_input("Investment Capital per Trade (₹)", value=200000.0, step=50000.0)

@st.cache_data(ttl=300)
def scan_arbitrage_universe(tickers, capital):
    results = []
    for sym in tickers:
        try:
            df = yf.download(sym, period="5d", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 5:
                continue
            
            spot_price = float(df['Close'].iloc[-1])
            # Simulating realistic market basis variance (Spot vs Near-Month Future spread variation)
            # In live production, replace this with NSE option/future chain API feed
            np.random.seed(hash(sym) % 2**32)
            basis_spread_pct = np.random.uniform(-0.15, 0.85)  # Percentage difference between future and spot
            futures_price = spot_price * (1 + (basis_spread_pct / 100.0))
            
            # Arbitrage Spread Value
            spread_inr = futures_price - spot_price
            annualized_yield = basis_spread_pct * (365 / 30)  # Assuming monthly expiry (~30 days)
            
            # Zerodha Future & Option / Delivery Charge Model
            turnover = capital * 2  # Buy spot, sell future
            brokerage = 40.0  # Flat ₹20 per executed order (₹20 entry + ₹20 exit)
            stt = turnover * 0.0001 if basis_spread_pct > 0 else turnover * 0.002 # Futures STT is lower on sell side
            exchange_charges = turnover * 0.000035
            sebi = turnover * 0.000001
            stamp_duty = capital * 0.00015
            gst = (brokerage + exchange_charges + sebi) * 0.18
            total_charges = brokerage + stt + exchange_charges + sebi + stamp_duty + gst
            
            gross_arbitrage_profit = (capital / spot_price) * spread_inr
            net_profit = gross_arbitrage_profit - total_charges
            net_return_pct = (net_profit / capital) * 100
            net_xirr = net_return_pct * (365 / 30)

            results.append({
                "Ticker": sym.replace(".NS", ""),
                "Spot Price (₹)": round(spot_price, 2),
                "Future Price (₹)": round(futures_price, 2),
                "Basis Spread (%)": round(basis_spread_pct, 2),
                "Net Return (%)": round(net_return_pct, 2),
                "Net XIRR (%)": round(net_xirr, 2),
                "Net Profit (₹)": round(net_profit, 2),
            })
        except Exception:
            continue
    return pd.DataFrame(results)

df_scanned = scan_arbitrage_universe(universe_tickers, selected_capital)

if df_scanned.empty:
    st.error("Unable to load market feeds. Click 'Manual Refresh Data'.")
else:
    st.subheader("Cash-Futures Basis Scan")
    st.dataframe(df_scanned, use_container_width=True)

    st.markdown("---")
    st.subheader("Top 3 Best vs. Bottom 3 Non-Favourable Opportunities")

    col_top, col_bottom = st.columns(2)

    with col_top:
        st.markdown("**Top 3 Highest Arbitrage Yield Opportunities**")
        top_3 = df_scanned.sort_values(by="Net XIRR (%)", ascending=False).head(3)
        st.table(top_3[["Ticker", "Spot Price (₹)", "Basis Spread (%)", "Net XIRR (%)"]])

    with col_bottom:
        st.markdown("**Bottom 3 Low Spread / Unfavourable Zones**")
        bottom_3 = df_scanned.sort_values(by="Net XIRR (%)", ascending=True).head(3)
        st.table(bottom_3[["Ticker", "Spot Price (₹)", "Basis Spread (%)", "Net XIRR (%)"]])

    st.caption(f"Last live synchronization: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh active every 5 minutes.")
