# NSE Quantitative Arbitrage & Cost-of-Carry Terminal ⚡

<!-- LIVE_STREAMLIT_APP_BANNER_START -->
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nse-quant-terminal.streamlit.app/)

> **🚀 Live Streamlit App:** [**https://nse-quant-terminal.streamlit.app/**](https://nse-quant-terminal.streamlit.app/)
<!-- LIVE_STREAMLIT_APP_BANNER_END -->

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nse-quant-terminal.streamlit.app/)
[![NSE 3PM IST Daily Arbitrage Paper Trader](https://github.com/purntripathi-cmd/nse-quant-terminal/actions/workflows/auto_logger.yml/badge.svg)](https://github.com/purntripathi-cmd/nse-quant-terminal/actions/workflows/auto_logger.yml)

An institutional-grade **100% Live-Data Cash-and-Carry Arbitrage Scanner, Backtesting Suite, and Automated 3:00 PM IST Paper Trading Terminal** for Indian equities (National Stock Exchange of India).

---

## 🏛️ Core Quantitative & Live-Data Architecture

### 1. 100% Live NSE F&O Market Feed (Zero Synthetic / Formula Pricing)
All artificial or formula-derived futures pricing and hardcoded stock dictionaries have been completely eliminated:
* **Full 213-Stock F&O Universe (~635 Active Futures Contracts):** Dynamically ingests the complete NSE F&O stock futures universe (`Near`, `Next`, and `Far` monthly expiries) from official **NSE UDiFF F&O BhavCopy archives** (`nsearchives.nseindia.com`) paired with **Live Intraday NSE Equity Derivatives API streams** (`www.nseindia.com/api/liveEquity-derivatives?index=stock_fut`).
* **Exchange-Published Contract Specs:** Reads exact exchange-mandated contract expiry dates (`XpryDt`), official lot sizes (`NewBrdLotQty`), underlying spot prices (`UndrlygPric`), futures close/last/settlement prices (`ClsPric`, `LastPric`, `SttlmPric`), traded volume in lots (`TtlTradgVol`), and Open Interest (`OpnIntrst`).

### 2. Official NSE Last-Tuesday Expiry Calendar & Roll-Window Guard
* **Last Tuesday Rule (NSE Circular Effective Sep 2025):** Accurately models NSE monthly F&O expiry on the **Last Tuesday** of each contract month (rolling back to the preceding trading day on NSE holidays, such as `23NOV2026` due to the `2026-11-24` Guru Nanak Jayanti holiday).
* **Expiry Roll-Window Filter (`Days Left >= 5`) & Calendar Roll Spreads ($F_{\text{Next}} - F_{\text{Near}}$):** Prevents near-expiry annualization distortion by automatically transitioning top rankings to the liquid Next-Month contract when Near-Month has fewer than 5 days remaining, and computes live Calendar Roll Spreads.

### 3. True-to-Label SEBI Statutory Charges & Execution Regimes
Models exact SEBI / NSE True-to-Label statutory transaction costs (`backtest_engine.py`):
* **S4: Institutional Alpha-Carry (`institutional_roll`):** Multi-cycle cash hold (amortized 0.10% cash delivery STT across 4 monthly cycles) + monthly futures rollover (0.02% futures sell STT, 0.002% futures stamp duty, 0.00173% NSE F&O exchange fee, SEBI + IPFT ₹15/cr, 18% GST, 2 bps execution slippage) + **Early Backwardation Unwind** whenever intraday/daily basis collapses to $\le 0$ before expiry.
* **S3: Single-Cycle Physical Delivery Netted (`single_cycle_netted`):** Cash buy (0.10% STT + 0.015% stamp duty) + Futures short (0.02% STT) settled via physical delivery netting at official exchange expiry (`SttlmPric == UndrlygPric`).
* **S2 / S1: Full 4-Leg Round-Trip Unwind (`full_4leg_unwind`):** Full 0.20% round-trip cash STT + 0.02% futures STT + 4-leg brokerage/exchange/slippage friction.

---

## 🧪 Real-Data Historical Backtest Results (May 2026 – October 2026)

Using `backtest_engine.py`, we backtested 5 candidate arbitrage strategies across **6 complete 2026 NSE monthly F&O expiry cycles** (`21,896` authentic NSE F&O UDiFF BhavCopy contract records across 34 trading checkpoints) with a strict **`> 9.00%` Net XIRR gate** and **Guaranteed 4-Leg Profit Floor (`>= ₹1,500`)**:

| Strategy ID | Strategy Name | Real Trades | Positive Carry Win Rate (%) | `> 9.00%` XIRR Beat Accuracy | Avg Expected XIRR (%) | Avg Realized Net XIRR (%) | Avg Profit / Trade (₹) | Total Net Profit (₹) | Min Trade XIRR (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **S1** | Naive Unfiltered 4-Leg Market Unwind (`ClsPric` Exit) | 60 | `88.3%` | `33.3%` | `8.86%` | `9.10%` | `₹4,809.50` | `₹2,88,569.98` | `-11.46%` |
| **S2** | Unfiltered 4-Leg Exchange Settlement (`SttlmPric` Convergence) | 60 | **`100.0%`** | `31.7%` | `8.86%` | `9.67%` | `₹5,036.33` | `₹3,02,179.73` | `1.42%` |
| **S3** | Physical Delivery Netted (`>9%` XIRR Gate, `SttlmPric`) | 9 | **`100.0%`** | **`100.0%`** | `13.14%` | **`14.65%`** | `₹8,205.88` | `₹73,852.96` | **`9.48%`** |
| **S4** | **Institutional Alpha-Carry (`>9%` XIRR + Early Backwardation Unwind + Roll-Hold)** | **12** | **`100.0%`** | **`100.0%`** | **`13.52%`** | **`28.64%`** | **`₹8,913.16`** | **`₹1,06,957.91`** | **`9.21%`** |
| **S5** | **Sniper Guaranteed-Profit (`>9%` XIRR, Max 2 Trades/Cycle, 4-Leg Profit Floor)** | **9** | **`100.0%`** | **`100.0%`** | **`12.52%`** | **`25.54%`** | **`₹6,763.11`** | **`₹60,867.97`** | **`9.21%`** |

---

## 🕒 Daily 3:00 PM IST Weekday Scheduled Paper Trading & MTM Validation

To continuously validate live strategy accuracy during active NSE market hours:
* **Automated Schedule:** `.github/workflows/auto_logger.yml` runs every weekday (Monday–Friday) at **3:00 PM IST (`cron: '30 9 * * 1-5'` UTC)** — 30 minutes before the 3:30 PM NSE market close, when institutional cash-futures basis and roll liquidity peak.
* **Real-Time Mark-to-Market (MTM) & Convergence Settlement:**
  * Marks all `ACTIVE` positions in `paper_trades.csv` against live NSE Spot and Futures prices.
  * Automatically closes positions early (`CLOSED - Early Backwardation Unwind`) if live futures trade at or below spot (`Future <= Spot`), locking in accelerated annualized XIRR.
  * Automatically settles positions on expiry (`SETTLED - Expiry Convergence`) at `SttlmPric == UndrlygPric`.
  * Enters top qualifying `S4` hurdle-beating contracts and commits both `paper_trades.csv` and `arbitrage_log.csv` to the repository.

---

## 🚀 Local Installation & Usage

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Real-Data Historical Backtest Engine:**
   ```bash
   python backtest_engine.py
   ```

3. **Execute a Headless 3:00 PM IST Paper Trade & MTM Sync:**
   ```bash
   RUN_DAILY_3PM_PAPER_TRADE=true python app.py
   ```

4. **Launch the Interactive Streamlit Terminal:**
   ```bash
   streamlit run app.py
   ```
