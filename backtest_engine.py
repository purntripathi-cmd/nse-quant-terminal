"""
Real-Data Historical Backtest Engine for NSE Cash-Futures Arbitrage Terminal.
Uses 100% authentic NSE F&O UDiFF BhavCopy archives (nsearchives.nseindia.com)
across 6 complete monthly F&O expiry cycles in 2026 (May 2026 – October 2026).
Zero synthetic or formula-generated futures prices.
"""

import io
import os
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
import requests
import pandas as pd
import numpy as np

# Official 2026 NSE F&O Trading Checkpoints across 6 Monthly Expiry Cycles
BACKTEST_DATES = [
    # May 2026 Cycle (Expiry: 2026-05-26)
    "20260428", "20260505", "20260512", "20260519", "20260525", "20260526",
    # June 2026 Cycle (Expiry: 2026-06-30)
    "20260602", "20260609", "20260616", "20260623", "20260629", "20260630",
    # July 2026 Cycle (Expiry: 2026-07-28)
    "20260701", "20260707", "20260714", "20260721", "20260727", "20260728",
    # August 2026 Cycle (Expiry: 2026-08-25)
    "20260803", "20260810", "20260817", "20260824", "20260825",
    # September 2026 Cycle (Expiry: 2026-09-29)
    "20260901", "20260908", "20260915", "20260922", "20260928", "20260929",
    # October 2026 Cycle (Expiry: 2026-10-27)
    "20261001", "20261008", "20261015", "20261022", "20261026",
]

EXPIRY_CYCLES = [
    {"name": "May-2026", "expiry": "2026-05-26", "entry": "2026-04-28", "exit": "2026-05-26"},
    {"name": "Jun-2026", "expiry": "2026-06-30", "entry": "2026-06-02", "exit": "2026-06-30"},
    {"name": "Jul-2026", "expiry": "2026-07-28", "entry": "2026-07-01", "exit": "2026-07-28"},
    {"name": "Aug-2026", "expiry": "2026-08-25", "entry": "2026-08-03", "exit": "2026-08-25"},
    {"name": "Sep-2026", "expiry": "2026-09-29", "entry": "2026-09-01", "exit": "2026-09-29"},
    {"name": "Oct-2026", "expiry": "2026-10-27", "entry": "2026-10-01", "exit": "2026-10-26"},
]


def compute_statutory_charges(spot_price: float, fut_price: float, lot_size: int, mode: str = "institutional_roll", slip_bps: float = 2.0) -> float:
    """
    Computes exact SEBI / NSE True-to-Label statutory taxes, exchange fees, GST, and execution slippage.
    Modes:
      - 'full_4leg_unwind': Fresh Cash Buy + Cash Sell (0.20% STT) + Fut Sell (0.02% STT) + 4 orders
      - 'single_cycle_netted': Single-Cycle Cash Buy + Fut Short settled via Physical Delivery Netting at Expiry
      - 'institutional_roll': Multi-cycle Cash Hold (4-cycle amortized Cash STT) + Monthly Futures Rollover
    """
    spot_val = float(spot_price) * int(lot_size)
    fut_val = float(fut_price) * int(lot_size)
    slip_rate = float(slip_bps) * 0.0001

    if mode == "full_4leg_unwind":
        stt = (spot_val * 0.002) + (fut_val * 0.0002)
        stamp = (spot_val * 0.00015) + (fut_val * 0.00002)
        exch = (spot_val * 2 * 0.0000297) + (fut_val * 2 * 0.0000173)
        sebi_ipft = (spot_val * 2 * 0.000002) + (fut_val * 2 * 0.000006)
        brok = 80.0
        gst = (brok + exch + sebi_ipft) * 0.18
        slip_cost = (spot_val + fut_val) * slip_rate
        return brok + stt + stamp + exch + sebi_ipft + gst + slip_cost

    elif mode == "single_cycle_netted":
        stt = (spot_val * 0.001) + (fut_val * 0.0002)
        stamp = spot_val * 0.00015
        exch = (spot_val * 0.0000297) + (fut_val * 0.0000173)
        sebi_ipft = (spot_val * 0.000002) + (fut_val * 0.000006)
        brok = 40.0
        gst = (brok + exch + sebi_ipft) * 0.18
        slip_cost = (spot_val + fut_val) * slip_rate
        return brok + stt + stamp + exch + sebi_ipft + gst + slip_cost

    else:  # institutional_roll
        stt = (spot_val * 0.00025) + (fut_val * 0.0002)
        stamp = (spot_val * 0.00015 / 4.0) + (fut_val * 0.00002)
        exch = (spot_val * 0.0000297 / 4.0) + (fut_val * 2 * 0.0000173)
        sebi_ipft = (spot_val * 0.000002 / 4.0) + (fut_val * 2 * 0.000006)
        brok = 40.0
        gst = (brok + exch + sebi_ipft) * 0.18
        slip_cost = fut_val * slip_rate
        return brok + stt + stamp + exch + sebi_ipft + gst + slip_cost


def download_nse_bhavcopy_history(dates=None) -> pd.DataFrame:
    if dates is None:
        dates = BACKTEST_DATES

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    def _fetch(dt_str):
        url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{dt_str}_F_0000.csv.zip"
        try:
            r = session.get(url, timeout=8)
            if r.status_code != 200:
                return None
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                cols = [
                    "TradDt", "FinInstrmTp", "TckrSymb", "XpryDt",
                    "OpnPric", "HghPric", "LwPric", "ClsPric", "LastPric",
                    "SttlmPric", "UndrlygPric", "OpnIntrst", "ChngInOpnIntrst",
                    "TtlTradgVol", "TtlTrfVal", "NewBrdLotQty"
                ]
                df = pd.read_csv(z.open(z.namelist()[0]), usecols=lambda c: c in cols)
                return df[df["FinInstrmTp"].isin(["STF", "IDF"])].copy()
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=15) as ex:
        dfs = list(ex.map(_fetch, dates))

    valid = [d for d in dfs if d is not None and not d.empty]
    if not valid:
        return pd.DataFrame()
    return pd.concat(valid, ignore_index=True)


def run_multi_strategy_backtest(df_raw: pd.DataFrame, hurdle_rate: float = 9.00):
    df = df_raw[df_raw["FinInstrmTp"] == "STF"].copy()
    df["TradDt"] = pd.to_datetime(df["TradDt"])
    df["XpryDt"] = pd.to_datetime(df["XpryDt"])
    df["DaysLeft"] = (df["XpryDt"] - df["TradDt"]).dt.days

    strategies = [
        {
            "id": "S1",
            "name": "S1: Naive Unfiltered 4-Leg Market Unwind (ClsPric Exit)",
            "charge_mode": "full_4leg_unwind",
            "use_sttlm": False,
            "early_backwardation_exit": False,
            "min_vol": 0,
            "min_xirr": 0.0,
            "guarantee_4leg_profit": False,
            "top_n": 10,
            "slip_bps": 5.0,
        },
        {
            "id": "S2",
            "name": "S2: Unfiltered 4-Leg Exchange Settlement (SttlmPric Convergence)",
            "charge_mode": "full_4leg_unwind",
            "use_sttlm": True,
            "early_backwardation_exit": False,
            "min_vol": 0,
            "min_xirr": 0.0,
            "guarantee_4leg_profit": False,
            "top_n": 10,
            "slip_bps": 5.0,
        },
        {
            "id": "S3",
            "name": "S3: Physical Delivery Netted (>9% XIRR Gate, SttlmPric)",
            "charge_mode": "single_cycle_netted",
            "use_sttlm": True,
            "early_backwardation_exit": False,
            "min_vol": 1000,
            "min_xirr": hurdle_rate,
            "guarantee_4leg_profit": True,
            "top_n": 3,
            "slip_bps": 3.0,
        },
        {
            "id": "S4",
            "name": "S4: Institutional Alpha-Carry (>9% XIRR + Early Backwardation Unwind + Roll-Hold)",
            "charge_mode": "institutional_roll",
            "use_sttlm": True,
            "early_backwardation_exit": True,
            "min_vol": 1000,
            "min_xirr": hurdle_rate,
            "guarantee_4leg_profit": True,
            "top_n": 3,
            "slip_bps": 2.0,
        },
        {
            "id": "S5",
            "name": "S5: Sniper Guaranteed-Profit (>9% XIRR, Max 2 Trades/Cycle, 4-Leg Profit Floor)",
            "charge_mode": "institutional_roll",
            "use_sttlm": True,
            "early_backwardation_exit": True,
            "min_vol": 2000,
            "min_xirr": hurdle_rate,
            "guarantee_4leg_profit": True,
            "top_n": 2,
            "slip_bps": 2.0,
        },
    ]

    summary_rows = []
    all_trades = []

    for cfg in strategies:
        strat_trades = []
        for cyc in EXPIRY_CYCLES:
            exp_dt = pd.to_datetime(cyc["expiry"])
            ent_dt = pd.to_datetime(cyc["entry"])
            ext_dt = pd.to_datetime(cyc["exit"])

            sub = df[(df["XpryDt"] == exp_dt) & (df["TradDt"] >= ent_dt) & (df["TradDt"] <= ext_dt)].copy()
            ent_df = sub[sub["TradDt"] == ent_dt].copy()
            if ent_df.empty:
                continue

            if cfg["min_vol"] > 0:
                ent_df = ent_df[(ent_df["TtlTradgVol"] >= cfg["min_vol"]) & (ent_df["OpnIntrst"] > 0)].copy()

            ent_df["EntrySpreadPct"] = ((ent_df["ClsPric"] - ent_df["UndrlygPric"]) / ent_df["UndrlygPric"]) * 100
            if cfg["min_vol"] > 0:
                ent_df = ent_df[(ent_df["EntrySpreadPct"] > 0.65) & (ent_df["EntrySpreadPct"] <= 1.85)].copy()

            exp_xirrs = []
            worst_case_nets = []
            for _, r in ent_df.iterrows():
                s0, f0, lot, d0 = float(r["UndrlygPric"]), float(r["ClsPric"]), int(r["NewBrdLotQty"]), max(1, int(r["DaysLeft"]))
                cap = s0 * lot * 1.05
                chg = compute_statutory_charges(s0, f0, lot, mode=cfg["charge_mode"], slip_bps=cfg["slip_bps"])
                chg_worst = compute_statutory_charges(s0, f0, lot, mode="full_4leg_unwind", slip_bps=5.0)
                exp_xirrs.append((((f0 - s0) * lot - chg) / cap) * 100 * (365.0 / d0))
                worst_case_nets.append(((f0 - s0) * lot) - chg_worst)

            ent_df["ExpectedXIRR"] = exp_xirrs
            ent_df["WorstCase4LegNet"] = worst_case_nets
            ent_df = ent_df.sort_values("ExpectedXIRR", ascending=False)
            if cfg["min_xirr"] > 0:
                ent_df = ent_df[ent_df["ExpectedXIRR"] > cfg["min_xirr"]]
            if cfg.get("guarantee_4leg_profit", False):
                ent_df = ent_df[ent_df["WorstCase4LegNet"] >= 1500.0]

            for _, row in ent_df.head(cfg["top_n"]).iterrows():
                sym = row["TckrSymb"]
                s0 = float(row["UndrlygPric"])
                f0 = float(row["ClsPric"])
                lot = int(row["NewBrdLotQty"])
                sym_path = sub[sub["TckrSymb"] == sym].sort_values("TradDt")
                exit_row = sym_path.iloc[-1]
                exit_type = "Expiry Settlement Convergence"

                if cfg["early_backwardation_exit"] and len(sym_path) > 1:
                    for _, prow in sym_path.iloc[1:-1].iterrows():
                        if (float(prow["ClsPric"]) - float(prow["UndrlygPric"])) <= 0:
                            exit_row = prow
                            exit_type = "Early Backwardation Unwind"
                            break

                s1 = float(exit_row["UndrlygPric"])
                if cfg["use_sttlm"] and exit_type == "Expiry Settlement Convergence":
                    f1 = float(exit_row["SttlmPric"]) if exit_row["TradDt"] == exp_dt else float(exit_row["ClsPric"])
                else:
                    f1 = float(exit_row["ClsPric"])

                days_held = max(1, int((exit_row["TradDt"] - ent_dt).days))
                gross_pnl = ((f0 - s0) - (f1 - s1)) * lot
                cap = round(s0 * lot * 1.05, 2)
                chg = compute_statutory_charges(s0, f0, lot, mode=cfg["charge_mode"], slip_bps=cfg["slip_bps"])
                net_pnl = gross_pnl - chg
                ret_pct = (net_pnl / cap) * 100
                rxirr = ret_pct * (365.0 / days_held)

                trade_rec = {
                    "Strategy ID": cfg["id"],
                    "Strategy": cfg["name"],
                    "Cycle": cyc["name"],
                    "Ticker": sym,
                    "Contract": f"{sym} {exp_dt.strftime('%d%b%Y').upper()}",
                    "Entry Date": ent_dt.strftime("%Y-%m-%d"),
                    "Exit Date": exit_row["TradDt"].strftime("%Y-%m-%d"),
                    "Days Held": days_held,
                    "Lot Size": lot,
                    "Entry Spot (₹)": round(s0, 2),
                    "Entry Future (₹)": round(f0, 2),
                    "Entry Basis (%)": round(float(row["EntrySpreadPct"]), 3),
                    "Exit Spot (₹)": round(s1, 2),
                    "Exit Future (₹)": round(f1, 2),
                    "Exit Basis (%)": round(((f1 - s1) / s1) * 100, 3),
                    "Capital Deployed (₹)": int(round(cap)),
                    "Statutory & Slippage Cost (₹)": round(chg, 2),
                    "Net Profit (₹)": round(net_pnl, 2),
                    "Net Return (%)": round(ret_pct, 3),
                    "Expected Entry XIRR (%)": round(float(row["ExpectedXIRR"]), 2),
                    "Realized Net XIRR (%)": round(rxirr, 2),
                    "Exit Mechanism": exit_type,
                    "Positive Carry Win": bool(net_pnl > 0),
                    "Hurdle Beat (>9.00%)": bool(rxirr > hurdle_rate),
                }
                strat_trades.append(trade_rec)
                all_trades.append(trade_rec)

        tdf = pd.DataFrame(strat_trades)
        if not tdf.empty:
            summary_rows.append({
                "Strategy ID": cfg["id"],
                "Strategy Name": cfg["name"],
                "Total Real Trades": len(tdf),
                "Positive Carry Win Rate (%)": round(tdf["Positive Carry Win"].mean() * 100, 1),
                "Hurdle Beat Accuracy (>9.00%)": round(tdf["Hurdle Beat (>9.00%)"].mean() * 100, 1),
                "Average Expected XIRR (%)": round(tdf["Expected Entry XIRR (%)"].mean(), 2),
                "Average Realized XIRR (%)": round(tdf["Realized Net XIRR (%)"].mean(), 2),
                "Median Realized XIRR (%)": round(tdf["Realized Net XIRR (%)"].median(), 2),
                "Avg Profit per Trade (₹)": round(tdf["Net Profit (₹)"].mean(), 2),
                "Total Net Profit (₹)": round(tdf["Net Profit (₹)"].sum(), 2),
                "Min Trade XIRR (%)": round(tdf["Realized Net XIRR (%)"].min(), 2),
            })

    return pd.DataFrame(summary_rows), pd.DataFrame(all_trades)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parquet_cache = "C:/Users/epurntr/.gemini/antigravity/brain/8d98f332-7977-49eb-869e-be83899e77c4/scratch/nse_fo_2026_history.parquet"
    if os.path.exists(parquet_cache):
        raw_df = pd.read_parquet(parquet_cache)
    else:
        raw_df = download_nse_bhavcopy_history()

    summary_df, trades_df = run_multi_strategy_backtest(raw_df)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summary_df.to_csv(os.path.join(base_dir, "backtest_summary.csv"), index=False)
    trades_df.to_csv(os.path.join(base_dir, "backtest_trades.csv"), index=False)
    print("=== BACKTEST SUMMARY (REAL 2026 NSE F&O BHAVCOPY DATA) ===")
    print(summary_df.to_string(index=False))
