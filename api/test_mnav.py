import yfinance as yf
import pandas as pd

print("=== Step 1: Fetch data ===")

mstr = yf.Ticker("MSTR")
btc = yf.Ticker("BTC-USD")

mstr_hist = mstr.history(period="6mo", interval="1d")
btc_hist = btc.history(period="6mo", interval="1d")

print("MSTR rows:", len(mstr_hist))
print("BTC rows:", len(btc_hist))

print("\n=== Step 2: Preview index ===")
print("MSTR index sample:")
print(mstr_hist.index[:3])

print("\nBTC index sample:")
print(btc_hist.index[:3])

# Reset index
mstr_df = mstr_hist[["Close"]].reset_index()
btc_df = btc_hist[["Close"]].reset_index()

mstr_date_col = mstr_df.columns[0]
btc_date_col = btc_df.columns[0]

# Convert to date string
mstr_df["date"] = pd.to_datetime(mstr_df[mstr_date_col]).dt.strftime("%Y-%m-%d")
btc_df["date"] = pd.to_datetime(btc_df[btc_date_col]).dt.strftime("%Y-%m-%d")

mstr_df = mstr_df[["date", "Close"]].rename(columns={"Close": "Close_MSTR"})
btc_df = btc_df[["date", "Close"]].rename(columns={"Close": "Close_BTC"})

print("\n=== Step 3: Date samples ===")
print("MSTR dates:", mstr_df["date"].head(5).tolist())
print("BTC dates:", btc_df["date"].head(5).tolist())

# Merge
df = pd.merge(mstr_df, btc_df, on="date", how="inner")

print("\n=== Step 4: Merge result ===")
print("Merged rows:", len(df))

if df.empty:
    print("❌ ERROR: Merge is empty!")
    exit()

print(df.head())

# Compute mNAV
SHARES_OUTSTANDING = 199000000
BTC_HOLDINGS = 214400

df["marketCap"] = df["Close_MSTR"] * SHARES_OUTSTANDING
df["btcNav"] = df["Close_BTC"] * BTC_HOLDINGS
df["mnav"] = df["marketCap"] / df["btcNav"]

print("\n=== Step 5: mNAV preview ===")
print(df[["date", "mnav"]].head())

print("\n✅ SUCCESS: Pipeline works locally")