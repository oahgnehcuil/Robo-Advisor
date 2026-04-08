from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import yfinance as yf
import pandas as pd
import math

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


def fetch_company_data(company_key: str, period: str, interval: str, btc_hist: pd.DataFrame):
    cfg = COMPANIES[company_key]
    stock = yf.Ticker(cfg["ticker"])
    stock_hist = stock.history(period=period, interval=interval)

    if stock_hist.empty:
        return {
            "error": f"{company_key} history is empty"
        }

    stock_df = stock_hist[["Close"]].reset_index()
    btc_df = btc_hist[["Close"]].reset_index()

    stock_date_col = stock_df.columns[0]
    btc_date_col = btc_df.columns[0]

    if interval.endswith("h") or interval.endswith("m"):
        fmt = "%Y-%m-%d %H:%M"
    else:
        fmt = "%Y-%m-%d"

    stock_df["date"] = pd.to_datetime(stock_df[stock_date_col]).dt.strftime(fmt)
    btc_df["date"] = pd.to_datetime(btc_df[btc_date_col]).dt.strftime(fmt)

    stock_df = stock_df[["date", "Close"]].rename(columns={"Close": "Close_STOCK"})
    btc_df = btc_df[["date", "Close"]].rename(columns={"Close": "Close_BTC"})

    df = pd.merge(stock_df, btc_df, on="date", how="inner").dropna()

    if df.empty:
        return {
            "error": "Merged dataframe is empty",
            "stock_sample_dates": stock_df["date"].head(5).tolist(),
            "btc_sample_dates": btc_df["date"].head(5).tolist()
        }

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
            "date": row["date"],
            "stock_close": round(float(row["Close_STOCK"]), 2),
            "btc_close": round(float(row["Close_BTC"]), 2),
            "market_cap_approx": round(float(row["marketCapApprox"]), 2),
            "btc_nav": round(float(row["btcNav"]), 2),
            "mnav": round(mnav_val, 4)
        })

    if not result:
        return {
            "error": "No valid rows after calculation"
        }

    return {
        "company": company_key,
        "company_name": cfg["name"],
        "ticker": cfg["ticker"],
        "shares_outstanding_assumption": shares_outstanding,
        "btc_holdings_assumption": btc_holdings,
        "latest": result[-1],
        "series": result
    }


@app.get("/api/mnav")
def get_all_mnav(
    period: str = Query(default="7d"),
    interval: str = Query(default="1h")
):
    try:
        btc = yf.Ticker("BTC-USD")
        btc_hist = btc.history(period=period, interval=interval)

        if btc_hist.empty:
            return JSONResponse(
                status_code=500,
                content={"error": "BTC history is empty"}
            )

        all_data = {}

        for company_key in COMPANIES.keys():
            all_data[company_key] = fetch_company_data(company_key, period, interval, btc_hist)

        return {
            "indicator": "mNAV",
            "period": period,
            "interval": interval,
            "companies": all_data,
            "available_companies": list(COMPANIES.keys())
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


handler = app