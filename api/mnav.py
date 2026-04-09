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

def safe_history(ticker: str, period: str, interval: str, retries: int = 3, sleep_sec: int = 2):
    last_error = None

    for i in range(retries):
        try:
            df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
            print(f"[DEBUG] {ticker} attempt {i+1}, rows={len(df)}")

            if not df.empty:
                return df
        except Exception as e:
            last_error = e
            print(f"[ERROR] {ticker} attempt {i+1}: {e}")

        time.sleep(sleep_sec)

    if last_error:
        print(f"[FINAL ERROR] {ticker}: {last_error}")
    else:
        print(f"[FINAL ERROR] {ticker}: empty history after retries")

    return pd.DataFrame()

def get_btc_history(period: str, interval: str):
    btc_tickers = ["BTC-USD", "BTCUSD=X"]

    for ticker in btc_tickers:
        df = safe_history(ticker, period, interval)
        if not df.empty:
            print(f"[INFO] Using BTC ticker: {ticker}")
            return df

    return pd.DataFrame()

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
    ticker = cfg["ticker"]

    stock_hist = safe_history(ticker, period, interval)

    if stock_hist.empty:
        return {"error": f"{ticker} history is empty"}

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

    time_fmt = "%Y-%m-%d" if interval.endswith("d") else "%Y-%m-%d %H:%M"

    result = []
    for _, row in df.iterrows():
        mnav_val = float(row["mnav"])
        if math.isnan(mnav_val) or math.isinf(mnav_val):
            continue

        result.append({
            "date": row["timestamp"].strftime(time_fmt),
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
    period: str = Query(default="14d"),
    interval: str = Query(default="1d")
):
    cache_key = f"{period}_{interval}"
    now = time.time()

    try:
        if cache_key in CACHE:
            cached_entry = CACHE[cache_key]
            if now - cached_entry["timestamp"] < CACHE_TTL:
                return cached_entry["data"]

        btc_hist = get_btc_history(period, interval)

        if btc_hist.empty:
            if cache_key in CACHE:
                stale_data = CACHE[cache_key]["data"].copy()
                stale_data["cache_status"] = "stale"
                stale_data["warning"] = "Used stale cache because BTC fetch failed."
                return stale_data

            return JSONResponse(
                status_code=500,
                content={"error": "BTC history is empty"}
            )

        all_data = {}
        for company_key in COMPANIES.keys():
            all_data[company_key] = fetch_company_data(company_key, period, interval, btc_hist)
            time.sleep(1)

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

        if cache_key in CACHE:
            stale_data = CACHE[cache_key]["data"].copy()
            stale_data["cache_status"] = "stale"
            stale_data["warning"] = "Used stale cache because live fetch failed."
            return stale_data

        if "Too Many Requests" in msg or "Rate limited" in msg or "429" in msg:
            return JSONResponse(
                status_code=429,
                content={"error": "資料來源暫時限流，請稍後再試。"}
            )

        return JSONResponse(
            status_code=500,
            content={"error": msg}
        )


handler = app