from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import yfinance as yf
import pandas as pd
import math
import time

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

CACHE = {}
CACHE_TTL = 1800  # 30 分鐘


def normalize_index_to_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.reset_index()

    time_col = df.columns[0]
    ts = pd.to_datetime(df[time_col], utc=True).dt.tz_convert(None).dt.floor("D")
    df["timestamp"] = ts

    return df


def build_company_result(company_key: str, stock_close_df: pd.DataFrame, btc_close_df: pd.DataFrame):
    cfg = COMPANIES[company_key]

    stock_df = normalize_index_to_timestamp(stock_close_df)
    btc_df = normalize_index_to_timestamp(btc_close_df)

    stock_df = stock_df[["timestamp", "Close"]].rename(columns={"Close": "Close_STOCK"})
    btc_df = btc_df[["timestamp", "Close"]].rename(columns={"Close": "Close_BTC"})

    stock_df = stock_df.sort_values("timestamp").drop_duplicates("timestamp")
    btc_df = btc_df.sort_values("timestamp").drop_duplicates("timestamp")

    df = pd.merge_asof(
        stock_df,
        btc_df,
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("1D")
    ).dropna()

    if df.empty:
        return {"error": "Merged dataframe is empty"}

    shares_outstanding = cfg["shares_outstanding"]
    btc_holdings = cfg["btc_holdings"]

    df["marketCapApprox"] = df["Close_STOCK"] * shares_outstanding
    df["btcNav"] = df["Close_BTC"] * btc_holdings
    df["mnav"] = df["marketCapApprox"] / df["btcNav"]

    result = []
    for _, row in df.iterrows():
        mnav_val = float(row["mnav"])
        if math.isnan(mnav_val) or math.isinf(mnav_val):
            continue

        result.append({
            "date": row["timestamp"].strftime("%Y-%m-%d"),
            "stock_close": round(float(row["Close_STOCK"]), 2),
            "btc_close": round(float(row["Close_BTC"]), 2),
            "market_cap_approx": round(float(row["marketCapApprox"]), 2),
            "btc_nav": round(float(row["btcNav"]), 2),
            "mnav": round(mnav_val, 4)
        })

    if not result:
        return {"error": "No valid rows after calculation"}

    return {
        "company": company_key,
        "company_name": cfg["name"],
        "ticker": cfg["ticker"],
        "latest": result[-1],
        "series": result
    }


@app.get("/api/mnav")
def get_all_mnav(
    period: str = Query(default="7d"),
    interval: str = Query(default="1d")
):
    cache_key = f"{period}_{interval}"
    now = time.time()

    try:
        # 先回新鮮 cache
        if cache_key in CACHE:
            cached_entry = CACHE[cache_key]
            if now - cached_entry["timestamp"] < CACHE_TTL:
                return cached_entry["data"]

        tickers = ["BTC-USD"] + [cfg["ticker"] for cfg in COMPANIES.values()]

        raw = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=False
        )

        if raw.empty:
            # 如果有舊 cache，就回舊 cache，不要整個炸掉
            if cache_key in CACHE:
                stale_data = CACHE[cache_key]["data"]
                stale_data["cache_status"] = "stale"
                return stale_data

            return JSONResponse(status_code=500, content={"error": "Downloaded data is empty"})

        all_data = {}

        btc_close_df = raw["BTC-USD"][["Close"]].dropna() if "BTC-USD" in raw.columns.levels[0] else pd.DataFrame()

        if btc_close_df.empty:
            if cache_key in CACHE:
                stale_data = CACHE[cache_key]["data"]
                stale_data["cache_status"] = "stale"
                return stale_data

            return JSONResponse(status_code=500, content={"error": "BTC history is empty"})

        for company_key, cfg in COMPANIES.items():
            ticker = cfg["ticker"]

            if ticker not in raw.columns.levels[0]:
                all_data[company_key] = {"error": f"{ticker} not found in download result"}
                continue

            stock_close_df = raw[ticker][["Close"]].dropna()

            if stock_close_df.empty:
                all_data[company_key] = {"error": f"{ticker} history is empty"}
                continue

            all_data[company_key] = build_company_result(company_key, stock_close_df, btc_close_df)

        result = {
            "indicator": "mNAV",
            "period": period,
            "interval": interval,
            "companies": all_data,
            "available_companies": list(COMPANIES.keys()),
            "cache_status": "fresh"
        }

        CACHE[cache_key] = {
            "timestamp": now,
            "data": result
        }

        return result

    except Exception as e:
        msg = str(e)

        # 有舊 cache 就優先回舊資料
        if cache_key in CACHE:
            stale_data = CACHE[cache_key]["data"]
            stale_data["cache_status"] = "stale"
            stale_data["warning"] = "Used stale cache because live fetch failed."
            return stale_data

        if "Too Many Requests" in msg or "Rate limited" in msg or "429" in msg:
            return JSONResponse(
                status_code=429,
                content={"error": "資料來源暫時限流，請稍後再試。"}
            )

        return JSONResponse(status_code=500, content={"error": msg})


handler = app