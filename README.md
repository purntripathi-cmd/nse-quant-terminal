# NSE Quantitative Arbitrage & Net Return Terminal

A cloud-hosted Streamlit web application that scans the Indian stock market (NSE) in real-time, models momentum probabilities, accounts for statutory Zerodha delivery fees and short-term taxes, and ranks top/bottom trading opportunities.

## Key Features
* **Automated & Manual Refresh:** Auto-polls live 5-minute interval data every 300 seconds using Streamlit fragments, with a manual cache-purge button.
* **Success Probability Engine:** Combines moving average crossovers and rolling annualized volatility to project confidence scores.
* **Indian Statutory Tax & Fee Engine:** Incorporates Zerodha delivery charges (0% brokerage, 0.1% STT both ways, exchange transaction fees, stamp duty, GST, and CDSL DP charges) alongside STCG/LTCG capital gains tax.
* **Liquidity Safeguards:** Compares allocated capital against 1% of the asset's Average Daily Turnover (ADT) to flag potential execution slippage.
* **Extremes Ranking:** Automatically extracts and displays the **Top 3 Best Net XIRR Opportunities** and **Bottom 3 Non-Favourable / High-Risk Zones**.

## Tech Stack
* Python 3.9+
* Streamlit
* yfinance
* Pandas / NumPy

## Deployment
Hosted live on Streamlit Community Cloud and connected to a public GitHub repository.
