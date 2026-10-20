# NSE Quantitative Arbitrage & Cost-of-Carry Terminal ⚡

<!-- LIVE_STREAMLIT_APP_BANNER_START -->
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nse-quant-terminal.streamlit.app/)

> **🚀 Live Streamlit App:** [**https://nse-quant-terminal.streamlit.app/**](https://nse-quant-terminal.streamlit.app/)
<!-- LIVE_STREAMLIT_APP_BANNER_END -->


[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nse-quant-terminal.streamlit.app/)
[![NSE Arbitrage Auto-Logger](https://github.com/purntripathi-cmd/nse-quant-terminal/actions/workflows/auto_logger.yml/badge.svg)](https://github.com/purntripathi-cmd/nse-quant-terminal/actions/workflows/auto_logger.yml)

An institutional-grade Cash-and-Carry Arbitrage scanner and terminal for Indian equities (National Stock Exchange). The application scans the top liquid F&O underlying constituents in real-time, computes theoretical Cost-of-Carry fair values accounting for dividend yield drag and market beta dispersion, models full SEBI statutory transaction costs, and tracks paper-traded positions across automated CI/CD runs.

---

## 🏛️ Core Quantitative Architecture

### 1. Vectorized Batch Spot Ingestion
Rather than issuing sequential, high-latency network queries across individual tickers, the engine employs multi-threaded vectorized batch downloads via `yfinance`. 
* **Throughput:** Scans 20+ liquid NSE large-caps in **~3.5 seconds** (down from >40s sequential).
* **Data Resiliency:** Ingests live 1-minute and 5-minute equity prints, computing intraday momentum, 20-period moving average deviations, and real-time liquidity depth.

### 2. Quantitative Cost-of-Carry & Fair Pricing Model
Under no-arbitrage equilibrium pricing, the theoretical futures price for an equity underlying is given by:
$$F_{\text{fair}} = S_t \cdot \left(1 + (r - q) \cdot \frac{T - t}{365}\right) + \Delta_{\text{basis}}(\beta, \sigma) - \text{Slippage}$$

Where:
* $S_t$: Real-time cash spot price.
* $r$: Risk-free benchmark rate (default 6.50% based on the RBI Repo Rate / 91-day T-Bill).
* $q$: Ticker-specific trailing annualized dividend yield (e.g., ITC, COALINDIA, TCS dividend drag).
* $\frac{T - t}{365}$: Precise day fraction to contract expiry.
* $\Delta_{\text{basis}}(\beta, \sigma)$: Systematic volatility and high-beta dislocation spread.
* $\text{Slippage}$: Impact cost penalized against Average Daily Turnover (ADT) and lot size.

### 3. Dynamic NSE Holiday-Adjusted Expiry Calendar
The engine dynamically computes monthly NSE F&O expiry dates (the last Thursday of the current and near month). It cross-references an integrated database of official NSE trading holidays (2024–2027) and automatically rolls expiry dates backward to the prior trading session whenever an expiry falls on an exchange holiday (e.g., Mahashivratri, Eid, Diwali, Christmas).

### 4. Dual Capital Deployment Modes
* **100% Cash-Funded (Covered Arbitrage):**
  $$Total\ Capital = S_t \cdot LotSize + Margin_{F\&O}$$
  Full cash outlay, offering zero margin-call risk with non-leveraged net XIRR.
* **Pledged Margin / Collateral (Optimized Yield):**
  Equity/ETF collateral (e.g., LiquidBeES, G-Secs) pledged with a standard 10% haircut, requiring only 20% liquid cash for exchange SPAN/exposure margins while idle collateral continues yielding ~6.50% interest.

### 5. Indian Statutory Tax & Transaction Friction Engine
Accurately models the complete post-Budget 2024/2026 statutory fee matrix:
* **Securities Transaction Tax (STT):**
  * Cash Delivery: 0.10% on entry and exit turnover.
  * F&O Futures: 0.02% on sell turnover.
* **Exchange Turnover Charges:** 0.00325% (NSE Cash) and 0.0019% (NSE Futures).
* **SEBI Regulatory Charges:** ₹10 per crore (0.0001%).
* **Stamp Duty:** 0.015% on cash buy; 0.002% on futures entry.
* **Goods and Services Tax (GST):** 18% levied on brokerage and exchange charges.

---

## 🛠️ Interactive Execution Tools

* **Live Broker Quote Calculator:** Enter live bid/ask quotes from Zerodha Kite, Groww, AngelOne, or Shoonya to compute exact net spread, total cash required, post-tax cash profit, and annualized Net XIRR before routing live orders.
* **Interactive F&O Lot-Size Override:** Adjust standard contract multipliers as NSE periodically revises derivative lot sizes.
* **Automated Paper Portfolio:** Tracks simulated fills meeting target hurdle rates ($XIRR \ge 6.50\%$), storing entry timestamps, capital required, and live status with full deduplication.

---

## 🤖 Headless CI/CD & Automated Logging

The terminal includes headless execution support triggered automatically via `.github/workflows/auto_logger.yml`:
* **Cron Frequency:** Runs every 15 minutes during active NSE market hours (Mon–Fri, 09:00–15:30 IST).
* **Audit Summaries:** Extracts top arbitrage opportunities and appends state snapshots to `arbitrage_log.csv` and executable paper trades to `paper_trades.csv`.
* **Zero UI Overhead:** Bypasses browser/Streamlit overhead during headless CI execution to complete logging jobs in under 5 seconds.

---

## 🚀 Local Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/purntripathi-cmd/nse-quant-terminal.git
   cd nse-quant-terminal
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the Streamlit Terminal:**
   ```bash
   streamlit run app.py
   ```

4. **Run Headless Audit Check:**
   ```bash
   python -c "import os; os.environ['GITHUB_ACTIONS']='true'; import app"
   ```

---

## ⚖️ Disclaimer
*This terminal is developed for quantitative research, algorithmic analysis, and educational simulation purposes. Arbitrage trading involves execution risk, market impact slippage, and derivative margin requirements. Users should verify live order books and consult certified financial advisors before deploying live capital.*
