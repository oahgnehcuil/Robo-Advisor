from fastapi import FastAPI
from fastapi.responses import JSONResponse
import yfinance as yf
import pandas as pd
import math

app = FastAPI()


@app.get("/api/mnav")
def get_mnav():
    try:
        mstr = yf.Ticker("MSTR")
        btc = yf.Ticker("BTC-USD")

        mstr_hist = mstr.history(period="7d", interval="1h")
        btc_hist = btc.history(period="7d", interval="1h")

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

        # 只保留 Close，並把 index 轉成 date 欄位
        mstr_df = mstr_hist[["Close"]].reset_index()
        btc_df = btc_hist[["Close"]].reset_index()

        # 找出日期欄位名稱（通常會是 Date 或 Datetime）
        mstr_date_col = mstr_df.columns[0]
        btc_date_col = btc_df.columns[0]

        # 轉成 yyyy-mm-dd 字串，避免時區/時間戳對不起來
        mstr_df["date"] = pd.to_datetime(mstr_df[mstr_date_col]).dt.strftime("%Y-%m-%d")
        btc_df["date"] = pd.to_datetime(btc_df[btc_date_col]).dt.strftime("%Y-%m-%d")

        mstr_df = mstr_df[["date", "Close"]].rename(columns={"Close": "Close_MSTR"})
        btc_df = btc_df[["date", "Close"]].rename(columns={"Close": "Close_BTC"})

        # 用 date 合併，不要直接 join index
        df = pd.merge(mstr_df, btc_df, on="date", how="inner").dropna()

        if df.empty:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Merged dataframe is empty",
                    "mstr_sample_dates": mstr_df["date"].head(5).tolist(),
                    "btc_sample_dates": btc_df["date"].head(5).tolist()
                }
            )

        # 先用固定假設值，讓系統穩定跑
        SHARES_OUTSTANDING = 199000000
        BTC_HOLDINGS = 214400

        df["marketCapApprox"] = df["Close_MSTR"] * SHARES_OUTSTANDING
        df["btcNav"] = df["Close_BTC"] * BTC_HOLDINGS
        df["mnav"] = df["marketCapApprox"] / df["btcNav"]

        result = []
        for _, row in df.iterrows():
            mnav_val = float(row["mnav"])

            if math.isnan(mnav_val) or math.isinf(mnav_val):
                continue

            result.append({
                "date": row["date"],
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