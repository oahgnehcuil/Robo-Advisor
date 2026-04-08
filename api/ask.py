from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google import genai
import os
import math
import yfinance as yf
import pandas as pd

app = FastAPI()

COMPANIES = {
    "MSTR": {
        "ticker": "MSTR",
        "name": "MicroStrategy",
        "shares_outstanding": 199000000,
        "btc_holdings": 214400
    },
    "COIN": {
        "ticker": "COIN",
        "name": "Coinbase",
        "shares_outstanding": 262000000,
        "btc_holdings": 9185
    },
    "3350.T": {
        "ticker": "3350.T",
        "name": "Metaplanet",
        "shares_outstanding": 593000000,
        "btc_holdings": 4050
    }
}


class AskRequest(BaseModel):
    question: str
    period: str = "7d"
    interval: str = "1h"


def normalize_time_column(df: pd.DataFrame, time_col: str, interval: str) -> pd.DataFrame:
    df = df.copy()
    ts = pd.to_datetime(df[time_col], utc=True).dt.tz_convert(None)

    if interval.endswith("h"):
        ts = ts.dt.floor("h")
    elif interval.endswith("m"):
        ts = ts.dt.floor("min")
    else:
        ts = ts.dt.floor("D")

    df["timestamp"] = ts
    return df


def fetch_company_data(company_key: str, period: str, interval: str, btc_hist: pd.DataFrame):
    cfg = COMPANIES[company_key]
    stock = yf.Ticker(cfg["ticker"])
    stock_hist = stock.history(period=period, interval=interval)

    if stock_hist.empty:
        return {"error": f"{company_key} history is empty"}

    stock_df = stock_hist[["Close"]].reset_index()
    btc_df = btc_hist[["Close"]].reset_index()

    stock_time_col = stock_df.columns[0]
    btc_time_col = btc_df.columns[0]

    stock_df = normalize_time_column(stock_df, stock_time_col, interval)
    btc_df = normalize_time_column(btc_df, btc_time_col, interval)

    stock_df = stock_df[["timestamp", "Close"]].rename(columns={"Close": "Close_STOCK"})
    btc_df = btc_df[["timestamp", "Close"]].rename(columns={"Close": "Close_BTC"})

    stock_df = stock_df.sort_values("timestamp").drop_duplicates("timestamp")
    btc_df = btc_df.sort_values("timestamp").drop_duplicates("timestamp")

    tolerance = pd.Timedelta("90min") if interval.endswith("h") else pd.Timedelta("1D")

    df = pd.merge_asof(
        stock_df,
        btc_df,
        on="timestamp",
        direction="nearest",
        tolerance=tolerance
    ).dropna()

    if df.empty:
        return {"error": "Merged dataframe is empty"}

    shares_outstanding = cfg["shares_outstanding"]
    btc_holdings = cfg["btc_holdings"]

    df["marketCapApprox"] = df["Close_STOCK"] * shares_outstanding
    df["btcNav"] = df["Close_BTC"] * btc_holdings
    df["mnav"] = df["marketCapApprox"] / df["btcNav"]

    if interval.endswith("h") or interval.endswith("m"):
        time_fmt = "%Y-%m-%d %H:%M"
    else:
        time_fmt = "%Y-%m-%d"

    result = []
    for _, row in df.iterrows():
        mnav_val = float(row["mnav"])
        if math.isnan(mnav_val) or math.isinf(mnav_val):
            continue

        result.append({
            "date": row["timestamp"].strftime(time_fmt),
            "stock_close": round(float(row["Close_STOCK"]), 2),
            "btc_close": round(float(row["Close_BTC"]), 2),
            "mnav": round(mnav_val, 4)
        })

    if not result:
        return {"error": "No valid rows after calculation"}

    return {
        "company": company_key,
        "company_name": cfg["name"],
        "ticker": cfg["ticker"],
        "latest": result[-1],
        "series": result[-24:]  # 只取最近 24 筆，避免 prompt 太大
    }


def get_dashboard_snapshot(period: str, interval: str):
    btc = yf.Ticker("BTC-USD")
    btc_hist = btc.history(period=period, interval=interval)

    if btc_hist.empty:
        return {"error": "BTC history is empty"}

    output = {}
    for company_key in COMPANIES.keys():
        output[company_key] = fetch_company_data(company_key, period, interval, btc_hist)
    return output


@app.post("/api/ask")
def ask_gemini(req: AskRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return JSONResponse(
                status_code=500,
                content={"error": "Missing GEMINI_API_KEY"}
            )

        dashboard_data = get_dashboard_snapshot(req.period, req.interval)

        if "error" in dashboard_data:
            return JSONResponse(status_code=500, content=dashboard_data)

        client = genai.Client(api_key=api_key)

        system_prompt = """
You are a financial dashboard assistant.
Answer only based on the provided dashboard data.
If the data is insufficient, clearly say so.
Keep the answer concise, factual, and easy to understand.
Focus on mNAV, stock price, BTC relationship, short-term trend, and cross-company comparison.
"""

        user_prompt = f"""
Dashboard data:
{dashboard_data}

User question:
{req.question}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_prompt}]}
            ],
        )

        return {
            "answer": response.text,
            "data_used": dashboard_data
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


handler = app