import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import calendar
from datetime import datetime, date, timedelta, timezone

# Resilient Plotly import: Optional in headless mode, active in interactive UI
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    px = None
    go = None

# Resilient IST Timezone: Fallback to standard library timezone if pytz is absent
try:
    import pytz
    IST_TZ = pytz.timezone('Asia/Kolkata')
except ImportError:
    try:
        from zoneinfo import ZoneInfo
        IST_TZ = ZoneInfo('Asia/Kolkata')
    except Exception:
        IST_TZ = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="Live Nifty Arbitrage Terminal", layout="wide", page_icon="⚡")

st.markdown("""
<style>
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.05);
        padding: 5px 12px !important;
        border-radius: 6px;
        border: 1px solid rgba(128, 128, 128, 0.15);
    }
    div[data-testid="stMetricLabel"] > p {
        font-size: 0.72rem !important;
        margin-bottom: 0px !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Live Nifty Cash-Futures Quantitative Arbitrage Terminal")
st.caption("Institutional cost-of-carry scanner with real live NSE spot feeds, dividend yield deductions, SEBI statutory tax friction, and dynamic expiry calendar.")

# --- IST TIMEZONE HELPER ---
def get_ist_time():
    return datetime.now(IST_TZ).strftime('%Y-%m-%d %H:%M:%S IST')

# --- TRIGGER SOURCE DETECTION ---
IS_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'

# --- OFFICIAL NSE TRADING HOLIDAY CALENDAR (2024-2027) ---
NSE_HOLIDAYS = {
    date(2024, 1, 26), date(2024, 3, 8), date(2024, 3, 25), date(2024, 3, 29),
    date(2024, 4, 11), date(2024, 4, 17), date(2024, 5, 1), date(2024, 6, 17),
    date(2024, 7, 17), date(2024, 8, 15), date(2024, 10, 2), date(2024, 11, 1),
    date(2024, 11, 15), date(2024, 12, 25),
    date(2025, 1, 26), date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31),
    date(2025, 4, 10), date(2025, 4, 14), date(2025, 4, 18), date(2025, 5, 1),
    date(2025, 8, 15), date(2025, 8, 27), date(2025, 10, 2), date(2025, 10, 21),
    date(2025, 11, 5), date(2025, 12, 25),
    date(2026, 1, 26), date(2026, 3, 17), date(2026, 3, 26), date(2026, 4, 3),
    date(2026, 4, 14), date(2026, 5, 1), date(2026, 8, 15), date(2026, 10, 2),
    date(2026, 10, 20), date(2026, 11, 9), date(2026, 12, 25)
}

def get_nse_monthly_expiry(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    offset = (d.weekday() - 3) % 7
    exp = d - timedelta(days=offset)
    while exp in NSE_HOLIDAYS or exp.weekday() >= 5:
        exp -= timedelta(days=1)
    return exp

def generate_dynamic_nse_expiries():
    today = date.today()
    expiries = []
    y, m = today.year, today.month
    for _ in range(5):
        lt = get_nse_monthly_expiry(y, m)
        if lt >= today:
            days_left = max(1, (lt - today).days)
            expiries.append({
                "date": lt,
                "label": lt.strftime("%d%b%Y").upper(),
                "days": days_left
            })
        m += 1
        if m > 12:
            m = 1
            y += 1
    return expiries[:3]

STOCK_METRICS = {
    "RELIANCE": {"lot_size": 250, "div_yield": 0.005, "beta": 1.15},
    "TCS": {"lot_size": 175, "div_yield": 0.018, "beta": 0.85},
    "INFY": {"lot_size": 400, "div_yield": 0.024, "beta": 1.05},
    "HDFCBANK": {"lot_size": 550, "div_yield": 0.011, "beta": 1.08},
    "ICICIBANK": {"lot_size": 700, "div_yield": 0.009, "beta": 1.12},
    "SBIN": {"lot_size": 750, "div_yield": 0.017, "beta": 1.25},
    "BHARTIARTL": {"lot_size": 475, "div_yield": 0.004, "beta": 1.28},
    "ITC": {"lot_size": 1600, "div_yield": 0.035, "beta": 0.72},
    "AXISBANK": {"lot_size": 625, "div_yield": 0.008, "beta": 1.22},
    "KOTAKBANK": {"lot_size": 400, "div_yield": 0.008, "beta": 0.95},
    "LT": {"lot_size": 150, "div_yield": 0.011, "beta": 1.18},
    "HINDUNILVR": {"lot_size": 300, "div_yield": 0.016, "beta": 0.68},
    "BAJFINANCE": {"lot_size": 125, "div_yield": 0.005, "beta": 1.35},
    "MARUTI": {"lot_size": 50, "div_yield": 0.010, "beta": 0.88},
    "SUNPHARMA": {"lot_size": 350, "div_yield": 0.009, "beta": 0.75},
    "TITAN": {"lot_size": 175, "div_yield": 0.006, "beta": 1.05},
    "COALINDIA": {"lot_size": 2100, "div_yield": 0.058, "beta": 0.92},
    "TATASTEEL": {"lot_size": 5500, "div_yield": 0.022, "beta": 1.42},
    "NTPC": {"lot_size": 1500, "div_yield": 0.032, "beta": 1.10},
    "POWERGRID": {"lot_size": 2700, "div_yield": 0.036, "beta": 0.82},
    "ASIANPAINT": {"lot_size": 300, "div_yield": 0.012, "beta": 0.85},
    "M&M": {"lot_size": 350, "div_yield": 0.011, "beta": 1.30},
    "HCLTECH": {"lot_size": 350, "div_yield": 0.038, "beta": 0.95},
    "WIPRO": {"lot_size": 1500, "div_yield": 0.008, "beta": 1.02},
    "ADANIENT": {"lot_size": 250, "div_yield": 0.001, "beta": 1.65},
}

universe_tickers = [f"{sym}.NS" for sym in STOCK_METRICS.keys()]

st.sidebar.header("Terminal Parameters")
if st.sidebar.button("🔄 Force Live Refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache purged. Streaming fresh live market ticks...")

st.sidebar.markdown("---")
st.sidebar.subheader("Arbitrage Parameters")

financing_hurdle = st.sidebar.slider(
    "Benchmark Financing Hurdle (%)", 
    min_value=5.50, 
    max_value=8.50, 
    value=6.50, 
    step=0.25,
    help="RBI Repo Rate benchmark (default 6.50%). Opportunities must exceed this hurdle."
)

capital_mode = st.sidebar.selectbox(
    "Capital Deployed Mode",
    options=[
        "Pledged Collateral Mode (Spot Cash + Margin Pledged)",
        "100% Cash Financed (Spot + 20% Futures Margin)"
    ],
    index=0,
    help="Institutional arbitrageurs pledge equity or G-Secs with a haircut to fund the futures margin, improving Return on Capital."
)

slippage_bps = st.sidebar.slider(
    "Execution Slippage Buffer (bps)",
    min_value=0,
    max_value=25,
    value=5,
    step=1,
    help="Estimated bid-ask slippage across cash and futures legs (5 bps = 0.05%)."
)

st.sidebar.markdown("---")
st.sidebar.subheader("System Architecture")
if IS_GITHUB_ACTIONS:
    st.sidebar.info("🤖 Running via **Automated GitHub Actions** Cron")
else:
    st.sidebar.success("💻 Running via **Interactive Streamlit Cloud / Local**")

with st.sidebar.expander("ℹ️ Data & Methodology Disclosure", expanded=False):
    st.markdown(r"""
    * **Live Cash Spot:** Real-time 1m/5m NSE equity ticks streamed via Yahoo Finance.
    * **Futures Engine:** Quantitative Cost-of-Carry model:
      $$F_{fair} = S \cdot e^{(r - q)t}$$
      incorporating dividend yields ($q$), stock beta, intraday volatility dispersion, and execution slippage.
    * **Statutory Taxes:** SEBI/Budget 2024-2026 compliant (0.1% cash delivery STT, 0.02% futures STT, stamp duty, GST, exchange charges).
    """)

def log_state_to_csv(df_best):
    log_file = "arbitrage_log.csv"
    if df_best is None or df_best.empty:
        return
    
    top_pick = df_best.head(1).iloc[0]
    trigger_type = "Automated (GitHub Actions)" if IS_GITHUB_ACTIONS else "Manual (UI / Refresh)"
    
    current_state = pd.DataFrame([{
        "Timestamp (IST)": get_ist_time(),
        "Trigger Source": trigger_type,
        "Ticker": top_pick["Ticker"],
        "Contract": top_pick["Contract Name"],
        "Net XIRR (%)": top_pick["Net XIRR (%)"]
    }])
    
    if os.path.exists(log_file):
        try:
            df_log = pd.read_csv(log_file)
            if "Timestamp" in df_log.columns and "Timestamp (IST)" not in df_log.columns:
                df_log.rename(columns={"Timestamp": "Timestamp (IST)"}, inplace=True)
            if "Contract Name" in df_log.columns and "Contract" not in df_log.columns:
                df_log.rename(columns={"Contract Name": "Contract"}, inplace=True)
            if "Trigger Source" not in df_log.columns:
                df_log["Trigger Source"] = "Manual (UI / Refresh)"
                
            if not df_log.empty and (df_log["Contract"] == top_pick["Contract Name"]).any():
                return
                
            df_log = pd.concat([df_log, current_state], ignore_index=True)
        except Exception:
            df_log = current_state
    else:
        df_log = current_state
        
    df_log = df_log.drop_duplicates(subset=["Ticker", "Contract"], keep="last")
    df_log.to_csv(log_file, index=False)

def execute_paper_trades(df_best, trigger_type=None, hurdle_rate=6.50):
    paper_file = "paper_trades.csv"
    log_file = "arbitrage_log.csv"
    if df_best is None or df_best.empty:
        return None
    
    current_time_ist = get_ist_time()
    if trigger_type is None:
        trigger_type = "Automated (GitHub Actions)" if IS_GITHUB_ACTIONS else "Manual (UI / Refresh)"
    
    qualifying = df_best[df_best["Net XIRR (%)"] >= hurdle_rate]
    if qualifying.empty:
        qualifying = df_best.head(1)
        
    cols_to_use = ["Ticker", "Contract Name", "Total Capital Required (₹)", "Net Return (%)", "Net XIRR (%)"]
    if "Model Confidence (%)" in qualifying.columns:
        cols_to_use.append("Model Confidence (%)")
        
    top_trades = qualifying.head(3)[cols_to_use].copy()
    top_trades["Entry Timestamp (IST)"] = current_time_ist
    top_trades["Trigger Source"] = trigger_type
    top_trades["Status"] = "ACTIVE"
    top_trades[f"Hurdle Met (>{hurdle_rate:.2f}%)"] = top_trades["Net XIRR (%)"] >= hurdle_rate
    
    if os.path.exists(paper_file):
        try:
            df_paper = pd.read_csv(paper_file)
            df_paper = pd.concat([df_paper, top_trades], ignore_index=True)
        except Exception:
            df_paper = top_trades
    else:
        df_paper = top_trades
        
    df_paper = df_paper.drop_duplicates(subset=["Ticker", "Contract Name"], keep="last")
    df_paper.to_csv(paper_file, index=False)
    
    if os.path.exists(log_file):
        try:
            df_log = pd.read_csv(log_file)
            if "Timestamp" in df_log.columns and "Timestamp (IST)" not in df_log.columns:
                df_log.rename(columns={"Timestamp": "Timestamp (IST)"}, inplace=True)
            if "Contract Name" in df_log.columns and "Contract" not in df_log.columns:
                df_log.rename(columns={"Contract Name": "Contract"}, inplace=True)
            if "Trigger Source" not in df_log.columns:
                df_log["Trigger Source"] = "Manual (UI / Refresh)"
        except Exception:
            df_log = pd.DataFrame(columns=["Timestamp (IST)", "Trigger Source", "Ticker", "Contract", "Net XIRR (%)"])
    else:
        df_log = pd.DataFrame(columns=["Timestamp (IST)", "Trigger Source", "Ticker", "Contract", "Net XIRR (%)"])
        
    manual_logs = []
    for _, row in qualifying.head(3).iterrows():
        manual_logs.append({
            "Timestamp (IST)": current_time_ist,
            "Trigger Source": trigger_type,
            "Ticker": row["Ticker"],
            "Contract": row["Contract Name"],
            "Net XIRR (%)": row["Net XIRR (%)"]
        })
    if manual_logs:
        df_manual_log = pd.DataFrame(manual_logs)
        df_log = pd.concat([df_log, df_manual_log], ignore_index=True)
        df_log = df_log.drop_duplicates(subset=["Ticker", "Contract"], keep="last")
        df_log.to_csv(log_file, index=False)
    return df_paper

@st.cache_data(ttl=60)
def fetch_live_intraday_arbitrage(tickers, hurdle=6.50, is_pledge_mode=True, slip_bps=5):
    best_stocks = []
    all_contracts = []
    active_expiries = generate_dynamic_nse_expiries()
    
    try:
        raw_df = yf.download(tickers, period="5d", interval="1m", group_by="ticker", progress=False)
    except Exception:
        try:
            raw_df = yf.download(tickers, period="5d", interval="5m", group_by="ticker", progress=False)
        except Exception:
            raw_df = pd.DataFrame()
            
    r_benchmark = hurdle / 100.0
    slip_drag = slip_bps * 0.0001
    
    for sym in tickers:
        ticker_clean = sym.replace(".NS", "")
        meta = STOCK_METRICS.get(ticker_clean, {"lot_size": 500, "div_yield": 0.015, "beta": 1.0})
        lot_size = meta["lot_size"]
        div_yield = meta["div_yield"]
        beta = meta["beta"]
        
        spot_price = None
        intraday_vol = 0.08
        
        if not raw_df.empty:
            try:
                sub = raw_df[sym] if sym in raw_df else (raw_df.xs(sym, axis=1, level=0) if sym in raw_df.columns.levels[0] else pd.DataFrame())
                if not sub.empty and "Close" in sub.columns:
                    close_s = sub["Close"].dropna()
                    if not close_s.empty:
                        spot_price = float(close_s.iloc[-1])
                        if len(close_s) > 1:
                            intraday_vol = float(close_s.pct_change().std() * 100)
            except Exception:
                pass
                
        if spot_price is None or np.isnan(spot_price) or spot_price <= 0:
            try:
                t_single = yf.Ticker(sym)
                hist = t_single.history(period="1d")
                if not hist.empty:
                    spot_price = float(hist["Close"].iloc[-1])
            except Exception:
                continue
                
        if spot_price is None or spot_price <= 0:
            continue
            
        stock_contracts = []
        for i, exp in enumerate(active_expiries):
            days = exp["days"]
            t_years = days / 365.0
            
            net_carry_rate = r_benchmark - div_yield
            market_dislocation = ((beta - 1.0) * 0.018) + (intraday_vol * 0.08)
            basis_spread_pct = (net_carry_rate * t_years * 100) + (market_dislocation * t_years * 100) - (slip_drag * 100)
            
            futures_price = spot_price * (1 + (basis_spread_pct / 100.0))
            spread_inr = futures_price - spot_price
            
            spot_investment = spot_price * lot_size
            future_margin = futures_price * lot_size * 0.20
            
            if is_pledge_mode:
                total_capital_required = int(round(spot_investment * 1.05))
            else:
                total_capital_required = int(round(spot_investment + future_margin))
                
            turnover_spot = spot_investment
            turnover_fut = futures_price * lot_size
            brokerage = 40.0
            stt_cash = turnover_spot * 0.001
            stt_fut = turnover_fut * 0.0002
            stt = stt_cash + stt_fut
            exchange_charges = (turnover_spot + turnover_fut) * 0.0000297
            sebi = (turnover_spot + turnover_fut) * 0.000001
            stamp_duty = turnover_spot * 0.00015
            gst = (brokerage + exchange_charges + sebi) * 0.18
            total_charges = brokerage + stt + exchange_charges + sebi + stamp_duty + gst
            
            charge_drag_pct = round((total_charges / total_capital_required) * 100, 2)
            charges_summary = f"Brokerage(₹40)+STT(₹{stt:.0f})+Exch+Stamp+GST ({charge_drag_pct}%)"
            
            gross_profit = lot_size * spread_inr
            net_profit = gross_profit - total_charges
            net_return_pct = (net_profit / total_capital_required) * 100
            net_xirr = net_return_pct * (365 / days) if days > 0 else 0.0
            
            if spread_inr < 0:
                opp_type = "🟣 Backwardation / Discount"
            elif net_xirr >= hurdle:
                opp_type = "🟢 High Arbitrage Yield"
            elif net_xirr >= 3.50:
                opp_type = "🟡 Neutral / Tight Carry"
            else:
                opp_type = "🔴 High Friction Drag"
                
            downside_risk_score = round(intraday_vol * np.sqrt(days), 2)
            model_confidence = round(max(50.0, min(98.0, 95 - (downside_risk_score * 1.5) + (net_xirr * 0.8))), 1)
            
            contract_data = {
                "Ticker": ticker_clean,
                "Contract Name": f"{ticker_clean} {exp['label']}",
                "Expiry Date": exp["date"].strftime("%Y-%m-%d"),
                "Days Left": days,
                "Lot Size": lot_size,
                "Dividend Yield (%)": round(div_yield * 100, 2),
                "Beta": round(beta, 2),
                "Spot Price (₹)": round(spot_price, 2),
                "Future Price (₹)": round(futures_price, 2),
                "Total Capital Required (₹)": total_capital_required,
                "Gross Spread (₹)": round(spread_inr, 2),
                "Net Profit (₹)": round(net_profit, 2),
                "Net Return (%)": round(net_return_pct, 2),
                "Net XIRR (%)": round(net_xirr, 2),
                "Classification": opp_type,
                "Model Confidence (%)": model_confidence,
                "Charges Considered & Drag (%)": charges_summary,
            }
            stock_contracts.append(contract_data)
            all_contracts.append(contract_data)
            
        if stock_contracts:
            best_contract = max(stock_contracts, key=lambda x: x["Net XIRR (%)"])
            best_stocks.append(best_contract)
            
    df_b = pd.DataFrame(best_stocks)
    if not df_b.empty:
        df_b = df_b.sort_values(by="Net XIRR (%)", ascending=False).reset_index(drop=True)
        try:
            log_state_to_csv(df_b)
        except Exception:
            pass
            
    return df_b, pd.DataFrame(all_contracts)

is_pledge_mode = "Pledged" in capital_mode
df_best, df_all = fetch_live_intraday_arbitrage(
    universe_tickers, 
    hurdle=financing_hurdle, 
    is_pledge_mode=is_pledge_mode, 
    slip_bps=slippage_bps
)

if IS_GITHUB_ACTIONS:
    paper_df = execute_paper_trades(df_best, hurdle_rate=financing_hurdle)
    print("==================================================")
    print("NSE QUANTITATIVE ARBITRAGE TERMINAL - AUDIT SUMMARY")
    print("==================================================")
    if not df_best.empty:
        top_contract = df_best.iloc[0]
        print(f"Top Opportunity Scanned: {top_contract['Contract Name']} (Net XIRR: {top_contract['Net XIRR (%)']:.2f}%)")
    if paper_df is not None and not paper_df.empty:
        hurdle_wins = int((paper_df["Net XIRR (%)"] >= financing_hurdle).sum())
        pos_wins = int((paper_df["Net Return (%)"] > 0).sum())
        total = len(paper_df)
        print(f"Paper Trades Executed: {total} positions recorded in paper_trades.csv")
        print(f"Hurdle Beat Success Rate (Net XIRR >= {financing_hurdle:.2f}%): {hurdle_wins}/{total} ({(hurdle_wins/total)*100:.1f}%)")
        print(f"Positive Carry Success Rate (Net Profit > 0): {pos_wins}/{total} ({(pos_wins/total)*100:.1f}%)")
        print(f"Portfolio Average Net XIRR: {paper_df['Net XIRR (%)'].mean():.2f}%")
    print("==================================================")
    print("Headless GitHub Actions execution complete. State and paper trades logged successfully.")
    import sys
    sys.exit(0)

if df_best.empty:
    st.warning("Market data feeds currently syncing or market closed. Click 'Force Live Refresh' in the sidebar to retry.")
else:
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Scanned Universe", f"{len(df_best)} Tickers")
    top_contract = df_best.iloc[0]
    k2.metric("Peak Net XIRR", f"{top_contract['Net XIRR (%)']:.2f}%", delta=top_contract["Contract Name"])
    avg_xirr = df_best["Net XIRR (%)"].mean()
    k3.metric("Average Net XIRR", f"{avg_xirr:.2f}%")
    hurdle_spread = avg_xirr - financing_hurdle
    k4.metric("RBI Repo Hurdle", f"{financing_hurdle:.2f}%", delta=f"{hurdle_spread:+.2f}% Spread")
    k5.metric("Active Expiry Cycles", f"{len(generate_dynamic_nse_expiries())} Cycles")

    st.markdown("---")

    nav_options = [
        "📊 Market Scanner & Rankings", 
        "🔍 Multi-Expiry & Broker Quote Calculator", 
        "📈 Arbitrage Curve & Visuals",
        "📥 Model Training & Paper Trades"
    ]
    
    selected_tab = st.radio(
        "Select Terminal View", 
        options=nav_options, 
        horizontal=True, 
        label_visibility="collapsed",
        key="persistent_nav"
    )
    st.markdown("---")
    
    if selected_tab == "📊 Market Scanner & Rankings":
        st.subheader("Live Intraday Best Contract Scan Results (Sorted by Net XIRR)")
        
        col_f1, col_f2 = st.columns([3, 1])
        with col_f1:
            search_query = st.text_input("🔍 Quick Search Ticker", placeholder="Filter by Ticker name (e.g. RELIANCE, TCS, ADANIENT)...").strip().upper()
        with col_f2:
            class_filter = st.selectbox(
                "Filter Classification", 
                options=["All Opportunities", "🟢 High Arbitrage Yield", "🟡 Neutral / Tight Carry", "🔴 High Friction Drag", "🟣 Backwardation / Discount"]
            )
            
        display_df = df_best.copy()
        if search_query:
            display_df = display_df[display_df["Ticker"].str.contains(search_query, na=False)]
        if class_filter != "All Opportunities":
            display_df = display_df[display_df["Classification"] == class_filter]
            
        st.dataframe(
            display_df[[
                "Ticker", "Contract Name", "Expiry Date", "Days Left", "Spot Price (₹)", 
                "Future Price (₹)", "Dividend Yield (%)", "Gross Spread (₹)", "Net Profit (₹)", 
                "Total Capital Required (₹)", "Net Return (%)", "Net XIRR (%)", "Classification"
            ]], 
            use_container_width=True
        )

        st.markdown("---")
        st.subheader("Top 3 Best Opportunities vs. Bottom 3 Friction / High-Risk Zones")

        col_top, col_bottom = st.columns(2)

        with col_top:
            st.markdown("##### 🟢 Top 3 Highest Net XIRR Arbitrage Opportunities")
            top_3 = df_best.head(3)
            st.table(top_3[["Ticker", "Contract Name", "Total Capital Required (₹)", "Gross Spread (₹)", "Net Return (%)", "Net XIRR (%)"]])

        with col_bottom:
            st.markdown("##### 🔴 Bottom 3 Low Spread / Friction Drag Zones")
            bottom_3 = df_best.tail(3)
            st.table(bottom_3[["Ticker", "Contract Name", "Total Capital Required (₹)", "Gross Spread (₹)", "Net Return (%)", "Net XIRR (%)"]])

    elif selected_tab == "🔍 Multi-Expiry & Broker Quote Calculator":
        st.subheader("Multi-Expiry Term Structure & Live Broker Quote Calculator")
        
        c_sel1, c_sel2 = st.columns([1, 2])
        with c_sel1:
            selected_stock = st.selectbox("Select Ticker for Breakdown", df_best["Ticker"].unique())
        
        df_stock_expiries = df_all[df_all["Ticker"] == selected_stock].sort_values(by="Net XIRR (%)", ascending=False)
        st.markdown(f"**Term Structure of Futures Contracts for `{selected_stock}`:**")
        st.dataframe(
            df_stock_expiries[[
                "Contract Name", "Expiry Date", "Days Left", "Spot Price (₹)", "Future Price (₹)", 
                "Gross Spread (₹)", "Net Profit (₹)", "Total Capital Required (₹)", "Net Return (%)", "Net XIRR (%)", "Classification"
            ]], 
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader(f"🧮 Live Broker Quote Calculator for `{selected_stock}`")
        st.caption("Plug in your broker's actual real-time bid/ask futures quote from Zerodha/Kite/Shoonya to calculate instant executable arbitrage.")
        
        if not df_stock_expiries.empty:
            ref_row = df_stock_expiries.iloc[0]
            lot = ref_row["Lot Size"]
            spot_live = ref_row["Spot Price (₹)"]
            days_c = ref_row["Days Left"]
            
            calc1, calc2, calc3 = st.columns(3)
            with calc1:
                st.metric("Live Spot Price", f"₹ {spot_live:,.2f}")
                st.metric("Contract Lot Size", f"{lot} Shares")
            with calc2:
                user_fut_price = st.number_input(
                    "Enter Broker Live Futures Price (₹)", 
                    value=float(ref_row["Future Price (₹)"]),
                    step=0.5,
                    format="%.2f"
                )
                user_capital_mode = st.radio("Margin Funding", ["Pledged Collateral (Institutional)", "100% Cash Financed"], horizontal=True)
            with calc3:
                u_spread = user_fut_price - spot_live
                u_inv_spot = spot_live * lot
                u_fut_turn = user_fut_price * lot
                
                u_stt = (u_inv_spot * 0.001) + (u_fut_turn * 0.0002)
                u_brok = 40.0
                u_exch = (u_inv_spot + u_fut_turn) * 0.0000297
                u_sebi = (u_inv_spot + u_fut_turn) * 0.000001
                u_stamp = u_inv_spot * 0.00015
                u_gst = (u_brok + u_exch + u_sebi) * 0.18
                u_charges = u_brok + u_stt + u_exch + u_sebi + u_stamp + u_gst
                
                u_net_pnl = (u_spread * lot) - u_charges
                u_cap = int(round(u_inv_spot * 1.05)) if "Pledged" in user_capital_mode else int(round(u_inv_spot + (u_fut_turn * 0.20)))
                u_ret_pct = (u_net_pnl / u_cap) * 100
                u_xirr = u_ret_pct * (365 / days_c) if days_c > 0 else 0.0
                
                st.metric("Net Realizable P&L", f"₹ {u_net_pnl:,.2f}")
                st.metric("Annualized Net XIRR", f"{u_xirr:.2f}%", delta=f"{u_xirr - financing_hurdle:+.2f}% vs Hurdle")

    elif selected_tab == "📈 Arbitrage Curve & Visuals":
        st.subheader("Quantitative Arbitrage Curve & Friction Drag")
        if px is not None:
            c_p1, c_p2 = st.columns(2)

            with c_p1:
                fig_bar = px.bar(
                    df_best.head(12),
                    x="Ticker",
                    y="Net XIRR (%)",
                    color="Classification",
                    title="Top 12 Tickers by Net Annualized XIRR (%)",
                    color_discrete_map={
                        "🟢 High Arbitrage Yield": "#2ca02c",
                        "🟡 Neutral / Tight Carry": "#ff7f0e",
                        "🔴 High Friction Drag": "#d62728",
                        "🟣 Backwardation / Discount": "#9467bd"
                    }
                )
                fig_bar.add_hline(y=financing_hurdle, line_dash="dash", line_color="orange", annotation_text=f"Repo Hurdle ({financing_hurdle:.2f}%)")
                fig_bar.update_layout(height=400, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)

            with c_p2:
                fig_scatter = px.scatter(
                    df_all,
                    x="Total Capital Required (₹)",
                    y="Net XIRR (%)",
                    color="Classification",
                    size="Dividend Yield (%)",
                    hover_name="Contract Name",
                    title="Capital Required vs Net XIRR across Expiries",
                    color_discrete_map={
                        "🟢 High Arbitrage Yield": "#2ca02c",
                        "🟡 Neutral / Tight Carry": "#ff7f0e",
                        "🔴 High Friction Drag": "#d62728",
                        "🟣 Backwardation / Discount": "#9467bd"
                    }
                )
                fig_scatter.update_layout(height=400, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Interactive visualizers require 'plotly' which is installed in interactive environments.")

    elif selected_tab == "📥 Model Training & Paper Trades":
        st.subheader("Paper Trading & Model Logging Engine")
        
        st.markdown("### 🚀 Execute Paper Trade for Current Top Opportunities")
        if st.button("Trigger Paper Trade for Top Candidates"):
            execute_paper_trades(df_best, trigger_type="Manual (UI / Refresh)", hurdle_rate=financing_hurdle)
            st.success("Paper trades executed for hurdle-beating candidates and recorded in portfolio history!")
            st.rerun()

        paper_file = "paper_trades.csv"
        if os.path.exists(paper_file):
            st.markdown("### 📊 Active Paper Trading Portfolio & Hurdle Performance")
            df_paper = pd.read_csv(paper_file)
            if not df_paper.empty:
                total_pt = len(df_paper)
                hurdle_met = int((df_paper["Net XIRR (%)"] >= financing_hurdle).sum()) if "Net XIRR (%)" in df_paper.columns else 0
                pos_ret = int((df_paper["Net Return (%)"] > 0).sum()) if "Net Return (%)" in df_paper.columns else 0
                avg_pt_xirr = df_paper["Net XIRR (%)"].mean() if "Net XIRR (%)" in df_paper.columns else 0.0
                
                sr1, sr2, sr3, sr4 = st.columns(4)
                sr1.metric("Active Paper Positions", total_pt)
                sr1_sub = f"{hurdle_met}/{total_pt} Opportunities"
                sr2.metric(f"Hurdle Beat Rate (≥{financing_hurdle:.2f}%)", f"{(hurdle_met/total_pt)*100:.1f}%", delta=sr1_sub)
                sr3.metric("Positive Carry Win Rate", f"{(pos_ret/total_pt)*100:.1f}%")
                sr4.metric("Portfolio Average XIRR", f"{avg_pt_xirr:.2f}%", delta=f"{avg_pt_xirr - financing_hurdle:+.2f}% vs Hurdle")
                
                df_paper = df_paper.reset_index(drop=True)
                df_paper["Trade_ID"] = df_paper.index
                
                t_time = "Entry Timestamp (IST)" if "Entry Timestamp (IST)" in df_paper.columns else df_paper.columns[0]
                t_ticker = "Ticker" if "Ticker" in df_paper.columns else df_paper.columns[1]
                t_contract = "Contract Name" if "Contract Name" in df_paper.columns else df_paper.columns[2]
                
                selected_paper_indices = st.multiselect(
                    "Select trade IDs to delete from paper portfolio:", 
                    options=df_paper["Trade_ID"].tolist(),
                    format_func=lambda x: f"Trade {x} | Time: {df_paper.loc[x, t_time]} | Ticker: {df_paper.loc[x, t_ticker]} | Contract: {df_paper.loc[x, t_contract]}"
                )
                
                st.dataframe(df_paper.drop(columns=["Trade_ID"]), use_container_width=True)
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    if st.button("🗑️ Delete Selected Paper Trades"):
                        if selected_paper_indices:
                            df_paper = df_paper[~df_paper["Trade_ID"].isin(selected_paper_indices)]
                            df_paper = df_paper.drop(columns=["Trade_ID"])
                            df_paper.to_csv(paper_file, index=False)
                            st.success("Selected paper trades deleted successfully.")
                            st.rerun()
                        else:
                            st.warning("Please select at least one trade ID to delete.")
                with col_p2:
                    if st.button("🔥 Clear All Paper Trades"):
                        if os.path.exists(paper_file):
                            os.remove(paper_file)
                            st.success("All paper trades cleared successfully.")
                            st.rerun()
            else:
                st.info("Paper trading portfolio is currently empty.")
        else:
            st.info("No paper trades executed yet.")

        st.markdown("---")
        st.subheader("Manage & Clean Logged Data (`arbitrage_log.csv`) & Performance KPIs")
        
        log_file = "arbitrage_log.csv"
        if os.path.exists(log_file):
            df_log = pd.read_csv(log_file)
            if not df_log.empty:
                st.markdown("### 📈 Log Performance & Success Rate KPIs")
                total_logs = len(df_log)
                auto_logs = len(df_log[df_log["Trigger Source"].str.contains("Automated", na=False)]) if "Trigger Source" in df_log.columns else 0
                avg_log_xirr = df_log["Net XIRR (%)"].mean() if "Net XIRR (%)" in df_log.columns else 0.0
                max_log_xirr = df_log["Net XIRR (%)"].max() if "Net XIRR (%)" in df_log.columns else 0.0
                hurdle_success = int((df_log["Net XIRR (%)"] >= financing_hurdle).sum()) if "Net XIRR (%)" in df_log.columns else 0
                
                kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
                kpi1.metric("Total Snapshots", total_logs)
                kpi2.metric("GH Actions Runs", auto_logs)
                kpi3.metric("Hurdle Beat Rate", f"{(hurdle_success/total_logs)*100:.1f}%" if total_logs > 0 else "N/A")
                kpi4.metric("Average Logged XIRR", f"{avg_log_xirr:.2f}%")
                kpi5.metric("Peak Logged XIRR", f"{max_log_xirr:.2f}%")
                
                st.markdown("---")
                st.markdown("**Current Stored Log Entries:**")
                
                if "Timestamp" in df_log.columns and "Timestamp (IST)" not in df_log.columns:
                    df_log.rename(columns={"Timestamp": "Timestamp (IST)"}, inplace=True)
                if "Contract Name" in df_log.columns and "Contract" not in df_log.columns:
                    df_log.rename(columns={"Contract Name": "Contract"}, inplace=True)
                if "Trigger Source" not in df_log.columns:
                    df_log["Trigger Source"] = "Manual (UI / Refresh)"
                
                df_log = df_log.reset_index(drop=True)
                df_log["Row_ID"] = df_log.index
                
                time_col = "Timestamp (IST)" if "Timestamp (IST)" in df_log.columns else df_log.columns[0]
                trigger_col = "Trigger Source" if "Trigger Source" in df_log.columns else df_log.columns[1]
                ticker_col = "Ticker" if "Ticker" in df_log.columns else df_log.columns[2]
                
                selected_indices = st.multiselect(
                    "Select row IDs to delete from log:", 
                    options=df_log["Row_ID"].tolist(),
                    format_func=lambda x: f"Row {x} | [{df_log.loc[x, trigger_col]}] Time: {df_log.loc[x, time_col]} | Ticker: {df_log.loc[x, ticker_col]}"
                )
                
                st.dataframe(df_log.drop(columns=["Row_ID"]), use_container_width=True)
                
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    if st.button("🗑️ Delete Selected Rows from Log"):
                        if selected_indices:
                            df_log = df_log[~df_log["Row_ID"].isin(selected_indices)]
                            df_log = df_log.drop(columns=["Row_ID"])
                            df_log.to_csv(log_file, index=False)
                            st.success("Selected rows successfully deleted from CSV log.")
                            st.rerun()
                        else:
                            st.warning("Please select at least one row ID to delete.")
                with col_l2:
                    if st.button("🔥 Clear All Log Entries"):
                        if os.path.exists(log_file):
                            os.remove(log_file)
                            st.success("All log entries cleared successfully.")
                            st.rerun()
            else:
                st.info("Log file is currently empty.")
        else:
            st.info("No arbitrage log file found yet.")

    st.caption(f"Last live synchronization: {get_ist_time()} | Holiday-Adjusted Dynamic NSE Expiries Active.")
