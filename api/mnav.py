from fastapi import FastAPI
from fastapi.responses import JSONResponse
import yfinance as yf
import pandas as pd
import math

app = FastAPI()


@app.get("/api/mnav")
def get_mnav():
    try:
        # 抓歷史價格
        mstr = yf.Ticker("MSTR")
        btc = yf.Ticker("BTC-USD")

        mstr_hist = mstr.history(period="6mo", interval="1d")
        btc_hist = btc.history(period="6mo", interval="1d")

        if mstr_hist.empty:
            return JSONResponse(
                status_code=500,
                content={"error": "MSTR history is empty"}
            )

        if btc_hist.empty:
            return JSONResponse(
                status_code=500,
                content={"error": "BTC history is empty"}
            )

        # 只取收盤價
        mstr_hist = mstr_hist[["Close"]].rename(columns={"Close": "Close_MSTR"})
        btc_hist = btc_hist[["Close"]].rename(columns={"Close": "Close_BTC"})

        # 對齊日期
        df = mstr_hist.join(btc_hist, how="inner").dropna()

        if df.empty:
            return JSONResponse(
                status_code=500,
                content={"error": "Joined dataframe is empty"}
            )

        # 先用固定假設值，讓網站先穩定跑起來
        SHARES_OUTSTANDING = 199000000
        BTC_HOLDINGS = 214400

        # 計算
        df["marketCapApprox"] = df["Close_MSTR"] * SHARES_OUTSTANDING
        df["btcNav"] = df["Close_BTC"] * BTC_HOLDINGS
        df["mnav"] = df["marketCapApprox"] / df["btcNav"]

        result = []
        for idx, row in df.iterrows():
            mnav_val = float(row["mnav"])

            if math.isnan(mnav_val) or math.isinf(mnav_val):
                continue

            result.append({
                "date": idx.strftime("%Y-%m-%d"),
                "mstr_close": round(float(row["Close_MSTR"]), 2),
                "btc_close": round(float(row["Close_BTC"]), 2),
                "market_cap_approx": round(float(row["marketCapApprox"]), 2),
                "btc_nav": round(float(row["btcNav"]), 2),
                "mnav": round(mnav_val, 4)
            })

        if not result:
            return JSONResponse(
                status_code=500,
                content={"error": "No valid rows after calculation"}
            )

        return {
            "indicator": "mNAV",
            "company": "MSTR",
            "shares_outstanding_assumption": SHARES_OUTSTANDING,
            "btc_holdings_assumption": BTC_HOLDINGS,
            "latest": result[-1],
            "series": result
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


handler = app