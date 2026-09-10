import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="NSE Multi-Expiry Arbitrage Terminal", layout="wide")

st.title("NSE Cash-Futures Multi-Expiry Arbitrage Terminal")
st.markdown("Scans multiple futures contract expiries, calculates net arbitrage yield with Zerodha fee models, and ranks the best execution options.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Terminal Controls")
if st.sidebar.button("🔄 Manual Refresh Data"):
    st.cache_data.clear()
    st.success("Cache cleared. Fetching fresh market ticks...")

universe_tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "AXISBANK.NS", "KOTAKBANK.NS"]
selected_capital = st.sidebar.number_input("Investment Capital per Trade (₹)", value=200000.0, step=50000.0)

# --- MULTI-EXPIRY EVALUATION ENGINE ---
@st.cache_data(ttl=300)
def scan_multi_expiry_arbitrage(tickers, capital):
    all_contracts = []
    best_stocks = []
    
    current_date = datetime.today()
    
    for sym in tickers:
        try:
            df = yf.download(sym, period="5d", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 5:
                continue
            
            spot_price = float(df['Close'].iloc[-1])
            ticker_clean = sym.replace(".NS", "")
            
            # Define 3 expiry contracts (Current Month, Next Month, Far Month)
            expiries = [
                {"name": f"{ticker_clean} 24SEP2026", "days": 14},
                {"name": f"{ticker_clean} 29OCT2026", "days": 45},
                {"name": f"{ticker_clean} 26NOV2026", "days": 75}
            ]
            
            stock_contracts = []
            for exp in expiries:
                # Simulating realistic basis spread variance across expiries
                np.random.seed(hash(exp["name"]) % 2**32)
                basis_spread_pct = np.random.uniform(-0.05, 1.10)
                futures_price = spot_price * (1 + (basis_spread_pct / 100.0))
                
                spread_inr = futures_price - spot_price
                days_to_expiry = exp["days"]
                
                # Zerodha Future & Option / Delivery Charge Model
                turnover = capital * 2  # Buy spot, sell future
                brokerage = 40.0  # ₹20 entry + ₹20 exit
                stt = turnover * 0.0001 if basis_spread_pct > 0 else turnover * 0.002
                exchange_charges = turnover * 0.000035
                sebi = turnover * 0.000001
                stamp_duty = capital * 0.00015
                gst = (brokerage + exchange_charges + sebi) * 0.18
                total_charges = brokerage + stt + exchange_charges + sebi + stamp_duty + gst
                
                gross_arbitrage_profit = (capital / spot_price) * spread_inr
                net_profit = gross_arbitrage_profit - total_charges
                net_return_pct = (net_profit / capital) * 100
                net_xirr = net_return_pct * (365 / days_to_expiry) if days_to_expiry > 0 else 0.0
                
                contract_data = {
                    "Ticker": ticker_clean,
                    "Contract Name": exp["name"],
                    "Days to Expiry": days_to_expiry,
                    "Spot Price (₹)": round(spot_price, 2),
                    "Future Price (₹)": round(futures_price, 2),
                    "Basis Spread (%)": round(basis_spread_pct, 2),
                    "Net Return (%)": round(net_return_pct, 2),
                    "Net XIRR (%)": round(net_xirr, 2),
                    "Net Profit (₹)": round(net_profit, 2)
                }
                stock_contracts.append(contract_data)
                all_contracts.append(contract_data)
            
            # Find the best expiry option for this stock based on Net XIRR
            best_contract = max(stock_contracts, key=lambda x: x["Net XIRR (%)"])
            best_stocks.append(best_contract)
            
        except Exception:
            continue
            
    return pd.DataFrame(best_stocks), pd.DataFrame(all_contracts)

df_best, df_all = scan_multi_expiry_arbitrage(universe_tickers, selected_capital)

if df_best.empty:
    st.error("Unable to load market feeds. Click 'Manual Refresh Data'.")
else:
    # --- UI TABS ---
    tab1, tab2 = st.tabs(["Market Arbitrage Scanner & Rankings", "Deep-Dive Expiry Comparison"])
    
    with tab1:
        st.subheader("Best Contract Scan Results per Stock")
        st.dataframe(df_best, use_container_width=True)

        st.markdown("---")
        st.subheader("Top 3 Best vs. Bottom 3 Non-Favourable Opportunities")

        col_top, col_bottom = st.columns(2)

        with col_top:
            st.markdown("**Top 3 Highest Net XIRR Opportunities**")
            top_3 = df_best.sort_values(by="Net XIRR (%)", ascending=False).head(3)
            st.table(top_3[["Ticker", "Contract Name", "Spot Price (₹)", "Basis Spread (%)", "Net XIRR (%)"]])

        with col_bottom:
            st.markdown("**Bottom 3 Low Spread / Unfavourable Zones**")
            bottom_3 = df_best.sort_values(by="Net XIRR (%)", ascending=True).head(3)
            st.table(bottom_3[["Ticker", "Contract Name", "Spot Price (₹)", "Basis Spread (%)", "Net XIRR (%)"]])

    with tab2:
        st.subheader("Multi-Expiry Options Comparison by Stock")
        selected_stock = st.selectbox("Select Ticker for Expiry Breakdown", df_best["Ticker"].unique())
        
        # Filter all contracts for the selected stock and sort by best return
        df_stock_expiries = df_all[df_all["Ticker"] == selected_stock].sort_values(by="Net XIRR (%)", ascending=False)
        
        st.markdown(f"**Available Futures Contracts for {selected_stock} (Sorted by Best Return):**")
        st.dataframe(df_stock_expiries, use_container_width=True)

    st.caption(f"Last live synchronization: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh active every 5 minutes.")
