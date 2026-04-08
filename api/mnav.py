from fastapi import FastAPI
from fastapi.responses import JSONResponse
import yfinance as yf
import pandas as pd
from math import isnan

app = FastAPI()

@app.get("/api/mnav")
def get_mnav():
    try:
        # 抓歷史資料
        mstr = yf.Ticker("MSTR")
        btc = yf.Ticker("BTC-USD")

        mstr_hist = mstr.history(period="6mo")[["Close"]]
        btc_hist = btc.history(period="6mo")[["Close"]]

        if mstr_hist.empty or btc_hist.empty:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to fetch data from yfinance"}
            )

        # 對齊日期
        df = mstr_hist.join(btc_hist, lsuffix="_MSTR", rsuffix="_BTC").dropna()

        # 先用固定參數，之後你可以改
        BTC_HOLDINGS = 214400

        info = mstr.info
        shares_outstanding = info.get("sharesOutstanding")

        if not shares_outstanding:
            return JSONResponse(
                status_code=500,
                content={"error": "sharesOutstanding not found"}
            )

        df["marketCapApprox"] = df["Close_MSTR"] * shares_outstanding
        df["btcNav"] = df["Close_BTC"] * BTC_HOLDINGS
        df["mnav"] = df["marketCapApprox"] / df["btcNav"]

        result = []
        for idx, row in df.iterrows():
            mnav_val = float(row["mnav"])
            if isnan(mnav_val):
                continue

            result.append({
                "date": idx.strftime("%Y-%m-%d"),
                "mstr_close": round(float(row["Close_MSTR"]), 2),
                "btc_close": round(float(row["Close_BTC"]), 2),
                "market_cap_approx": round(float(row["marketCapApprox"]), 2),
                "btc_nav": round(float(row["btcNav"]), 2),
                "mnav": round(mnav_val, 4)
            })

        latest = result[-1] if result else None

        return {
            "indicator": "mNAV",
            "company": "MSTR",
            "btc_holdings_assumption": BTC_HOLDINGS,
            "latest": latest,
            "series": result
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# 給 Vercel 用
handler = app